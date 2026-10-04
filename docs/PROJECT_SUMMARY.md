# Project Summary

## What this project is

Northstar Freight's self-service portal — shipper booking, employee operations (bookings,
invoices, dock events, carrier records), and carrier invoicing — with an AI copilot woven directly
into the employee side. The portal itself is the same one documented in the sibling
`Northstar-Legacy-System` project; this folder is where the AI actually shows up for the people who
use it, rather than living only in a separate demo console.

See [01-how-the-ai-integration-works.md](01-how-the-ai-integration-works.md) for what was added and
how it works.

## How the three related projects fit together

| Project | What it is |
|---|---|
| `Northstar-Legacy-System` | The portal on its own, with no AI — the clean "before" reference. |
| `Northstar-Copilot-POC` | The AI system's original standalone home — its own console, kept as a separate, unmodified stakeholder-facing demo. |
| `Northstar-Legacy-With-AI` (this folder) | The portal from the first project, with the AI's own logic (ported from the second) running inside this project's own backend. |

This folder's frontend and database schema are unmodified from `Northstar-Legacy-System`. Its
backend (`backend/northstar_web_api/main.py`) gained a few lines mounting the AI's own routes
(`backend/copilot_api/`, `/api/ai/...`) alongside the portal's own — one process, no separate AI
service to run. See that project's own docs for the portal's booking/approval flow and database
design, and [01-how-the-ai-integration-works.md](01-how-the-ai-integration-works.md) for how the
reconciliation logic and guardrails work here.

## Data

`backend/scripts/generate_more_data.py` adds on top of the portal's own starter seed to reach a
larger, more realistic dataset (about 25 carriers, 50 shippers, 100 invoices) — enough real
discrepancies for the AI features to have something to find. Run once, after the portal's own
`seed_northstar_web_data.py`.

## Governance

The portal's own login and data access are unchanged: real password checks inside Postgres
(`pgcrypto`), no shared admin login. The AI's own access follows its own role model, kept
independent of the portal's — an Analyst account can chat and review invoices, but Pending
Approvals requires a Manager or Admin login.
