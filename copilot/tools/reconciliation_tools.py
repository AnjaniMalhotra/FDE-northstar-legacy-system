"""Reconciliation — the facts, not the verdict. Whether a discrepancy is big
enough to flag is a policy question (policy_tools.py / flag_tools.py), never
decided here."""
# ------------------------------------------
# IMPORTS
# ------------------------------------------
from langchain_core.tools import tool
from sqlalchemy import text

from copilot.database import engine
from copilot.reconciliation_detention import format_reconciliation, get_reconciliation
from copilot.reconciliation_linehaul import format_linehaul_reconciliation, get_linehaul_reconciliation


# ------------------------------------------
# CHECK DETENTION RECONCILIATION — compare actual vs. billed detention
# ------------------------------------------
@tool
def check_detention_reconciliation(shipment_id: int) -> str:
    """
    Computes the ACTUAL detention time for a shipment from real dock arrival/
    departure timestamps, and compares it to what the carrier BILLED on the
    invoice. Returns the raw facts (actual vs. billed hours and dollars) —
    it does not decide whether the difference counts as a flaggable
    discrepancy. Use search_policy_documents to find that threshold.
    """
    try:
        result = get_reconciliation(engine, shipment_id)
        if not result:
            return f"No data found for shipment_id {shipment_id}."
        return format_reconciliation(result)
    except Exception as e:
        return f"Reconciliation error: {e}"


# ------------------------------------------
# CHECK LINEHAUL RECONCILIATION — compare the agreed rate to billed linehaul
# ------------------------------------------
@tool
def check_linehaul_reconciliation(shipment_id: int) -> str:
    """
    Compares the linehaul rate AGREED when the shipment was booked to what
    the carrier actually BILLED on the invoice. Returns the raw facts
    (agreed vs. billed dollars) — it does not decide whether the difference
    counts as a flaggable discrepancy. Use search_policy_documents to find
    that threshold (linehaul_rate_policy.md). Unlike detention, there's no
    time dimension here — this is a flat rate comparison.
    """
    try:
        result = get_linehaul_reconciliation(engine, shipment_id)
        if not result:
            return f"No data found for shipment_id {shipment_id}."
        return format_linehaul_reconciliation(result)
    except Exception as e:
        return f"Reconciliation error: {e}"


# ------------------------------------------
# GET INVOICE DETAILS — one invoice's full charges, route, and review status
# ------------------------------------------
@tool
def get_invoice_details(shipment_id: int) -> str:
    """
    Looks up ONE specific invoice by its shipment id: carrier, route,
    submitted date, every charge on the invoice (linehaul, fuel surcharge,
    detention, total), the AI's review status (not yet reviewed /
    auto-logged / pending approval / approved / rejected, with the
    reasoning on file if any), and Northstar's own human AP decision if one
    has been recorded (a separate record from the AI's review). Use this
    whenever the question names a specific invoice/shipment number and wants to know
    about it generally — NOT get_carrier_invoice_history, which takes a
    carrier id and lists many invoices; a bare "invoice 21" or "shipment
    21" means THIS tool.
    """
    query = text("""
        SELECT i.id AS invoice_id, i.shipment_id, i.submitted_at, i.linehaul_amount, i.fuel_surcharge,
               i.detention_hours_billed, i.detention_amount_billed, i.total_amount,
               s.origin, s.dest, c.name AS carrier_name
        FROM invoices i
        JOIN shipments s ON s.id = i.shipment_id
        JOIN carriers c ON c.id = i.carrier_id
        WHERE i.shipment_id = :shipment_id
    """)
    flag_query = text("""
        SELECT tier, status, reasoning, discrepancy_amount FROM dispute_flags
        WHERE shipment_id = :shipment_id ORDER BY flag_id DESC LIMIT 1
    """)
    ap_decision_query = text("""
        SELECT decision, note, at FROM invoice_decisions
        WHERE invoice_id = (SELECT id FROM invoices WHERE shipment_id = :shipment_id)
        ORDER BY at DESC LIMIT 1
    """)
    with engine.connect() as conn:
        row = conn.execute(query, {"shipment_id": shipment_id}).fetchone()
        if not row:
            return f"No invoice found for shipment_id {shipment_id}."
        flag = conn.execute(flag_query, {"shipment_id": shipment_id}).fetchone()
        ap_decision = conn.execute(ap_decision_query, {"shipment_id": shipment_id}).fetchone()

    summary = (
        f"Invoice {row.invoice_id} (shipment {row.shipment_id}), {row.carrier_name}, "
        f"{row.origin} -> {row.dest}, submitted {row.submitted_at}. "
        f"Linehaul ${row.linehaul_amount}, fuel surcharge ${row.fuel_surcharge}, "
        f"detention {row.detention_hours_billed}hrs/${row.detention_amount_billed}, total ${row.total_amount}."
    )
    if flag:
        summary += f" AI review status: {flag.tier}/{flag.status}, ${flag.discrepancy_amount} discrepancy — {flag.reasoning}"
    else:
        summary += " AI review status: not yet reviewed."
    if ap_decision:
        summary += f" Northstar AP decision on file: {ap_decision.decision} ({ap_decision.at})" + (f" — {ap_decision.note}" if ap_decision.note else "")
    return summary
