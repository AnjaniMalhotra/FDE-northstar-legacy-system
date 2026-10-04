"""Named, per-carrier lookups — easier to authorize, log, and explain than
a free-form query, and what the agent should reach for whenever a question
is about one carrier's history or pattern rather than a single invoice."""
# ------------------------------------------
# IMPORTS
# ------------------------------------------
from sqlalchemy import text

from copilot.database import engine
from langchain_core.tools import tool


# ------------------------------------------
# GET CARRIER INVOICE HISTORY — list a carrier's invoices, most recent first
# ------------------------------------------
@tool
def get_carrier_invoice_history(carrier_id: int) -> str:
    """Lists a carrier's invoices — submitted date, billed detention, and
    total amount — most recent first. Use this instead of query_northstar_data
    when the question is specifically about one carrier's invoice history.
    carrier_id MUST come from the user or an earlier tool result in this
    conversation — never call this with a guessed or default carrier_id just
    because none was given (e.g. a date-only question with no carrier named
    is NOT this tool; use query_northstar_data with a WHERE submitted_at
    clause instead, or ask which carrier)."""
    query = text("""
        SELECT id AS invoice_id, shipment_id, submitted_at, detention_hours_billed,
               detention_amount_billed, total_amount
        FROM invoices
        WHERE carrier_id = :carrier_id ORDER BY submitted_at DESC LIMIT 20
    """)
    with engine.connect() as conn:
        rows = conn.execute(query, {"carrier_id": carrier_id}).fetchall()
    if not rows:
        return f"No invoices found for carrier_id {carrier_id}."
    return "\n".join(
        f"Invoice {r.invoice_id} (shipment {r.shipment_id}, {r.submitted_at}): "
        f"detention {r.detention_hours_billed}hrs/${r.detention_amount_billed}, total ${r.total_amount}"
        for r in rows
    )


# ------------------------------------------
# GET CARRIER FLAG HISTORY — list every dispute flag logged against a carrier
# ------------------------------------------
@tool
def get_carrier_flag_history(carrier_id: int) -> str:
    """Lists every dispute flag ever logged against a carrier — tier, status,
    and (if resolved) whether the dispute was upheld. Use this to answer
    'has this carrier been flagged before?' or 'what's their pattern?'"""
    query = text("""
        SELECT flag_id, shipment_id, tier, status, dispute_outcome, reasoning, created_at
        FROM dispute_flags
        WHERE carrier_id = :carrier_id ORDER BY created_at DESC LIMIT 20
    """)
    with engine.connect() as conn:
        rows = conn.execute(query, {"carrier_id": carrier_id}).fetchall()
    if not rows:
        return f"No flags on record for carrier_id {carrier_id}."
    return "\n".join(
        f"Flag {r.flag_id} (shipment {r.shipment_id}, {r.created_at}): {r.tier}/{r.status}"
        f"{f', dispute {r.dispute_outcome}' if r.dispute_outcome else ''} — {r.reasoning}"
        for r in rows
    )


# ------------------------------------------
# GET CARRIER RISK PROFILE — Legacy's own safety/risk fields for a carrier
# ------------------------------------------
@tool
def get_carrier_risk_profile(carrier_id: int) -> str:
    """Northstar's own safety/risk fields for a carrier: safety rating,
    out-of-service violations, insurance status, and whether it's on the
    Elevated Risk list. Use this before recommending any carrier-level
    escalation."""
    query = text("""
        SELECT mc_number, safety_rating, oos_violations, insurance_status, elevated_risk
        FROM carriers WHERE id = :carrier_id
    """)
    with engine.connect() as conn:
        row = conn.execute(query, {"carrier_id": carrier_id}).fetchone()
    if not row:
        return f"No carrier found with carrier_id {carrier_id}."

    return (
        f"MC number: {row.mc_number}\n"
        f"Safety rating: {row.safety_rating}, out-of-service violations: {row.oos_violations}, insurance: {row.insurance_status}\n"
        f"Elevated Risk: {bool(row.elevated_risk)}"
    )
