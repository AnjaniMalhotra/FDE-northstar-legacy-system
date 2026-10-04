"""Invoice detail, the AI review flow, and a human's Approve/Hold decision —
one thin function per action, reusing copilot.identity.get_role_engine (the
logged-in user's own restricted DB role) and copilot.agent_runner.ask.

SQL results are aliased directly to camelCase in the SELECT itself, so no
generic snake_case<->camelCase translation layer is needed here (unlike the
separate legacy project's northstar_web_api/naming.py, which exists because
that API is generic over arbitrary tables — these queries are hand-written
and fixed)."""
# ------------------------------------------
# IMPORTS
# ------------------------------------------
import json

from fastapi import APIRouter, Depends, HTTPException
from pydantic import BaseModel
from sqlalchemy import text

from backend.copilot_api.auth import ChatThread, User, get_ai_user, get_chat_thread, require_tab
from copilot.agent_runner import ask
from copilot.database import engine as agent_engine
from copilot.identity import get_role_engine
from copilot.orchestrator import load_system_prompt, northstar_agent
from copilot.plain_language import plain_language_linehaul_policy_line, plain_language_outcome, plain_language_policy_line
from copilot.reconciliation_detention import get_reconciliation, plain_language_facts
from copilot.reconciliation_linehaul import get_linehaul_reconciliation, plain_language_linehaul_facts

router = APIRouter(prefix="/api/ai")


# ------------------------------------------
# DERIVE AI STATUS — reviewed-but-undecided/approved/on-hold/not-reviewed,
# from ai_invoice_reviews — decoupled from whether a dispute_flags row
# exists, since a clean invoice never gets one but still needs a human
# decision. Also used by console_routes.list_invoices.
# ------------------------------------------
def _derive_ai_status(review_decision: str | None, reviewed_at) -> str:
    if reviewed_at is None:
        return "NOT_REVIEWED"
    if review_decision == "APPROVED":
        return "APPROVED"
    if review_decision == "ON_HOLD":
        return "ON_HOLD"
    return "AWAITING_DECISION"


# ------------------------------------------
# INVOICE DETAIL — one invoice's charges, its current AI review status, and
# Northstar's own human AP decision (invoice_decisions) shown alongside it
# — two separate records, deliberately kept separate rather than merged.
# ------------------------------------------
@router.get("/invoices/{shipment_id}")
def get_invoice(shipment_id: int, user: User = Depends(get_ai_user)):
    engine = get_role_engine(user.role)
    with engine.connect() as conn:
        invoice = conn.execute(text("""
            SELECT i.id AS "invoiceId", i.shipment_id AS "shipmentId", i.submitted_at AS "submittedAt",
                   i.linehaul_amount AS "linehaulAmount", i.fuel_surcharge AS "fuelSurcharge",
                   i.detention_hours_billed AS "detentionHoursBilled", i.detention_amount_billed AS "detentionAmountBilled",
                   i.total_amount AS "totalAmount",
                   s.origin AS "origin", s.dest AS "dest",
                   s.pickup_appt AS "pickupAppt", s.delivery_appt AS "deliveryAppt",
                   c.id AS "carrierId", c.name AS "carrierName"
            FROM invoices i
            JOIN shipments s ON s.id = i.shipment_id
            JOIN carriers c ON c.id = i.carrier_id
            WHERE i.shipment_id = :shipment_id
        """), {"shipment_id": shipment_id}).mappings().first()
        if not invoice:
            raise HTTPException(status_code=404, detail=f"No invoice found for shipment {shipment_id}.")

        flag = conn.execute(text("""
            SELECT flag_id AS "flagId", tier, status, reasoning,
                   discrepancy_amount AS "discrepancyAmount", created_at AS "createdAt"
            FROM dispute_flags WHERE shipment_id = :shipment_id ORDER BY flag_id DESC LIMIT 1
        """), {"shipment_id": shipment_id}).mappings().first()

        review = conn.execute(text("""
            SELECT reviewed_at AS "reviewedAt", decision, decided_by AS "decidedBy", decided_at AS "decidedAt",
                   ai_review AS "aiReview"
            FROM ai_invoice_reviews WHERE shipment_id = :shipment_id
        """), {"shipment_id": shipment_id}).mappings().first()

        ap_decision = conn.execute(text("""
            SELECT decision, decided_by AS "decidedBy", note, at
            FROM invoice_decisions WHERE invoice_id = :invoice_id ORDER BY at DESC LIMIT 1
        """), {"invoice_id": invoice["invoiceId"]}).mappings().first()

    ai_status = _derive_ai_status(review["decision"] if review else None, review["reviewedAt"] if review else None)
    return {
        "invoice": dict(invoice),
        "flag": dict(flag) if flag else None,
        "review": dict(review) if review else None,
        "apDecision": dict(ap_decision) if ap_decision else None,
        "aiStatus": ai_status,
    }


