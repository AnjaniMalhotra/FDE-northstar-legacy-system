"""
The FastAPI backend for frontend/northstar_web/ — real login (Postgres pgcrypto),
real sessions (HttpOnly cookie), and a small generic REST API over the
northstar_web database. This is the only thing standing between the
browser and the database; an FDE instead connects to Postgres directly
with the read-only northstar_web_fde_ro role (see scripts/northstar_web_security.sql).

Run: uvicorn backend.northstar_web_api.main:app --reload --port 8020
"""
# ------------------------------------------
# IMPORTS
# ------------------------------------------
from fastapi import APIRouter, Cookie, Depends, FastAPI, HTTPException, Response
from fastapi.middleware.cors import CORSMiddleware
from pydantic import BaseModel
from sqlalchemy import text
from sqlalchemy.engine import Connection

from backend.northstar_web_api import auth
from backend.northstar_web_api.db import get_conn
from backend.northstar_web_api.routes import router as collections_router

# ------------------------------------------
# APP + CORS — the static site (a different port) needs cross-origin cookies
# ------------------------------------------
app = FastAPI(title="Northstar Web API")
app.add_middleware(
    CORSMiddleware,
    allow_origins=["http://localhost:8010", "http://127.0.0.1:8010"],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

auth_router = APIRouter(prefix="/api/auth")


# ------------------------------------------
# LOGIN BODY
# ------------------------------------------
class LoginBody(BaseModel):
    portal: str
    email: str
    password: str


# ------------------------------------------
# LOGIN / LOGOUT / ME
# ------------------------------------------
@auth_router.post("/login")
def login(body: LoginBody, response: Response, conn: Connection = Depends(get_conn)):
    user = auth.login(conn, response, body.portal.upper(), body.email, body.password)
    if not user:
        raise HTTPException(status_code=401, detail="Incorrect email or password.")
    return user


@auth_router.post("/logout")
def logout(
    response: Response,
    conn: Connection = Depends(get_conn),
    session_token: str | None = Cookie(default=None, alias=auth.SESSION_COOKIE),
):
    auth.logout(conn, response, session_token)
    return {"ok": True}


@auth_router.get("/me")
def me(user: dict = Depends(auth.require_session)):
    return user


app.include_router(auth_router)


# ------------------------------------------
# PUBLIC CONTACT FORM — the one endpoint anonymous visitors can reach; no
# session required, unlike everything under collections_router. Write-only
# on purpose — no one reads inquiries back through the API, an FDE or admin
# reads the table directly (see scripts/northstar_web_migrate_contact.sql).
#
# Registered before collections_router on purpose: Starlette matches routes
# in registration order, and collections_router's POST /api/{collection}
# would otherwise catch "contact" as a collection name first and demand a
# session before this route is ever tried.
# ------------------------------------------
class ContactBody(BaseModel):
    name: str
    email: str
    company: str | None = None
    phone: str | None = None
    subject: str
    message: str


@app.post("/api/contact")
def submit_contact(body: ContactBody, conn: Connection = Depends(get_conn)):
    conn.execute(
        text(
            "INSERT INTO contact_inquiries (name, email, company, phone, subject, message)"
            " VALUES (:name, :email, :company, :phone, :subject, :message)"
        ),
        body.model_dump(),
    )
    return {"ok": True}


app.include_router(collections_router)
