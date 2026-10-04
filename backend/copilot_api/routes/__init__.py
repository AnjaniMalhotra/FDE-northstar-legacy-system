"""Combines every route file into the single `router` main.py mounts:
console_routes.py (chat + the dashboard/invoice list, every role),
action_routes.py (Pending Approvals, Audit Log — Manager+/Admin), and
invoice_routes.py (invoice detail, the AI review trigger, the human
decision)."""
# ------------------------------------------
# IMPORTS
# ------------------------------------------
from fastapi import APIRouter

from backend.copilot_api.routes.action_routes import router as action_router
from backend.copilot_api.routes.console_routes import router as console_router
from backend.copilot_api.routes.invoice_routes import router as invoice_router

# ------------------------------------------
# COMBINE — one router main.py can mount with a single include_router call
# ------------------------------------------
router = APIRouter()
router.include_router(invoice_router)
router.include_router(console_router)
router.include_router(action_router)
