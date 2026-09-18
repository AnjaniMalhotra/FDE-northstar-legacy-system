"""
Real, server-side login: password checked with Postgres's own pgcrypto
(crypt/gen_salt — the same technique scripts/migrate_identity_v4.sql
already uses), and a session token issued as an HttpOnly cookie. Every
other endpoint in this API requires a valid, unexpired session — nothing
is enforced only by client-side JS.
"""
# ------------------------------------------
# IMPORTS
# ------------------------------------------
import secrets
from datetime import datetime, timedelta

from fastapi import Cookie, Depends, HTTPException, Response
from sqlalchemy import text
from sqlalchemy.engine import Connection

from backend.northstar_web_api.db import get_conn
from backend.northstar_web_api.naming import row_to_camel

SESSION_COOKIE = "northstar_web_session"
SESSION_LIFETIME = timedelta(days=7)


# ------------------------------------------
# LOGIN — verify email/password/portal, issue a session
# ------------------------------------------
def login(conn: Connection, response: Response, portal: str, email: str, password: str) -> dict | None:
    row = conn.execute(
        text(
            "SELECT id, portal, role, email, name, company_name, carrier_id FROM users"
            " WHERE portal = :portal AND email = :email AND password_hash = crypt(:password, password_hash)"
        ),
        {"portal": portal, "email": email, "password": password},
    ).mappings().first()
    if not row:
        return None

    token = secrets.token_urlsafe(32)
    expires_at = datetime.utcnow() + SESSION_LIFETIME
    conn.execute(
        text("INSERT INTO sessions (token, user_id, expires_at) VALUES (:token, :user_id, :expires_at)"),
        {"token": token, "user_id": row["id"], "expires_at": expires_at},
    )
    response.set_cookie(SESSION_COOKIE, token, httponly=True, samesite="lax", max_age=int(SESSION_LIFETIME.total_seconds()))
    return row_to_camel(dict(row))


# ------------------------------------------
# LOGOUT — delete the session row and clear the cookie
# ------------------------------------------
def logout(conn: Connection, response: Response, token: str | None) -> None:
    if token:
        conn.execute(text("DELETE FROM sessions WHERE token = :token"), {"token": token})
    response.delete_cookie(SESSION_COOKIE)


# ------------------------------------------
# REQUIRE SESSION — FastAPI dependency: every protected route depends on this
# ------------------------------------------
def require_session(
    conn: Connection = Depends(get_conn),
    session_token: str | None = Cookie(default=None, alias=SESSION_COOKIE),
) -> dict:
    if not session_token:
        raise HTTPException(status_code=401, detail="Not logged in.")
    row = conn.execute(
        text(
            "SELECT u.id, u.portal, u.role, u.email, u.name, u.company_name, u.carrier_id FROM sessions s"
            " JOIN users u ON u.id = s.user_id"
            " WHERE s.token = :token AND s.expires_at > now()"
        ),
        {"token": session_token},
    ).mappings().first()
    if not row:
        raise HTTPException(status_code=401, detail="Session expired or invalid — please log in again.")
    return row_to_camel(dict(row))
