# Northstar Freight — Legacy System

The freight brokerage's pre-AI world: a self-service portal, none of it touched by AI. This folder
is deliberately standalone: no AI copilot, no RAG, no LLM, nothing from that side of the project.
The AI copilot lives in its own separate repo and reads/writes this system's `northstar_web`
database directly (its own tables and Postgres roles, added purely additively), without needing
anything in here to change.

`legacy_web` — the five disconnected "before FDE" branded systems (AP, TMS, DockTrak, Carrier
Master, TransCheck) that used to live here — has been retired, along with the separate
`northstar_freight` database it read/writes. `northstar_web` (below) already showed the same
"no AI, no cross-checking" pain point and is the AI integration's real target, so keeping both was
redundant. See
[docs/build-log/06-retire-legacy-web-and-northstar-freight.md](docs/build-log/06-retire-legacy-web-and-northstar-freight.md).

## What's here

```
backend/
├── northstar_web_api/      FastAPI backend for the self-service portal below — real
│                           password login (Postgres pgcrypto), real sessions.
└── scripts/                Schema, one-time setup, and seed data for northstar_web, this
                             project's one database. Run backend/scripts/bootstrap.sh once.

frontend/
└── northstar_web/          The shipper/employee/carrier self-service portal — plain
                             HTML/CSS/JS calling backend/northstar_web_api/.

docs/                       The problem statement, company profile, and the build-log entries
                             that tell this system's own story.

deletes/                    legacy_web and its supporting northstar_freight scripts, retired —
                             moved here rather than deleted outright.
```

## One database

- **`northstar_web`** — carriers, users, shipments, dock events, invoices, invoice decisions;
  clean table/column names since it's built from scratch. Served to the portal by
  `backend/northstar_web_api/` via a read/write app role, and read/written by the sibling AI
  copilot project via its own separate, more restricted roles (`northstar_web_agent` + 3 human
  roles) — see `Northstar-Copilot-POC/scripts/northstar_web_ai_security.sql`.

## Setup

```bash
python3 -m venv .venv && source .venv/bin/activate
pip install -r requirements.txt
cp .env.example .env        # fill in DB_ADMIN_USER (your OS user) and the two password vars
bash backend/scripts/bootstrap.sh
```

Then run each app:
```bash
# northstar_web_api — port 8020
uvicorn backend.northstar_web_api.main:app --reload --port 8020

# frontend/northstar_web — port 8010
cd frontend/northstar_web && python3 -m http.server 8010
```

## Why this folder exists

This is the groundwork for deploying the legacy system on its own — real infrastructure (GCP,
Cloud SQL), separate from wherever the AI copilot POC is being demoed from. The AI side connects to
`northstar_web` directly now (see `docs/build-log/06-retire-legacy-web-and-northstar-freight.md`
and the sibling project's own `docs/build-log/07-point-ai-at-northstar-web.md`) — this project's
own application code never changes to accommodate it; everything the AI needs was added from its
own side, as new tables/roles that sit alongside this project's schema without altering it.
