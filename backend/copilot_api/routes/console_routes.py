"""The two every-role, read-oriented endpoints: the chat widget's one
endpoint, and the invoice list + dashboard counts."""
# ------------------------------------------
# IMPORTS
# ------------------------------------------
from fastapi import APIRouter, Depends
from pydantic import BaseModel
from sqlalchemy import text

from backend.copilot_api.auth import ChatThread, User, get_chat_thread, require_tab
from backend.copilot_api.routes.invoice_routes import _derive_ai_status
from copilot.agent_runner import ask
from copilot.dashboard_summary import get_flag_summary, get_shipment_status_summary
from copilot.identity import get_role_engine
from copilot.orchestrator import load_system_prompt, northstar_agent

router = APIRouter(prefix="/api/ai")


# ------------------------------------------
# AGENT CHAT — one message in, one response out. Used by the floating
# chat widget (nav.js) for free-form questions; the invoice page's own
# review flow is POST /invoices/{shipment_id}/review, not this.
# ------------------------------------------
class ChatBody(BaseModel):
    message: str


@router.post("/chat")
def chat(body: ChatBody, user: User = Depends(require_tab("chat")), thread: ChatThread = Depends(get_chat_thread)):
    thread_config = {"configurable": {"thread_id": thread.thread_id}}
    if not thread.initialized:
        northstar_agent.invoke({"messages": [load_system_prompt()]}, config=thread_config)
        thread.initialized = True
    response = ask(body.message, thread_config, role=user.role)
    return {"response": response}


# ------------------------------------------
# INVOICE LIST — every invoice with its current AI review status, one
# table the dashboard filters client-side (by clicking a KPI) instead of
# maintaining two separate "reviewed" / "not reviewed" queries — the same
# data source both power. aiStatus comes from ai_invoice_reviews (see
# _derive_ai_status) — a clean invoice has no dispute_flags row but still
# gets a real status once reviewed.
# ------------------------------------------
@router.get("/invoices")
def list_invoices(user: User = Depends(require_tab("dashboard"))):
    engine = get_role_engine(user.role)
    with engine.connect() as conn:
        rows = conn.execute(text("""
            SELECT DISTINCT ON (i.shipment_id)
                   i.shipment_id AS "shipmentId", c.name AS "carrierName", i.total_amount AS "totalAmount",
                   f.flag_id AS "flagId", f.tier, f.status,
                   r.reviewed_at AS "reviewedAt", r.decision
            FROM invoices i
            JOIN carriers c ON c.id = i.carrier_id
            LEFT JOIN dispute_flags f ON f.shipment_id = i.shipment_id
            LEFT JOIN ai_invoice_reviews r ON r.shipment_id = i.shipment_id
            ORDER BY i.shipment_id, f.flag_id DESC
        """)).mappings().all()
    return [
        {**dict(r), "aiStatus": _derive_ai_status(r["decision"], r["reviewedAt"])}
        for r in rows
    ]


# ------------------------------------------
# DASHBOARD — the counts an invoice list alone can't give: Elevated Risk
# carriers (a carrier property, not an invoice one) and shipment status
# (derived from dock events, not dispute_flags). Every role can reach it.
# ------------------------------------------
@router.get("/dashboard")
def dashboard(user: User = Depends(require_tab("dashboard"))):
    engine = get_role_engine(user.role)
    flags = get_flag_summary(engine)
    shipments = get_shipment_status_summary(engine)

    return {
        "elevatedRiskCarriers": flags.elevated_risk_carriers,
        "shipments": {
            "scheduled": shipments.scheduled,
            "enroute": shipments.enroute,
            "atDock": shipments.at_dock,
            "delivered": shipments.delivered,
        },
    }
