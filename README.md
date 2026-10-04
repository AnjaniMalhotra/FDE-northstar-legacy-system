# Northstar Freight — Portal, with the AI Copilot Woven In

This folder is a copy of `Northstar-Legacy-System` (the shipper/employee/carrier self-service
portal), with the AI copilot woven directly in — a chat widget, an AI Review panel on the invoice
page, and native Pending Approvals/Audit Log pages. `Northstar-Legacy-System` itself is untouched
and stays available as the clean "before" reference; this folder is where the integrated version
actually runs — **as one self-contained project**, with the AI's own logic (`copilot/`) running
inside this project's own backend, not calling out to a separately-running service.

See [docs/01-how-the-ai-integration-works.md](docs/01-how-the-ai-integration-works.md) for what
each piece does and why it's built the way it is, and
[`project-overview/README.md`](project-overview/README.md) for the full three-part capstone this
project is one part of.

The portal's own code — booking, invoices, dock events, carrier records, the Approve/Hold decision
flow — is unchanged from `Northstar-Legacy-System`. The AI's own logic was ported in from the
standalone `Northstar-Copilot-POC` project (which stays a separate, unmodified stakeholder-demo
project) and mounted onto this same backend under `/api/ai/...`.

## What's here

```
copilot/                      The AI's own logic — orchestrator, tools, guardrails,
                               reconciliation, RAG, prompts. Ported in unchanged.

data/policy/                  RAG source documents + policy_config.json/access_policy.json.
                               Ported in unchanged.

backend/
├── northstar_web_api/        The one FastAPI app. main.py mounts the portal's own routers
│                             (unchanged from Northstar-Legacy-System) alongside copilot_api's.
├── copilot_api/               The AI's own routes (chat, invoice review, Pending Approvals,
│                              Audit Log) and its own login — ported in from
│                              Northstar-Copilot-POC, with one edit: every route's prefix
│                              changed from /api to /api/ai, so it can never collide with
│                              the portal's own generic /api/{collection} routes.
└── scripts/
    ├── northstar_web_schema.sql / _security.sql / seed_northstar_web_data.py
    │                          The portal's own setup — unchanged.
    ├── generate_more_data.py
    │                          Adds on top of the starter seed to reach a larger dataset
    │                          (about 25 carriers, 50 shippers, 100 invoices).
    ├── northstar_web_ai_schema.sql / _security.sql
    │                          The AI's own additive tables/roles — ported in unchanged.
    └── ingest_policy_documents.py / generate_risk_memo_pdf.py
                               RAG setup — ported in, with path constants adjusted for this
                               project's folder depth (backend/scripts/, not scripts/).

frontend/northstar_web/
├── employee/
│   ├── ai-approvals.html      Flags waiting on a human decision.
│   ├── ai-audit.html          The AI's full audit trail.
│   ├── invoice-detail.html    Unchanged except for one new AI Review card.
│   └── ...                    Every other employee page: unchanged, plus the chat widget.
└── shared/js/ai_widget.js     The chat widget — no login of its own, just the one portal
                                session every other page already relies on.

docs/                          This folder's own story — the AI integration. The portal's own
                                history lives in Northstar-Legacy-System's docs, not duplicated here.
```

## Architecture

```
Browser  →  backend/northstar_web_api/ (FastAPI, port 8020)  →  Postgres: northstar_web
              /              (the static site itself, mounted last)      ▲
              /api/...        (the portal's own routes)                  │ direct psql/SQLAlchemy,
              /api/ai/...     (the AI's own routes, same process)  FDE ──┘ read-only, bypasses the API
```

- One process, one port — the same app serves the API *and* the static site. No separate
  `copilot_api` service, and no separate static-file server either.
