"""Northstar AP — Invoice Processing. Raw invoice lookup plus a real
Approve/Hold decision action — the one piece of this whole simulation
that actually changes data, mirroring what an AP clerk really does."""
# ------------------------------------------
# IMPORTS
# ------------------------------------------
from fastapi import APIRouter, Form, Request
from fastapi.responses import RedirectResponse
from sqlalchemy import text

from backend.legacy_web.db import admin_engine
from backend.legacy_web.render import templates

router = APIRouter(prefix="/ap")


# ------------------------------------------
# PENDING INVOICES — real invoices with no decision recorded yet, oldest first
# ------------------------------------------
def pending_invoices(limit: int = 15):
    with admin_engine.connect() as conn:
        return conn.execute(
            text(
                "SELECT i.invc_id, i.ld_id, c.car_nm, i.tot_amt "
                "FROM dbo.tbl_carr_invc_raw i "
                "JOIN dbo.tbl_carr_mstr c ON c.car_id = i.car_id "
                "LEFT JOIN dbo.tbl_ap_invc_dcsn_raw d ON d.invc_id = i.invc_id "
                "WHERE d.dcsn_id IS NULL "
                "ORDER BY i.invc_id LIMIT :limit"
            ),
            {"limit": limit},
        ).mappings().all()


# ------------------------------------------
# DECISION COUNTS — real counts by latest decision per invoice, for dashboard tiles
# ------------------------------------------
def decision_counts():
    with admin_engine.connect() as conn:
        pending = conn.execute(
            text(
                "SELECT COUNT(*) FROM dbo.tbl_carr_invc_raw i "
                "LEFT JOIN dbo.tbl_ap_invc_dcsn_raw d ON d.invc_id = i.invc_id "
                "WHERE d.dcsn_id IS NULL"
            )
        ).scalar()
        rows = conn.execute(
            text(
                "SELECT dcsn_cd, COUNT(*) AS n FROM ("
                "  SELECT DISTINCT ON (invc_id) invc_id, dcsn_cd FROM dbo.tbl_ap_invc_dcsn_raw"
                "  ORDER BY invc_id, dcsn_ts DESC"
                ") latest GROUP BY dcsn_cd"
            )
        ).mappings().all()
    counts = {"PENDING": pending, "APPROVED": 0, "HOLD": 0}
    counts.update({r["dcsn_cd"]: r["n"] for r in rows})
    return counts


# ------------------------------------------
# RECENT ACTIVITY — the latest decisions made, for the intranet homepage
# ------------------------------------------
def recent_activity(limit: int = 5):
    with admin_engine.connect() as conn:
        return conn.execute(
            text(
                "SELECT d.invc_id, c.car_nm, d.dcsn_cd, d.dcsn_ts "
                "FROM dbo.tbl_ap_invc_dcsn_raw d "
                "JOIN dbo.tbl_carr_invc_raw i ON i.invc_id = d.invc_id "
                "JOIN dbo.tbl_carr_mstr c ON c.car_id = i.car_id "
                "ORDER BY d.dcsn_ts DESC LIMIT :limit"
            ),
            {"limit": limit},
        ).mappings().all()


# ------------------------------------------
# QUEUE + SEARCH — the pending-invoice queue, plus lookup-by-ID
# ------------------------------------------
@router.get("")
def search(request: Request):
    return templates.TemplateResponse(
        request, "ap_search.html", {"queue": pending_invoices(), "counts": decision_counts(), "active": "queue"}
    )


# ------------------------------------------
# INVOICE DETAIL — raw invoice fields + this invoice's decision history
# ------------------------------------------
@router.get("/invoice")
def invoice_detail(request: Request, invoice_id: int):
    with admin_engine.connect() as conn:
        invoice = conn.execute(
            text("SELECT * FROM dbo.tbl_carr_invc_raw WHERE invc_id = :id"),
            {"id": invoice_id},
        ).mappings().first()
        decisions = conn.execute(
            text(
                "SELECT * FROM dbo.tbl_ap_invc_dcsn_raw WHERE invc_id = :id "
                "ORDER BY dcsn_ts DESC"
            ),
            {"id": invoice_id},
        ).mappings().all()
    status = decisions[0]["dcsn_cd"] if decisions else "PENDING"
    return templates.TemplateResponse(
        request,
        "ap_detail.html",
        {"invoice_id": invoice_id, "invoice": invoice, "decisions": decisions, "status": status, "active": "queue"},
    )


# ------------------------------------------
# CONFIRM DECISION — a deliberate second step before Approve/Hold takes effect
# ------------------------------------------
@router.get("/invoice/{invoice_id}/decision/confirm")
def confirm_decision(request: Request, invoice_id: int, dcsn_cd: str):
    with admin_engine.connect() as conn:
        invoice = conn.execute(
            text("SELECT * FROM dbo.tbl_carr_invc_raw WHERE invc_id = :id"),
            {"id": invoice_id},
        ).mappings().first()
    return templates.TemplateResponse(
        request, "ap_confirm.html", {"invoice": invoice, "dcsn_cd": dcsn_cd, "active": "queue"}
    )


# ------------------------------------------
# RECORD DECISION — Approve/Hold, written straight to the legacy table
# ------------------------------------------
@router.post("/invoice/{invoice_id}/decision")
def record_decision(
    invoice_id: int,
    dcsn_cd: str = Form(...),
    dcsn_by_txt: str = Form(...),
    dcsn_note_txt: str = Form(""),
):
    with admin_engine.begin() as conn:
        conn.execute(
            text(
                "INSERT INTO dbo.tbl_ap_invc_dcsn_raw (invc_id, dcsn_cd, dcsn_by_txt, dcsn_note_txt) "
                "VALUES (:invc_id, :dcsn_cd, :dcsn_by_txt, :dcsn_note_txt)"
            ),
            {
                "invc_id": invoice_id,
                "dcsn_cd": dcsn_cd,
                "dcsn_by_txt": dcsn_by_txt,
                "dcsn_note_txt": dcsn_note_txt,
            },
        )
    return RedirectResponse(f"/ap/invoice?invoice_id={invoice_id}", status_code=303)
