"""Database-derived detention facts shared by the agent and evaluation.
Detention has a time dimension (billed hours vs. real dock dwell time) —
see reconciliation_linehaul.py for the simpler, flat-rate linehaul check."""
# ------------------------------------------
# IMPORTS
# ------------------------------------------
from dataclasses import dataclass
from datetime import datetime, timedelta
from decimal import Decimal, ROUND_HALF_UP

from sqlalchemy import text
from sqlalchemy.engine import Engine


# ------------------------------------------
# ROUNDING PRECISION — money values round to the nearest cent
# ------------------------------------------
MONEY = Decimal("0.01")


# ------------------------------------------
# RECONCILIATION RESULT — billed vs. actual detention facts and their variances
# ------------------------------------------
@dataclass(frozen=True)
class Reconciliation:
    shipment_id: int
    invoice_id: int
    carrier_id: int
    actual_hours: Decimal
    billed_hours: Decimal
    actual_amount: Decimal
    billed_amount: Decimal
    arrival: datetime
    departure: datetime
    free_hours: Decimal
    rate_per_hour: Decimal

    @property
    def hour_variance(self) -> Decimal:
        return self.billed_hours - self.actual_hours

    @property
    def amount_variance(self) -> Decimal:
        return self.billed_amount - self.actual_amount

    @property
    def time_variance(self) -> timedelta:
        return timedelta(hours=float(abs(self.hour_variance)))

    @property
    def dwell_hours(self) -> Decimal:
        return Decimal(str((self.departure - self.arrival).total_seconds())) / Decimal("3600")


# ------------------------------------------
# GET RECONCILIATION — pull billed and actual detention facts for one shipment
# ------------------------------------------
def get_reconciliation(engine: Engine, shipment_id: int) -> Reconciliation | None:
    """Calculate billed-versus-actual detention from northstar_web's own
    tables only — no views layer needed, since that schema is already
    clean."""
    # ------------------------------------------
    # QUERY — join shipment, invoice, and dock events for this shipment
    # ------------------------------------------
    query = text("""
        SELECT i.id AS invoice_id, s.carrier_id, s.detention_free_hours,
               s.detention_rate_per_hour, i.detention_hours_billed,
               i.detention_amount_billed,
               MIN(CASE WHEN d.type = 'ARRIVAL' THEN d.timestamp END) AS arrival,
               MIN(CASE WHEN d.type = 'DEPARTURE' THEN d.timestamp END) AS departure
        FROM shipments s
        JOIN invoices i ON i.shipment_id = s.id
        JOIN dock_events d ON d.shipment_id = s.id
        WHERE s.id = :shipment_id
        GROUP BY i.id, s.carrier_id, s.detention_free_hours,
                 s.detention_rate_per_hour, i.detention_hours_billed,
                 i.detention_amount_billed
    """)
    # ------------------------------------------
    # FETCH ROW — bail out if the shipment or its dock events are incomplete
    # ------------------------------------------
    with engine.connect() as conn:
        row = conn.execute(query, {"shipment_id": shipment_id}).fetchone()
    if not row or not row.arrival or not row.departure:
        return None

    # ------------------------------------------
    # COMPUTE ACTUAL DETENTION — dwell time minus free hours, priced at the contract rate
    # ------------------------------------------
    dwell_hours = Decimal(str((row.departure - row.arrival).total_seconds())) / Decimal("3600")
    actual_hours = max(Decimal("0"), dwell_hours - Decimal(str(row.detention_free_hours)))
    actual_amount = (actual_hours * Decimal(str(row.detention_rate_per_hour))).quantize(MONEY, ROUND_HALF_UP)
    # ------------------------------------------
    # BUILD RESULT — combine actual and billed figures into one Reconciliation
    # ------------------------------------------
    return Reconciliation(
        shipment_id=shipment_id, invoice_id=row.invoice_id, carrier_id=row.carrier_id,
        actual_hours=actual_hours.quantize(MONEY, ROUND_HALF_UP),
        billed_hours=Decimal(str(row.detention_hours_billed)), actual_amount=actual_amount,
        billed_amount=Decimal(str(row.detention_amount_billed)),
        arrival=row.arrival, departure=row.departure,
        free_hours=Decimal(str(row.detention_free_hours)),
        rate_per_hour=Decimal(str(row.detention_rate_per_hour)),
    )


# ------------------------------------------
# FORMAT RECONCILIATION — render facts as text for the LLM to read
# ------------------------------------------
def format_reconciliation(result: Reconciliation) -> str:
    """Render facts for the LLM; policy decisions happen elsewhere."""
    return (
        f"Shipment {result.shipment_id}:\n"
        f"ACTUAL detention: {result.actual_hours:.2f} hrs = ${result.actual_amount:.2f}\n"
        f"BILLED detention: {result.billed_hours:.2f} hrs = ${result.billed_amount:.2f}\n"
        f"Difference: {result.hour_variance:+.2f} hrs, ${result.amount_variance:+.2f}"
    )


# ------------------------------------------
# FORMAT DURATION — a Decimal hour count as "1 hour 42 minutes" / "31 minutes", for people
# ------------------------------------------
def _format_duration(hours: Decimal) -> str:
    total_minutes = int((hours * 60).to_integral_value(rounding=ROUND_HALF_UP))
    h, m = divmod(total_minutes, 60)
    parts = []
    if h:
        parts.append(f"{h} hour{'s' if h != 1 else ''}")
    if m or not parts:
        parts.append(f"{m} minute{'s' if m != 1 else ''}")
    return " ".join(parts)


# ------------------------------------------
# PLAIN LANGUAGE FACTS — the same reconciliation, spelled out for a non-technical reader
# ------------------------------------------
def plain_language_facts(result: Reconciliation) -> list[dict]:
    """Every number a person would want to see to trust the ACTUAL-vs-BILLED result,
    in plain English — no jargon, no raw column names. Used by the invoice review
    page instead of the raw ACTUAL/BILLED text above."""
    overage_hours = max(Decimal("0"), result.dwell_hours - result.free_hours)
    overage_text = (
        "None — within the free time allowed" if overage_hours <= 0
        else f"{_format_duration(overage_hours)} over the free allowance"
    )
    return [
        {"label": "Free time allowed", "value": f"{result.free_hours:.0f} hours"},
        {"label": "Truck arrived", "value": result.arrival.strftime("%b %-d, %Y, %-I:%M %p")},
        {"label": "Truck left", "value": result.departure.strftime("%b %-d, %Y, %-I:%M %p")},
        {"label": "Time at the dock", "value": _format_duration(result.dwell_hours)},
        {"label": "Time over the free allowance", "value": overage_text},
        {"label": "Detention rate", "value": f"${result.rate_per_hour:.2f} per hour"},
        {"label": "What detention should cost", "value": f"${result.actual_amount:.2f}"},
        {"label": "What the carrier billed", "value": f"${result.billed_amount:.2f}"},
        {
            "label": "Difference",
            "value": (
                f"${result.amount_variance:.2f} too much" if result.amount_variance > 0
                else f"${-result.amount_variance:.2f} too little" if result.amount_variance < 0
                else "None — billed correctly"
            ),
        },
    ]
