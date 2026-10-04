"""The AI's own /me and /my-access endpoints. Identity itself comes
straight from the portal's own session (see backend/copilot_api/auth.py's
get_ai_user) — there is no separate AI login or logout anymore. No app
object here: this project has only one FastAPI app
(backend/northstar_web_api/main.py), which mounts this file's auth_router
and routes/__init__.py's api_router alongside its own — one process, one
port, no separate service to run.
"""
# ------------------------------------------
# IMPORTS
# ------------------------------------------
from fastapi import APIRouter, Depends

from backend.copilot_api import auth
from copilot import access_policy
from copilot.identity import User

# ------------------------------------------
# THE FRONTEND TABS THIS CONSOLE ACTUALLY HAS PAGES FOR — a role may be
# granted more in access_policy.json (e.g. ADMIN's "legacy"), but that tab
# has no page, so it's never offered in the nav.
# ------------------------------------------
KNOWN_TABS = ["dashboard", "chat", "directory", "approvals", "audit"]

auth_router = APIRouter(prefix="/api/ai")


# ------------------------------------------
# ME — who the AI thinks you are: always re-derived from the portal
# session you're already logged into, never a separate credential check
# ------------------------------------------
@auth_router.get("/me")
def me(user: User = Depends(auth.get_ai_user)):
    tabs = [t for t in access_policy.visible_tabs(user.role) if t in KNOWN_TABS]
    return {"userId": user.user_id, "displayName": user.display_name, "role": user.role, "uiTabs": tabs}


# ------------------------------------------
# MY ACCESS — the permissions panel, same source of truth access_policy.py
# uses everywhere else.
# ------------------------------------------
@auth_router.get("/my-access")
def my_access(user: User = Depends(auth.get_ai_user)):
    perms = access_policy.get_permissions(user.role)
    return {
        "role": perms.role,
        "description": perms.description,
        "dataRead": perms.data_read,
        "dataWrite": perms.data_write,
        "aiTools": perms.ai_tools,
    }
