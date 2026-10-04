"""
Real human identity and role-based database access.

Logs in against the SAME users table the northstar_web portal already uses
(Northstar-Legacy-System owns that table — this file only reads it, never
writes it). A portal employee's existing role (OPERATIONS/ACCOUNTS_PAYABLE/
ADMIN) is translated into which AI role/database login to use — the
translation lives entirely here, not as a change to the portal's own data.

This is a pluggable auth design: a real local password login today
(authenticate(), checked by Postgres itself), with a real OAuth slot ready
to drop in later. Swapping AUTH_MODE=OAUTH would change *how a User gets
identified* (a verified provider claim instead of a password), not the
User/role shape or anything downstream of it — every caller of
get_role_engine() stays exactly the same either way.
"""
# ------------------------------------------
# IMPORTS
# ------------------------------------------
import os
from dataclasses import dataclass
from functools import lru_cache
from pathlib import Path

from dotenv import load_dotenv
from sqlalchemy import create_engine, text
from sqlalchemy.engine import Engine

# ------------------------------------------
# LOAD ENV VARS — read .env from project root
# ------------------------------------------
project_root = Path(__file__).resolve().parent.parent
load_dotenv(project_root / ".env")

# ------------------------------------------
# AUTH MODE — LOCAL_DEV password login today, OAuth slot for later
# ------------------------------------------
AUTH_MODE = os.getenv("AUTH_MODE", "LOCAL_DEV").strip().upper()

# ------------------------------------------
# DB CONNECTION SETTINGS — host/port/name shared by every role's login
# ------------------------------------------
DB_HOST = os.getenv("DB_HOST", "localhost")
DB_PORT = os.getenv("DB_PORT", "5432")
DB_NAME = os.getenv("DB_NAME")
INSTANCE_CONNECTION_NAME = os.getenv("INSTANCE_CONNECTION_NAME")

# ------------------------------------------
# ROLE LOGIN TABLE — per-role Postgres user/password
# ------------------------------------------
# Each human role connects as its own, separately-restricted Postgres login
# (scripts/northstar_web_ai_security.sql) — never a shared admin connection.
# 3 roles this pass — a separate COMPLIANCE role is a known, deliberate gap,
# folded into ADMIN, since adding it would mean a new portal login, which is
# off-limits for this change (northstar_web's own data stays untouched).
ROLE_LOGIN = {
    "ANALYST": ("northstar_web_analyst", os.getenv("DB_ANALYST_PASSWORD", "change_this_local_dev_password")),
    "MANAGER": ("northstar_web_manager", os.getenv("DB_MANAGER_PASSWORD", "change_this_local_dev_password")),
    "ADMIN":   ("northstar_web_admin",   os.getenv("DB_HUMAN_ADMIN_PASSWORD", "change_this_local_dev_password")),
}

# ------------------------------------------
# PORTAL ROLE MAP — translate northstar_web's existing employee role into
# which AI role/database login to use. Lives entirely here, not as a write
# to northstar_web's own users table — see module docstring.
# ------------------------------------------
PORTAL_ROLE_MAP = {
    "OPERATIONS": "ANALYST",
    "ACCOUNTS_PAYABLE": "MANAGER",
    "ADMIN": "ADMIN",
}


# ------------------------------------------
# USER IDENTITY — the shape every layer reads, regardless of auth mode
# ------------------------------------------
@dataclass(frozen=True)
class User:
    user_id: str        # email — the same key a real OAuth "sub"/email claim would use
    display_name: str
    role: str            # ANALYST, MANAGER, or ADMIN (translated from the portal's own role)


# ------------------------------------------
# GET ROLE ENGINE — cached per-role restricted database connection
# ------------------------------------------
@lru_cache(maxsize=None)
def get_role_engine(role: str) -> Engine:
    """The role's own restricted database connection. Cached per role —
    there are only 3, and each is cheap to keep open for the process
    lifetime rather than reconnecting on every call. Two connection shapes,
    picked by whether INSTANCE_CONNECTION_NAME is set — same branch
    backend/northstar_web_api/db.py uses, so this role's login resolves
    correctly whether it's running locally or on Cloud Run."""
    if role not in ROLE_LOGIN:
        raise ValueError(f"Unknown role: {role}")
    user, password = ROLE_LOGIN[role]
    if INSTANCE_CONNECTION_NAME:
        socket_path = f"/cloudsql/{INSTANCE_CONNECTION_NAME}"
        db_url = f"postgresql+psycopg://{user}:{password}@/{DB_NAME}?host={socket_path}"
    else:
        db_url = f"postgresql+psycopg://{user}:{password}@{DB_HOST}:{DB_PORT}/{DB_NAME}"
    return create_engine(db_url)


# ------------------------------------------
# AUTHENTICATE — verify a password against Postgres and return the User
# ------------------------------------------
def authenticate(user_id: str, password: str) -> User | None:
    """Real password login for AUTH_MODE=LOCAL_DEV, against northstar_web's
    own EMPLOYEE-portal users table. The comparison happens inside Postgres
    itself (pgcrypto's crypt()), not in Python — this app never reads or
    holds a password hash, only asks the database "does this one match?"
    (scripts/northstar_web_ai_security.sql grants northstar_web_analyst
    column-level SELECT on password_hash for exactly this query). Returns
    None on any mismatch, on an employee whose portal role has no AI
    mapping (PORTAL_ROLE_MAP), or if the users row is not an EMPLOYEE at
    all — the AI never authenticates a shipper or carrier login."""
    query = text("""
        SELECT email, name, role FROM users
        WHERE portal = 'EMPLOYEE' AND email = :user_id AND password_hash = crypt(:password, password_hash)
    """)
    with get_role_engine("ANALYST").connect() as conn:
        row = conn.execute(query, {"user_id": user_id, "password": password}).fetchone()
    if not row:
        return None
    ai_role = PORTAL_ROLE_MAP.get(row.role)
    if not ai_role:
        return None
    return User(row.email, row.name, ai_role)
