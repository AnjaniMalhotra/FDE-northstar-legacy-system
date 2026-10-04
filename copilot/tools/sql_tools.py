"""The general-purpose, validated SQL lookup tool — a fallback for
questions the named tools (carrier_tools.py, reconciliation_tools.py) don't
cover."""
# ------------------------------------------
# IMPORTS
# ------------------------------------------
import sqlglot
from langchain_core.tools import tool
from sqlalchemy import text
from sqlglot import exp

from copilot.database import engine

# ------------------------------------------
# ALLOWED_QUERY_TABLES — the only tables this tool is allowed to touch.
# Legacy-owned tables (carriers, shipments, dock_events, invoices,
# invoice_decisions) are read-only here — this tool never writes anything,
# and the agent's own Postgres role has no write grant on them either way.
# ------------------------------------------
ALLOWED_QUERY_TABLES = {
    "carriers", "shipments", "dock_events", "invoices", "invoice_decisions",
    "dispute_flags", "ai_invoice_reviews",
}


# ------------------------------------------
# VALIDATE SELECT QUERY — parse and check the SQL before it's ever run
# ------------------------------------------
def _validate_select_query(sql_query: str) -> str | None:
    """Returns None if the query is safe to run, or an error string if not.
    Uses a real SQL parser (sqlglot), not a string-prefix check — a prefix
    check like ``.startswith("SELECT")`` doesn't catch a stacked query
    (``SELECT ...; DROP TABLE ...``) or a UNION pulling in a system table.
    This is defense in depth on top of the database's own RBAC, not a
    replacement for it — the agent's role still can't write to any of
    these tables, or read users/sessions/shipment_requests at all, even if
    this check were somehow bypassed."""
    # ------------------------------------------
    # PARSE THE QUERY
    # ------------------------------------------
    try:
        statements = [s for s in sqlglot.parse(sql_query, read="postgres") if s is not None]
    except Exception as e:
        return f"Could not parse query: {e}"

    # ------------------------------------------
    # REJECT ANYTHING BUT A SINGLE SELECT
    # ------------------------------------------
    if len(statements) != 1:
        return "Only a single SELECT statement is allowed — no stacked/multiple statements."
    if not isinstance(statements[0], (exp.Select, exp.Union)):
        return "Only SELECT statements are allowed."

    # ------------------------------------------
    # CHECK EVERY TABLE AGAINST THE ALLOWLIST
    # ------------------------------------------
    for table in statements[0].find_all(exp.Table):
        schema = table.db or None
        if schema not in (None, "", "public") or table.name not in ALLOWED_QUERY_TABLES:
            qualified = f"{schema}.{table.name}" if schema else table.name
            return f"SECURITY BLOCK: query references a table outside the allowed set: {qualified}"
    return None


# ------------------------------------------
# QUERY NORTHSTAR DATA — validated, read-only SQL lookup tool
# ------------------------------------------
@tool
def query_northstar_data(sql_query: str) -> str:
    """
    Runs a read-only SQL query against northstar_web's shipment/invoice/
    carrier data. No schema prefix is needed — everything is in the public
    schema. The exact columns on each table (guessing a column name that
    isn't listed here WILL fail with "column does not exist" — use exactly
    these names, nothing else):

    - carriers: id, name, mc_number, safety_rating, oos_violations, insurance_status,
      detention_free_hours, detention_rate_per_hour, rate_factor, elevated_risk
    - shipments: id, carrier_id, origin, dest, weight_lbs, goods_description,
      agreed_rate, detention_free_hours, detention_rate_per_hour, pickup_appt,
      delivery_appt, status
    - dock_events: id, shipment_id, type ('ARRIVAL'/'DEPARTURE'), timestamp
    - invoices: id, shipment_id, carrier_id, submitted_at, linehaul_amount,
      detention_hours_billed, detention_amount_billed, fuel_surcharge, total_amount, status
    - invoice_decisions: id, invoice_id, decided_by, decision, note, at — Northstar's own
      human AP decision record, separate from the AI's own review (ai_invoice_reviews)
    - dispute_flags: flag_id, shipment_id, invoice_id, carrier_id, discrepancy_amount,
      tier ('TIER_1'/'TIER_2'), status ('AUTO_LOGGED'/'PENDING_APPROVAL'/'APPROVED'/'REJECTED'),
      charge_type, reasoning, created_at, resolved_by, resolved_at, dispute_outcome
    - ai_invoice_reviews: shipment_id, reviewed_at, decision, decided_by, decided_at, ai_review

    Good for an ad-hoc business question none of the named tools cover (e.g.
    "how many Tier 2 flags total, regardless of status," "which carriers have
    more than 2 elevated-risk flags," "what's the maximum detention amount
    billed"). Only a single SELECT statement is allowed. Prefer the named
    tools (get_invoice_details, get_carrier_invoice_history, etc.) when one
    fits — use this only for a lookup none of them cover.
    """
    # ------------------------------------------
    # VALIDATE THE QUERY
    # ------------------------------------------
    error = _validate_select_query(sql_query)
    if error:
        return error
    # ------------------------------------------
    # RUN THE QUERY & FORMAT RESULTS
    # ------------------------------------------
    try:
        with engine.connect() as conn:
            result = conn.execute(text(sql_query))
            columns = list(result.keys())
            rows = result.fetchmany(20)
        if not rows:
            return "No rows matched."
        return f"COLUMNS: {', '.join(columns)}\n" + "\n".join(str(tuple(row)) for row in rows)
    except Exception as e:
        return f"Database error: {e}"
