"""The agent's one write-capable action. Two gates must both pass before
anything is written: an access-policy check (does this role's AI session
even have this capability?) and an evidence check (was real POLICY content
actually retrieved this turn?) — either one refusing is enough to stop the
write."""
# ------------------------------------------
# IMPORTS
# ------------------------------------------
import json

from langchain_core.runnables import RunnableConfig
from langchain_core.tools import tool
from sqlalchemy import text

from copilot import access_policy
from copilot.database import engine
from copilot.guardrails import authorize_flag, authorize_linehaul_flag
from copilot.reconciliation_detention import get_reconciliation
from copilot.reconciliation_linehaul import get_linehaul_reconciliation
from copilot.tracing import has_policy_evidence


# ------------------------------------------
# LOG DISPUTE FLAG — the agent's one write-capable action
# ------------------------------------------
@tool
def log_dispute_flag(shipment_id: int, reasoning: str, config: RunnableConfig, charge_type: str = "DETENTION") -> str:
    """
    Records a dispute flag for an invoice discrepancy on the given shipment.
    This is the ONLY write-capable action this agent has, and it never
    disputes a charge, holds a payment, or blocks a carrier itself — it
    only logs a flag.

    charge_type is "DETENTION" (default) or "LINEHAUL" — which charge the
    discrepancy is about, matching whichever reconciliation tool you called
    (check_detention_reconciliation or check_linehaul_reconciliation). You
    only supply the shipment ID, reasoning, and charge_type. The tool
    derives the invoice, carrier, billed-vs-agreed/actual variance, and
    tier from the database; it never trusts an LLM-supplied discrepancy
    amount. A Tier 1 flag is AUTO_LOGGED; a Tier 2 flag is
    PENDING_APPROVAL and requires a human reviewer. You must have already
    called search_policy_documents and gotten a real POLICY result (not
    just a SOP/MEMO one, and not an abstain) earlier in this conversation,
    or this call is refused.
    """
    # ------------------------------------------
    # PULL TRACE/ROLE/SESSION CONTEXT OFF THE CONFIG
    # ------------------------------------------
    trace_id = config["configurable"]["trace_id"]
    role = config["configurable"].get("role", "")
    session_id = config["configurable"].get("thread_id", "")

    # ------------------------------------------
    # GATE CHECKS — refuse if role lacks capability or no policy evidence exists
    # ------------------------------------------
    if not access_policy.can_use_ai_tool(role, "log_dispute_flag"):
        return (f"Refused: the {role} role's AI session does not have flag-logging capability "
                f"(see data/policy/access_policy.json) — flags are proposed by Analysts/Managers.")
    if not has_policy_evidence(trace_id):
        return ("Refused: no POLICY evidence found for this trace. Call search_policy_documents "
                "and confirm it returned real POLICY content (not just SOP/MEMO, and not an "
                "abstain) before logging a flag.")
    if charge_type not in ("DETENTION", "LINEHAUL"):
        return f"Refused: charge_type must be DETENTION or LINEHAUL, got {charge_type!r}."

    # ------------------------------------------
    # DEDUP CHECK — refuse a second flag for the same shipment+charge while
    # one is still open. Nothing stops the LLM from calling this tool twice
    # for the same discrepancy — observed live, both within one turn (a
    # reasoner re-evaluating mid-turn) and across turns (the same question
    # asked twice) — so this is enforced here, deterministically, not left
    # to prompting alone.
    # ------------------------------------------
    with engine.connect() as conn:
        existing = conn.execute(text("""
            SELECT flag_id FROM dispute_flags
            WHERE shipment_id = :shipment_id AND charge_type = :charge_type
              AND status IN ('AUTO_LOGGED', 'PENDING_APPROVAL')
            ORDER BY flag_id DESC LIMIT 1
        """), {"shipment_id": shipment_id, "charge_type": charge_type}).fetchone()
    if existing:
        return f"Not logged: flag {existing.flag_id} for this shipment's {charge_type.lower()} charge is already open, pending review."

    try:
        # ------------------------------------------
        # COMPUTE RECONCILIATION & AUTHORIZE THE FLAG — the matching pair for this charge type
        # ------------------------------------------
        if charge_type == "LINEHAUL":
            result = get_linehaul_reconciliation(engine, shipment_id)
            if not result:
                return f"Cannot log a flag: no invoice found for shipment_id {shipment_id}."
            auth = authorize_linehaul_flag(engine, result)
        else:
            result = get_reconciliation(engine, shipment_id)
            if not result:
                return f"Cannot log a flag: no invoice found for shipment_id {shipment_id}."
            auth = authorize_flag(engine, result)
        if not auth.is_flaggable:
            return auth.reason
        status = "AUTO_LOGGED" if auth.can_auto_log else "PENDING_APPROVAL"

        # ------------------------------------------
        # BUILD THE INSERT STATEMENTS — flag record and its audit-log entry
        # ------------------------------------------
        insert_flag = text("""
            INSERT INTO dispute_flags
                (shipment_id, invoice_id, carrier_id, discrepancy_amount, tier, status, reasoning, tier_reason, charge_type)
            VALUES (:shipment_id, :invoice_id, :carrier_id, :discrepancy_amount, :tier, :status, :reasoning, :tier_reason, :charge_type)
        """)
        insert_audit = text("""
            INSERT INTO agent_audit_log
                (session_id, node_name, tool_name, content, trace_id, role, metadata)
            VALUES (:session_id, 'tools', 'log_dispute_flag', :content, :trace_id, :role, :metadata)
        """)
        summary = f"Flag recorded for carrier_id {result.carrier_id} as {auth.tier} / {status} ({charge_type}). {auth.reason}"

        # ------------------------------------------
        # ATOMIC WRITE — commit the flag and its audit record together
        # ------------------------------------------
        # Atomic: the flag and the audit record confirming it exist commit
        # together, or neither does — no window where one exists without the other.
        with engine.begin() as conn:
            conn.execute(insert_flag, {
                "shipment_id": result.shipment_id, "invoice_id": result.invoice_id, "carrier_id": result.carrier_id,
                "discrepancy_amount": result.amount_variance, "tier": auth.tier,
                "status": status, "reasoning": reasoning, "tier_reason": auth.reason, "charge_type": charge_type,
            })
            conn.execute(insert_audit, {
                "session_id": session_id, "content": summary, "trace_id": trace_id, "role": role,
                "metadata": json.dumps({"shipment_id": shipment_id, "tier": auth.tier, "status": status, "policy_version": auth.policy_version, "charge_type": charge_type}),
            })
        return summary
    except Exception as e:
        return f"Failed to log flag: {e}"