- **One login, at the start.** There is exactly one session cookie (`northstar_web_session`) and
  one login form. The AI's own routes (`backend/copilot_api/auth.py`'s `get_ai_user`) read that
  same cookie and derive their role from the employee's existing portal role
  (`copilot/identity.py`'s `PORTAL_ROLE_MAP`) — there is no second credential check anywhere.
- Login is real: password checked server-side with Postgres's own `pgcrypto`, and a session cookie
  (`HttpOnly`) is required on every other request.
- An FDE gets their own **read-only** Postgres role (`northstar_web_fde_ro`) and connects straight
  to the database — no HTTP layer, no shared login. See "FDE access" below.

## One database, shared with `Northstar-Legacy-System`

Both folders point at the same `northstar_web` database — **only run one folder's
`northstar_web_api` at a time** (both bind port 8020, and would otherwise be two copies of the same
app hitting the same live data).

## Setup

```bash
python3 -m venv .venv && source .venv/bin/activate
pip install -r requirements.txt
cp .env.example .env        # fill in the portal's own vars AND the AI's (see the file's own comments)
bash backend/scripts/bootstrap.sh
python3 backend/scripts/generate_more_data.py   # optional — a larger dataset for the AI to work with
```

`bootstrap.sh` runs, in order: the portal's own schema/security/seed, then the AI's own additive
schema/security, then (if `PINECONE_API_KEY` is set) RAG document ingestion — idempotently, safe to
re-run.

Then run:
```bash
uvicorn backend.northstar_web_api.main:app --reload --port 8020
```
Then open `http://localhost:8020/`. One process — it serves the site, the portal's own API, and
the AI's routes together.

The chat widget (bottom-right, on any employee page) never asks you to log in — it reads the
portal session you already have. The same is true of Pending Approvals and the Audit Log.

## The three portals

| Portal | Demo login | Password |
|---|---|---|
| Shipper | `shipper@acmemfg.com` | `demo123` |
| Employee — Operations | `ops@northstarfreight.com` | `demo123` |
| Employee — Accounts Payable | `ap@northstarfreight.com` | `demo123` |
| Employee — Admin | `admin@northstarfreight.com` | `demo123` |
| Carrier — Pioneer Haulers | `dispatch@pioneerhaulers.com` | `demo123` |
| Carrier — Redline Transport | `dispatch@redlinetransport.com` | `demo123` |

(Every carrier in the network has a login — see `backend/scripts/seed_northstar_web_data.py` for
the full list; the email is `dispatch@` + the carrier's name, lowercased with spaces removed.)
Access to the Manager/Admin-only Pending Approvals page follows the AI's own role model — an
Operations login (Analyst) won't see it.

## FDE access

A real FDE connects straight to Postgres, not through the website or the API:

```
psql -h localhost -p 5432 -U northstar_web_fde_ro -d northstar_web
```
(password: `NORTHSTAR_WEB_FDE_PASSWORD` in `.env`)

That role can `SELECT` from every portal table — carriers, users (minus `password_hash`),
shipment_requests, shipments, dock_events, invoices, invoice_decisions — and nothing else.
`INSERT`/`UPDATE`/`DELETE` are rejected by Postgres itself. The AI's own roles
(`northstar_web_agent` + 3 human roles) are separate and even narrower, plus full access to the
AI's own tables (`dispute_flags`, `ai_invoice_reviews`, `agent_audit_log`).

## How data persists

Every page reads and writes through `backend/northstar_web_api/` (never `localStorage`), so what a
shipper submits shows up for Employees, and what an Employee approves shows up for the Carrier, for
real, across any browser or device. To reset the demo data, connect as the admin user, truncate the
tables, then re-run the seed script.

## The end-to-end flow

1. **Shipper** books a shipment (`shipper/new-shipment.html`) — fills in route/weight/goods,
   compares carrier pricing, submits.
2. **Employee (Operations)** reviews it (`employee/booking-detail.html`), manually checking Carrier
   Master and the Policy Reference page, and approves or rejects it.
3. **Carrier** sees the booked shipment, marks it delivered once complete (real dock
   arrival/departure is auto-captured at that moment, simulating a telematics feed — no one types
   it in), and fills in the invoice template (`carrier/invoice-form.html`).
4. **Employee (Accounts Payable)** reviews the invoice (`employee/invoice-detail.html`) — the AI
   Review card runs the detention/linehaul reconciliation automatically and shows its finding above
   the decision; Dock Events, Shipments, Carrier Master, and Policies are still there to check by
   hand too — then approves it or holds it with a note.
5. If held, the **Carrier** sees the note on `carrier/disputes.html`, revises the invoice, and
   resubmits — back to step 4, until approved.

Every invoice can be downloaded as a PDF via the browser's own print dialog
(`carrier/invoice-view.html` → Download PDF) — no PDF library involved.

## Why this folder exists

What the client actually gets: the AI copilot wired into their existing system, running as one
self-contained codebase they can build, deploy, and maintain on their own — no dependency on the
separate `Northstar-Copilot-POC` demo project. `Northstar-Legacy-System` itself is never touched
directly; everything here is additive on top of a copy of it.
