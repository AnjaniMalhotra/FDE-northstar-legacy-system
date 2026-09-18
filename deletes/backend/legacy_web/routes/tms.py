"""Northstar TMS — Load Booking. Where the agreed rate and detention terms
for a load live — on a completely different screen from the invoice
that has to be checked against them."""
# ------------------------------------------
# IMPORTS
# ------------------------------------------
from fastapi import APIRouter, Request
from sqlalchemy import text

from backend.legacy_web.db import admin_engine
from backend.legacy_web.render import templates

router = APIRouter(prefix="/tms")


# ------------------------------------------
# SEARCH FORM — pick a load ID
# ------------------------------------------
@router.get("")
def search(request: Request):
    return templates.TemplateResponse(request, "tms_search.html", {})


# ------------------------------------------
# LOAD DETAIL — raw booking fields (agreed rate, free time, detention rate)
# ------------------------------------------
@router.get("/load")
def load_detail(request: Request, load_id: int):
    with admin_engine.connect() as conn:
        load = conn.execute(
            text("SELECT * FROM dbo.tbl_load_bkg_raw WHERE ld_id = :id"),
            {"id": load_id},
        ).mappings().first()
    return templates.TemplateResponse(request, "tms_detail.html", {"load_id": load_id, "load": load})
