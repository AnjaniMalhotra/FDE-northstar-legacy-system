"""DockTrak Terminal. The ground truth for detention — real arrival and
departure timestamps — with no math done on them anywhere on this screen."""
# ------------------------------------------
# IMPORTS
# ------------------------------------------
from fastapi import APIRouter, Request
from sqlalchemy import text

from backend.legacy_web.db import admin_engine
from backend.legacy_web.render import templates

router = APIRouter(prefix="/dock")


# ------------------------------------------
# SEARCH FORM — pick a load ID
# ------------------------------------------
@router.get("")
def search(request: Request):
    return templates.TemplateResponse(request, "dock_search.html", {})


# ------------------------------------------
# EVENT LOG — every ARRIVAL/DEPARTURE event for this load, oldest first
# ------------------------------------------
@router.get("/events")
def event_log(request: Request, load_id: int):
    with admin_engine.connect() as conn:
        events = conn.execute(
            text("SELECT * FROM dbo.tbl_dock_evt_raw WHERE ld_id = :id ORDER BY evt_ts"),
            {"id": load_id},
        ).mappings().all()
    return templates.TemplateResponse(request, "dock_detail.html", {"load_id": load_id, "events": events})