# ------------------------------------------
# BUILD CHECKS — the plain-language breakdown for both charge types,
# independently derived from the same database facts guardrails.py itself
# trusts — never from the LLM's own wording. Shared by the live review
# flow and the backfill script, so both build the exact same shape.
# ------------------------------------------
def _build_checks(engine, shipment_id: int) -> list[dict]:
    checks = []
    with engine.connect() as conn:
        latest_flag_by_charge = {
            row["chargeType"]: row
            for row in conn.execute(text("""
                SELECT DISTINCT ON (charge_type) charge_type AS "chargeType", tier, tier_reason AS "tierReason"
                FROM dispute_flags
                WHERE shipment_id = :shipment_id
                ORDER BY charge_type, flag_id DESC
            """), {"shipment_id": shipment_id}).mappings().all()
        }

    detention = get_reconciliation(engine, shipment_id)
    detention_flag = latest_flag_by_charge.get("DETENTION")
    checks.append({
        "title": "Detention Check",
        "facts": plain_language_facts(detention) if detention else [],
        "policyLine": plain_language_policy_line(),
        "outcomeLine": plain_language_outcome(
            detention_flag["tier"] if detention_flag else None,
            detention_flag["tierReason"] if detention_flag else "",
        ),
    })

    linehaul = get_linehaul_reconciliation(engine, shipment_id)
    linehaul_flag = latest_flag_by_charge.get("LINEHAUL")
    checks.append({
        "title": "Linehaul Check",
        "facts": plain_language_linehaul_facts(linehaul) if linehaul else [],
        "policyLine": plain_language_linehaul_policy_line(),
        "outcomeLine": plain_language_outcome(
            linehaul_flag["tier"] if linehaul_flag else None,
            linehaul_flag["tierReason"] if linehaul_flag else "",
        ),
    })
    return checks


# ------------------------------------------
# REVIEW INVOICE — runs the agent once (for its recommendation text and to
# let it log a flag for either charge if warranted), then independently
# derives a plain-language breakdown for both Detention and Linehaul from
# the same database facts guardrails.py itself trusts — never from the
# LLM's own wording, so it can't drift or vary in phrasing between
# invoices. Persisted once, in the same INSERT that already records "the
# AI looked at this invoice" (see ai_invoice_reviews' own history) — so a
# reopened invoice shows the identical breakdown instead of just
# dispute_flags' one-line reasoning.
# ------------------------------------------
@router.post("/invoices/{shipment_id}/review")
def review_invoice(shipment_id: int, user: User = Depends(get_ai_user), thread: ChatThread = Depends(get_chat_thread)):
    thread_config = {"configurable": {"thread_id": thread.thread_id}}
    if not thread.initialized:
        northstar_agent.invoke({"messages": [load_system_prompt()]}, config=thread_config)
        thread.initialized = True

    question = (f"Are the detention and linehaul charges on shipment {shipment_id} legitimate? "
                f"Check both against our policy, and log a flag for either one if warranted.")
    recommendation = ask(question, thread_config, role=user.role)

    ai_review = {"checks": _build_checks(agent_engine, shipment_id), "recommendation": recommendation}

    with agent_engine.begin() as conn:
        conn.execute(text("""
            INSERT INTO ai_invoice_reviews (shipment_id, ai_review) VALUES (:shipment_id, :ai_review)
            ON CONFLICT (shipment_id) DO NOTHING
        """), {"shipment_id": shipment_id, "ai_review": json.dumps(ai_review)})

    return {"aiReview": ai_review}


# ------------------------------------------
# DECIDE — a human's Approve/Hold call on the AI's own review of one
# invoice. Manager+/Admin only (same roles who can already resolve a
# dispute_flags row). This writes ai_invoice_reviews.decision, NOT
# Northstar's own invoice_decisions — that table records Northstar AP's
# real payment-authorization decision and stays theirs to write. If a flag
# is still open for this shipment, its status is kept in sync so
# approvals.html doesn't silently diverge from this.
# ------------------------------------------
class DecisionBody(BaseModel):
    decision: str  # "APPROVED" or "ON_HOLD"


@router.post("/invoices/{shipment_id}/decision")
def decide_invoice(shipment_id: int, body: DecisionBody, user: User = Depends(require_tab("approvals"))):
    if body.decision not in ("APPROVED", "ON_HOLD"):
        raise HTTPException(status_code=400, detail="decision must be APPROVED or ON_HOLD.")
    engine = get_role_engine(user.role)
    with engine.begin() as conn:
        result = conn.execute(text("""
            UPDATE ai_invoice_reviews
            SET decision = :decision, decided_by = :reviewer, decided_at = NOW()
            WHERE shipment_id = :shipment_id
        """), {"decision": body.decision, "reviewer": user.user_id, "shipment_id": shipment_id})
        if result.rowcount == 0:
            raise HTTPException(status_code=404, detail=f"Shipment {shipment_id} has not been AI-reviewed yet.")

        flag_status = "APPROVED" if body.decision == "APPROVED" else "REJECTED"
        conn.execute(text("""
            UPDATE dispute_flags SET status = :flag_status, resolved_by = :reviewer, resolved_at = NOW()
            WHERE shipment_id = :shipment_id AND status IN ('AUTO_LOGGED', 'PENDING_APPROVAL')
        """), {"flag_status": flag_status, "reviewer": user.user_id, "shipment_id": shipment_id})
    return {"ok": True}
