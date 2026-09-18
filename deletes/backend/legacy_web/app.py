"""
Northstar Freight's system AS IT EXISTED BEFORE any FDE engagement — no AI,
no reconciliation math, no automatic cross-checking. Five separate,
differently-branded systems (AP, TMS, DockTrak, Carrier Master, and the
external TransCheck safety registry), each a plain lookup screen over the
raw legacy tables. Nothing here calculates or compares anything for you —
that's the entire point. Replaces the earlier Streamlit version
(src/legacy_ui.py, moved to deletes/) with something that actually looks
and feels like the pile of disconnected real systems it's simulating.

Run: uvicorn backend.legacy_web.app:app --reload --port 8001
"""
# ------------------------------------------
# IMPORTS
# ------------------------------------------
from pathlib import Path

from fastapi import FastAPI, Request
from fastapi.staticfiles import StaticFiles

from backend.legacy_web.render import templates
from backend.legacy_web.routes import ap, carriers, dock, safety, tms
from backend.legacy_web.routes.ap import decision_counts, pending_invoices, recent_activity

# ------------------------------------------
# APP + STATIC FILES — one FastAPI app, one static mount for all system CSS
# ------------------------------------------
app = FastAPI(title="Northstar Freight — Legacy Systems (pre-FDE)")
app.mount("/static", StaticFiles(directory=str(Path(__file__).resolve().parent / "static")), name="static")

# ------------------------------------------
# ROUTERS — one per "system," each its own file under routes/
# ------------------------------------------
app.include_router(ap.router)
app.include_router(tms.router)
app.include_router(dock.router)
app.include_router(carriers.router)
app.include_router(safety.router)

# ------------------------------------------
# LANDING PAGE — the employee's actual starting point: an intranet directory
# ------------------------------------------
@app.get("/")
def landing(request: Request):
    return templates.TemplateResponse(
        request,
        "landing.html",
        {"counts": decision_counts(), "activity": recent_activity(), "queue": pending_invoices(limit=5)},
    )
