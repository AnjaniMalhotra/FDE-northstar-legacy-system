"""Identity for the AI's own routes — derived straight from the portal's
own already-authenticated session (northstar_web_session, DB-backed). There
is no second login and no second session store: an employee who is logged
into the portal is automatically recognized here too, via
copilot.identity.PORTAL_ROLE_MAP deciding which AI role that employee role
becomes. Shipper/carrier logins never reach the AI's routes at all (their
portal role has no entry in PORTAL_ROLE_MAP).
"""
# ------------------------------------------
# IMPORTS
# ------------------------------------------
import uuid
from dataclasses import dataclass

from fastapi import Cookie, Depends, HTTPException

from backend.northstar_web_api.auth import SESSION_COOKIE as PORTAL_SESSION_COOKIE
from backend.northstar_web_api.auth import require_session as require_portal_session
from copilot.identity import PORTAL_ROLE_MAP, User


# ------------------------------------------
# GET AI USER — translate the already-logged-in portal user into the AI's
# own User/role. No credential check happens here; require_portal_session
# (above) already did that.
# ------------------------------------------
def get_ai_user(portal_user: dict = Depends(require_portal_session)) -> User:
    ai_role = PORTAL_ROLE_MAP.get(portal_user["role"])
    if not ai_role:
        raise HTTPException(status_code=403, detail="This portal role has no AI access.")
    return User(user_id=portal_user["email"], display_name=portal_user["name"], role=ai_role)


# ------------------------------------------
# REQUIRE TAB ACCESS — FastAPI dependency factory: gate a route by ui_tab,
# the same table access_policy.json already uses for console tab
# visibility. Server-side enforcement, not just hiding a nav link.
# ------------------------------------------
def require_tab(tab_key: str):
    from copilot import access_policy

    def _check(user: User = Depends(get_ai_user)) -> User:
        if not access_policy.can_view_tab(user.role, tab_key):
            raise HTTPException(status_code=403, detail=f"Your role does not have access to '{tab_key}'.")
        return user

    return _check


# ------------------------------------------
# CHAT THREAD CACHE — one LangGraph thread per portal session, so a
# multi-turn chat (or an invoice's AI review) stays coherent across
# requests. Keyed by the portal's own session token purely as a cache key
# for conversation continuity — never used for identity or access control,
# and never issued by this file.
# ------------------------------------------
@dataclass
class ChatThread:
    thread_id: str
    initialized: bool = False


_CHAT_THREADS: dict[str, ChatThread] = {}


def get_chat_thread(portal_token: str | None = Cookie(default=None, alias=PORTAL_SESSION_COOKIE)) -> ChatThread:
    return _CHAT_THREADS.setdefault(portal_token, ChatThread(thread_id=str(uuid.uuid4())))
