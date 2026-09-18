"""TransCheck Carrier Safety Registry. A separate outside system Northstar
does not own (backend/legacy_carrier_safety.py) — a manual, extra step nobody
has time for unless something's already gone wrong."""
# ------------------------------------------
# IMPORTS
# ------------------------------------------
from fastapi import APIRouter, Request

from backend.legacy_carrier_safety import get_carrier_safety_profile
from backend.legacy_web.render import templates

router = APIRouter(prefix="/safety")


# ------------------------------------------
# SEARCH FORM — the "you are leaving Northstar" entry point
# ------------------------------------------
@router.get("")
def search(request: Request):
    return templates.TemplateResponse(request, "safety_search.html", {})


# ------------------------------------------
# SAFETY LOOKUP — calls the external registry by MC number
# ------------------------------------------
@router.get("/lookup")
def lookup(request: Request, mc_number: str):
    profile, error = None, None
    try:
        profile = get_carrier_safety_profile(mc_number)
    except Exception as e:
        error = str(e)
    return templates.TemplateResponse(
        request, "safety_result.html", {"mc_number": mc_number, "profile": profile, "error": error}
    )
