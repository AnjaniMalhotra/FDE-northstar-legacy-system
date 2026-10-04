"""Read-only, system-wide aggregate tools — for a "how many" question that
no per-shipment/per-carrier tool can answer (see system_prompt.txt rule 8).
Each wraps a pure counting function in copilot/dashboard_summary.py, the
same one backend/copilot_api/routes/console_routes.py's dashboard endpoint
uses, so the numbers shown in chat and on the dashboard can never drift
apart."""
# ------------------------------------------
# IMPORTS
# ------------------------------------------
from langchain_core.tools import tool

from copilot.dashboard_summary import get_flag_summary
from copilot.dashboard_summary import get_shipment_status_summary as compute_shipment_status_summary
from copilot.database import engine


# ------------------------------------------
# GET DISPUTE FLAG SUMMARY — system-wide flag/risk counts
# ------------------------------------------
@tool
def get_dispute_flag_summary() -> str:
    """
    System-wide counts: how many dispute flags are pending human approval
    right now, how many were auto-logged in the last 7 days, and how many
    carriers currently carry an Elevated Risk flag. Use this for an
    aggregate/count question (e.g. "how many invoices are pending
    approval") — never invent a count from a single load or carrier lookup.
    """
    summary = get_flag_summary(engine)
    return (
        f"{summary.pending_tier2_approvals} flag(s) pending Tier 2 human approval. "
        f"{summary.auto_logged_this_week} flag(s) auto-logged (Tier 1) in the last 7 days. "
        f"{summary.elevated_risk_carriers} carrier(s) currently marked Elevated Risk."
    )


# ------------------------------------------
# GET SHIPMENT STATUS SUMMARY — system-wide shipment status counts
# ------------------------------------------
@tool
def get_shipment_status_summary() -> str:
    """
    System-wide counts of shipments by status — Scheduled, Enroute, At
    Dock, Delivered — derived the same way the shipment directory computes
    it (from real dock events and appointment times, not a stored field).
    Use this for a question like "how many shipments are enroute" or "how
    many loads are still scheduled" — never invent a count from a single
    load lookup.
    """
    summary = compute_shipment_status_summary(engine)
    return (
        f"{summary.scheduled} scheduled, {summary.enroute} enroute, "
        f"{summary.at_dock} at dock, {summary.delivered} delivered."
    )
