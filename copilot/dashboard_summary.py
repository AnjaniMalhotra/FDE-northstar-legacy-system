"""System-wide counts over northstar_web — pure aggregation, no tool/HTTP
concerns, shared by the chat tools (copilot/tools/reporting_tools.py) and the
dashboard API endpoint (backend/copilot_api/routes/console_routes.py) so
the counting logic exists in exactly one place. Mirrors
copilot/reconciliation_detention.py's shape: frozen dataclass + one get_*
function per concern."""
# ------------------------------------------
# IMPORTS
# ------------------------------------------
from dataclasses import dataclass
from datetime import datetime

from sqlalchemy import text
from sqlalchemy.engine import Engine

from copilot.shipment_status import compute_status


# ------------------------------------------
# FLAG SUMMARY — dispute_flags + carrier risk counts
# ------------------------------------------
@dataclass(frozen=True)
class FlagSummary:
    pending_tier2_approvals: int
    auto_logged_this_week: int
    elevated_risk_carriers: int


def get_flag_summary(engine: Engine) -> FlagSummary:
    with engine.connect() as conn:
        pending = conn.execute(text(
            "SELECT count(*) FROM dispute_flags WHERE status = 'PENDING_APPROVAL'"
        )).scalar_one()
        auto_logged = conn.execute(text(
            "SELECT count(*) FROM dispute_flags "
            "WHERE status = 'AUTO_LOGGED' AND created_at > now() - interval '7 days'"
        )).scalar_one()
        # elevated: Legacy's own carriers.elevated_risk column — the AI's own
        # carrier_risk_notes override table was removed along with the
        # Carrier Risk & Disputes console tab, the only way it was ever set.
        elevated = conn.execute(text(
            "SELECT count(*) FROM carriers WHERE elevated_risk"
        )).scalar_one()
    return FlagSummary(pending, auto_logged, elevated)


# ------------------------------------------
# SHIPMENT STATUS SUMMARY — counts by derived status (not a stored column)
# ------------------------------------------
@dataclass(frozen=True)
class ShipmentStatusSummary:
    scheduled: int
    enroute: int
    at_dock: int
    delivered: int


def get_shipment_status_summary(engine: Engine) -> ShipmentStatusSummary:
    with engine.connect() as conn:
        shipments = conn.execute(text(
            "SELECT id AS shipment_id, pickup_appt, delivery_appt FROM shipments"
        )).mappings().all()
        events = conn.execute(text("""
            SELECT shipment_id, bool_or(type = 'ARRIVAL') AS has_arrival, bool_or(type = 'DEPARTURE') AS has_departure
            FROM dock_events GROUP BY shipment_id
        """)).mappings().all()
    events_by_shipment = {e["shipment_id"]: e for e in events}

    now = datetime.now()
    counts = {"SCHEDULED": 0, "ENROUTE": 0, "AT_DOCK": 0, "DELIVERED": 0}
    for shipment in shipments:
        ev = events_by_shipment.get(shipment["shipment_id"], {"has_arrival": False, "has_departure": False})
        status = compute_status(shipment["pickup_appt"], shipment["delivery_appt"], ev["has_arrival"], ev["has_departure"], now)
        counts[status] += 1
    return ShipmentStatusSummary(counts["SCHEDULED"], counts["ENROUTE"], counts["AT_DOCK"], counts["DELIVERED"])
