"""The two Manager+/Admin action tabs: Pending Approvals (approve/reject a
flag) and the Audit Log those actions get recorded to."""
# ------------------------------------------
# IMPORTS
# ------------------------------------------
from fastapi import APIRouter, Depends
from sqlalchemy import text

from backend.copilot_api.auth import User, require_tab
from copilot.identity import get_role_engine

router = APIRouter(prefix="/api/ai")


# ------------------------------------------
# PENDING APPROVALS — Manager+: approve or reject a flag
# ------------------------------------------
@router.get("/flags/pending")
def pending_flags(user: User = Depends(require_tab("approvals"))):
    engine = get_role_engine(user.role)
    with engine.connect() as conn:
        rows = conn.execute(text("""
            SELECT flag_id AS "flagId", shipment_id AS "shipmentId", carrier_id AS "carrierId",
                   discrepancy_amount AS "discrepancyAmount", tier, reasoning, created_at AS "createdAt"
            FROM dispute_flags WHERE status = 'PENDING_APPROVAL' ORDER BY flag_id
        """)).mappings().all()
    return list(rows)


@router.post("/flags/{flag_id}/approve")
def approve_flag(flag_id: int, user: User = Depends(require_tab("approvals"))):
    engine = get_role_engine(user.role)
    with engine.begin() as conn:
        conn.execute(text("""UPDATE dispute_flags SET status='APPROVED',
                        resolved_by=:reviewer, resolved_at=NOW() WHERE flag_id=:id"""),
                     {"reviewer": user.user_id, "id": flag_id})
    return {"ok": True}


@router.post("/flags/{flag_id}/reject")
def reject_flag(flag_id: int, user: User = Depends(require_tab("approvals"))):
    engine = get_role_engine(user.role)
    with engine.begin() as conn:
        conn.execute(text("""UPDATE dispute_flags SET status='REJECTED',
                        resolved_by=:reviewer, resolved_at=NOW() WHERE flag_id=:id"""),
                     {"reviewer": user.user_id, "id": flag_id})
    return {"ok": True}


# ------------------------------------------
# AUDIT LOG — Manager+: every agent action, recorded
# ------------------------------------------
@router.get("/audit-log")
def audit_log(user: User = Depends(require_tab("audit"))):
    engine = get_role_engine(user.role)
    with engine.connect() as conn:
        rows = conn.execute(text("""
            SELECT log_id AS "logId", logged_at AS "loggedAt", trace_id AS "traceId", role,
                   node_name AS "nodeName", tool_name AS "toolName", content, metadata
            FROM agent_audit_log ORDER BY log_id DESC LIMIT 100
        """)).mappings().all()
    return list(rows)
