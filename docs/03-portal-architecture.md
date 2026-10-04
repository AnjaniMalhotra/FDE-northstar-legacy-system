# Portal Architecture

How the system is actually put together: three portals, one backend, one database.

## The shape of it

```
frontend/northstar_web/
├── shipper/    plain HTML/CSS/JS — request a shipment, track it
├── employee/   plain HTML/CSS/JS — approve requests, review invoices, manage carriers
├── carrier/    plain HTML/CSS/JS — view assigned shipments, submit invoices
└── shared/     one CSS system + one JS file every page calls the backend through

backend/northstar_web_api/   FastAPI app — the only thing any portal talks to, and also serves
                              the static files above (one process, one port)
backend/scripts/             schema.sql (tables), security.sql (roles), seed_northstar_web_data.py
```

Each portal is a separate set of static HTML pages with no build step and no framework — every page
loads `shared/js/` for API calls and `shared/css/` for styling, then does its own DOM updates with
plain JavaScript. There's no server-side templating: the backend only ever returns JSON, and every
page renders itself.

## One backend, one database

All three portals call the same FastAPI backend (`backend/northstar_web_api/`), which talks to one
Postgres database (`northstar_web`). The backend exposes a small, mostly generic set of routes
keyed by table name (`/api/shipments`, `/api/invoices`, `/api/dockEvents`, ...) rather than a
bespoke endpoint per page — list, get-one, insert, update. Invoices are the one case with real
extra logic: every invoice fetch also pulls its full `invoice_decisions` history, so the employee
review page can show not just the current status but every decision made along the way.

**Why one backend for three portals, instead of three separate services:** they share the same
tables, the same login mechanism, and the same "who am I" session check — splitting them into
separate services would mean either duplicating that logic three times or building a way to share
it, for no real benefit at this scale. What does differ by portal is *what each login is allowed to
see and do* — that's handled by role, not by which service answers the request (see
[04-security-and-access-model.md](04-security-and-access-model.md)).

## The data model

```
users            — one table for all three portals; a row's `portal` + `role` decide what it can do
carriers         — the vetted carrier network
shipment_requests — a shipper's ask, before an employee decides
shipments        — created once a request is approved; carries the agreed rate + detention terms
dock_events      — real arrival/departure timestamps, tied to a shipment
invoices         — what a carrier billed for a delivered shipment
invoice_decisions — the approve/hold/revise history for one invoice
sessions         — opaque login tokens, checked on every request
```

The relationships follow the real-world flow directly: a `shipment_request` becomes a `shipment`
once approved, a `shipment` accumulates `dock_events` as the truck moves, and a `shipment` gets
exactly one `invoice` after delivery, which can accumulate many `invoice_decisions` over time as
Finance reviews it. Nothing here is normalized further than the workflow actually needs — the
schema is meant to be read in one sitting, not modeled like a production ERP.

## How a request becomes a page

1. A page loads and calls a shared login-check function — if there's no valid session cookie, it
   redirects to that portal's own login page.
2. Once logged in, the page calls one or more `/api/...` routes to fetch the data it needs (e.g.,
   the employee invoices page fetches `/api/invoices`, which comes back with each invoice's decision
   history already attached).
3. The page renders that JSON into HTML itself — there's no server-rendered template anywhere in
   this project.
4. An action (approving a request, recording an invoice decision) is a plain `POST`/`PATCH` back to
   the same API, which writes to Postgres inside one transaction per request and returns the updated
   row.

This is deliberately the simplest shape that teaches the real pattern — a stateless API backend, a
relational schema that mirrors the real-world workflow, and thin client pages — without reaching for
a frontend framework, server-side rendering, or a job queue that this scale of system doesn't need.
