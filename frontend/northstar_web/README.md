# Northstar Freight — Company Website (Shipper / Employee / Carrier)

A plain HTML/CSS/JS frontend — no build step, no framework, no AI — for
three separate portals, backed by a real PostgreSQL database (`northstar_web`)
through a small FastAPI service (`backend/northstar_web_api/`). This site's
own code is the "before AI copilot" world: modern-looking, but every check
and decision a human makes here is manual. The sibling `Northstar-Copilot-POC`
project now reads and writes this same `northstar_web` database directly
(its own tables/roles, added purely additively — see
`docs/build-log/06-retire-legacy-web-and-northstar-freight.md`) — this
site's own code never calls it and stays unaware of it either way.

## Architecture

```
Browser  →  backend/northstar_web_api/ (FastAPI, port 8020)  →  Postgres: northstar_web
                                                              ▲
                                                              │ direct psql/SQLAlchemy,
                                                     FDE ─────┘ read-only, bypasses the API
```

- The browser never talks to Postgres directly — only to the FastAPI backend, over `fetch()`.
- Login is real: password checked server-side with Postgres's own `pgcrypto`
  (`backend/scripts/northstar_web_security.sql`), and a session cookie (HttpOnly) is
  required on every other request.
- An FDE gets their own **read-only** Postgres role (`northstar_web_fde_ro`)
  and connects straight to the database — no HTTP layer, no shared login.
  See "FDE access" below.

## Run it

1. **Database** (one-time setup, from the project root):
   ```
   psql -U $DB_ADMIN_USER -d postgres -f backend/scripts/northstar_web_schema.sql
   psql -U $DB_ADMIN_USER -d northstar_web -f backend/scripts/northstar_web_security.sql
   python3 backend/scripts/seed_northstar_web_data.py
   ```
   Or just run `bash backend/scripts/bootstrap.sh` once, which does this end to end.
2. **Backend**:
   ```
   uvicorn backend.northstar_web_api.main:app --reload --port 8020
   ```
3. **Site** (a separate terminal):
   ```
   cd frontend/northstar_web
   python3 -m http.server 8010
   ```
   Then open `http://localhost:8010/`. (Port 8010, not 8000 — something
   else may already be using 8000 on your machine.)

## The three portals

| Portal | Demo login | Password |
|---|---|---|
| Shipper | `shipper@acmemfg.com` | `demo123` |
| Employee — Operations | `ops@northstarfreight.com` | `demo123` |
| Employee — Accounts Payable | `ap@northstarfreight.com` | `demo123` |
| Employee — Admin | `admin@northstarfreight.com` | `demo123` |
| Carrier — Pioneer Haulers | `dispatch@pioneerhaulers.com` | `demo123` |
| Carrier — Redline Transport | `dispatch@redlinetransport.com` | `demo123` |

(Every carrier in the network has a login — see
`backend/scripts/seed_northstar_web_data.py` for the full list; the email is
`dispatch@` + the carrier's name, lowercased with spaces removed.)

## FDE access

A real FDE connects straight to Postgres, not through the website or the API:

```
psql -h localhost -p 5432 -U northstar_web_fde_ro -d northstar_web
```
(password: `NORTHSTAR_WEB_FDE_PASSWORD` in `.env`)

That role can `SELECT` from every table — carriers, users (minus
`password_hash`), shipment_requests, shipments, dock_events, invoices,
invoice_decisions — and nothing else. `INSERT`/`UPDATE`/`DELETE` are
rejected by Postgres itself. The sibling AI copilot project connects with
its own, separate set of restricted roles instead of this one
(`northstar_web_agent` + 3 human roles — see the Northstar-Copilot-POC
project's `scripts/northstar_web_ai_security.sql`), each scoped even
narrower than this FDE role, plus full access to its own 4 tables.

## How data persists

`shared/js/db.js` is a `fetch()` client (not `localStorage`) — every page
reads and writes through `backend/northstar_web_api/`, so what a shipper submits
shows up for Employees, and what an Employee approves shows up for the
Carrier, for real, across any browser or device. `backend/scripts/seed_northstar_web_data.py`
seeds the same rich starter dataset the earlier `localStorage` version used
(12 carriers, every request/shipment/invoice status the app can display),
run once against an empty database — it skips itself if carriers already exist.

To reset the demo data, connect as the admin user and truncate the tables,
then re-run the seed script.

## The end-to-end flow

1. **Shipper** books a shipment (`shipper/new-shipment.html`) — fills in
   route/weight/goods, compares carrier pricing, submits.
2. **Employee (Operations)** reviews it (`employee/booking-detail.html`),
   manually checking Carrier Master and the Policy Reference page, and
   approves or rejects it.
3. **Carrier** sees the booked shipment, marks it delivered once complete
   (real dock arrival/departure is auto-captured at that moment, simulating
   a telematics feed — no one types it in), and fills in the invoice
   template (`carrier/invoice-form.html`).
4. **Employee (Accounts Payable)** reviews the invoice
   (`employee/invoice-detail.html`), manually checking Dock Events,
   Shipments (TMS), Carrier Master, TransCheck, and the Policy Reference —
   nothing is cross-checked automatically — then approves it or holds it
   with a note.
5. If held, the **Carrier** sees the note on `carrier/disputes.html`,
   revises the invoice, and resubmits — back to step 4, until approved.

Every invoice can be downloaded as a PDF via the browser's own print dialog
(`carrier/invoice-view.html` → Download PDF) — no PDF library involved.
