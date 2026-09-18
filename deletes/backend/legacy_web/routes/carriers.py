"""Carrier Management. Carrier profile plus real performance aggregates
(loads on file, invoice history, dispute count) — but nothing about a
carrier's external safety/compliance standing, which lives in TransCheck,
a genuinely separate system this one has no visibility into."""
# ------------------------------------------
# IMPORTS
# ------------------------------------------
from fastapi import APIRouter, Request
from sqlalchemy import text

from backend.legacy_web.db import admin_engine
from backend.legacy_web.render import templates

router = APIRouter(prefix="/carriers")


# ------------------------------------------
# SEARCH FORM — pick a carrier ID
# ------------------------------------------
@router.get("")
def search(request: Request):
    return templates.TemplateResponse(request, "carrier_search.html", {})


# ------------------------------------------
# PERFORMANCE STATS — real aggregates computed from this carrier's own loads
# and invoices; nothing about safety/compliance, which isn't this system's data
# ------------------------------------------
def carrier_stats(carrier_id: int):
    with admin_engine.connect() as conn:
        loads = conn.execute(
            text("SELECT COUNT(*) FROM dbo.tbl_load_bkg_raw WHERE car_id = :id"), {"id": carrier_id}
        ).scalar()
        invoices = conn.execute(
            text("SELECT COUNT(*), AVG(tot_amt) FROM dbo.tbl_carr_invc_raw WHERE car_id = :id"),
            {"id": carrier_id},
        ).one()
        disputes = conn.execute(
            text(
                "SELECT COUNT(*) FROM ("
                "  SELECT DISTINCT ON (d.invc_id) d.invc_id, d.dcsn_cd FROM dbo.tbl_ap_invc_dcsn_raw d "
                "  JOIN dbo.tbl_carr_invc_raw i ON i.invc_id = d.invc_id "
                "  WHERE i.car_id = :id ORDER BY d.invc_id, d.dcsn_ts DESC"
                ") latest WHERE dcsn_cd = 'HOLD'"
            ),
            {"id": carrier_id},
        ).scalar()
    return {"loads": loads, "invoice_count": invoices[0], "avg_invoice": invoices[1], "disputes": disputes}


# ------------------------------------------
# CARRIER DETAIL — raw carrier master fields + real performance aggregates
# ------------------------------------------
@router.get("/carrier")
def carrier_detail(request: Request, carrier_id: int):
    with admin_engine.connect() as conn:
        carrier = conn.execute(
            text("SELECT * FROM dbo.tbl_carr_mstr WHERE car_id = :id"),
            {"id": carrier_id},
        ).mappings().first()
    stats = carrier_stats(carrier_id) if carrier else None
    return templates.TemplateResponse(
        request, "carrier_detail.html", {"carrier_id": carrier_id, "carrier": carrier, "stats": stats}
    )
