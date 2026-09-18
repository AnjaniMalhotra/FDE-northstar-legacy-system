# Project Summary — for Professor & Students

This is the one file to read for the whole story of this system without digging through every doc.
Covers the legacy world only — the AI copilot built on top of it is a separate sibling project
(`Northstar-Copilot-POC`) with its own summary doc.

## 1. The idea behind the project

The course is teaching the **Forward Deployed Engineer (FDE)** role — engineers who embed directly
with a customer, learn their real (usually messy) systems, and ship a working AI solution rather
than a generic product. See the sibling project's
[docs/01-fde-background-and-reference-review.md](../../Northstar-Copilot-POC/docs/01-fde-background-and-reference-review.md)
for the full background: where the role came from, why AI companies have rapidly adopted the same
model, and what an FDE actually does day to day.

## 2. Why freight, and why this specific company

Freight and logistics are a strong domain for teaching this because every real freight company's
data is genuinely messy (legacy systems, disconnected teams, manual documents) — the exact
conditions that make the FDE role necessary rather than a plug-and-play SaaS tool. Eight
freight-adjacent verticals were surveyed before choosing.

**Northstar Freight — a freight brokerage** — was chosen as the project's domain. A freight
brokerage doesn't own trucks; it matches shippers who need freight moved with a network of trucking
carriers, earning the difference (the margin) between what it charges and what it pays the carrier.
That margin is thin and leaks constantly through billing mismatches and fraud — almost all of it
hidden inside PDFs and disconnected systems.

## 3. What this folder actually is

This is the **"before FDE" world**: what Northstar's systems looked like before any AI copilot was
built. Today that's one system — a self-service portal (`northstar_web`) — with no AI, no
cross-checking, no reconciliation math anywhere in it. It used to also include five disconnected
internal systems and a separate synthetic legacy database with deliberately cryptic column names
(`legacy_web`/`northstar_freight`); those are retired now that the portal shows the same gap over
more of the real workflow and is where the AI is actually integrating — see
[build-log/06](build-log/06-retire-legacy-web-and-northstar-freight.md). See the sibling project's
[docs/02-ai-copilot-solution.md](../../Northstar-Copilot-POC/docs/02-ai-copilot-solution.md), where
the full problem-and-solution story lives, for the business problem this world's gaps eventually
lead to fixing.

## 4. How the project is structured

The course originally taught this project's shape as six academic phases; it's since been split
into **three delivery phases**, mirroring how a real FDE engagement actually unfolds. This folder
covers **Phase 1 — Legacy System** in full. Phase 2 (the Copilot POC) lives in the sibling project;
**Phase 3 — Integration** is now underway there too, reading/writing this folder's own
`northstar_web` database directly rather than a separate one — see
[build-log/06](build-log/06-retire-legacy-web-and-northstar-freight.md).

## 5. How the code itself is being written

Because this is a teaching project, code quality here means something specific: **the minimum code
needed to teach each concept**, not the most complete or clever solution. See
[CLAUDE.md](../CLAUDE.md) for the exact rules being followed (function-length limits, no
speculative code, no premature abstractions) and [build-log/](build-log/) for a running,
step-by-step record of what was built and why.

## 6. How safety and governance are handled, here

This folder has no AI, so its governance story is narrower than the sibling project's 7-layer
model: **database-enforced access**, not application-level checks. `backend/northstar_web_api`'s
login is checked entirely inside Postgres itself (`pgcrypto`) — this app never reads or holds a
password. An FDE connects to the `northstar_web` database directly with a strictly read-only role
(`northstar_web_fde_ro`), bypassing the API entirely, rather than a shared admin login. The sibling
AI copilot project now connects the same way in spirit — its own restricted roles, never the app's
shared login — though with its own separate set of roles, not this exact one.

## 7. Where things stand right now — Phase 1 (done)

- **The kickoff brief and a scoping decision** are written down — the project is deliberately
  focused on one pain point (overbilled detention charges), with a clear, plain-language rule for
  what counts as an "anomaly" and what always needs a human before anything happens. See
  [build-log/01-kickoff-and-scoping.md](build-log/01-kickoff-and-scoping.md).
- **A synthetic "legacy" freight brokerage database** is built and running locally in Postgres —
  clean data deliberately obfuscated into cryptic legacy column names. The security was actually
  tested, not just written. See
  [build-log/02-synthetic-legacy-system.md](build-log/02-synthetic-legacy-system.md) for the full
  story, including two real bugs hit and fixed along the way.
- **TransCheck, the external carrier-safety feed** — built first as a real SOAP/XML service, later
  simplified to a plain Python module once the operational cost of a second process outweighed the
  teaching value — same lesson (a mocked external vendor), no second process to run. See
  [build-log/03-transcheck-carrier-safety-feed.md](build-log/03-transcheck-carrier-safety-feed.md).
- **A five-system "before FDE" web simulation** (`backend/legacy_web/`) — AP, TMS, DockTrak,
  Carrier Master, and TransCheck, each its own differently-branded system with no cross-checking
  between them, replacing an earlier single-app Streamlit stand-in, plus a later fix for a
  misleading "EXTERNAL" label found on a page that actually reads Northstar's own carrier record.
  See [build-log/04-legacy-web-simulation.md](build-log/04-legacy-web-simulation.md).
- **A newer self-service portal** (`frontend/northstar_web/` + `backend/northstar_web_api/`) —
  real shipper/employee/carrier logins backed by a separate Postgres database, a full booking →
  approval → delivery → invoice flow with realistic mock data, and a premium visual pass to match
  real logistics-industry sites. See
  [build-log/05-northstar-web-portal.md](build-log/05-northstar-web-portal.md).
- **This folder itself was carved out as a standalone project**, verified end-to-end (fresh venv,
  isolated test database, both apps actually started and hit) rather than assumed to work — two
  real path bugs found and fixed in the process (a nesting-depth bug in the data-generation
  scripts, and a hardcoded database name in the schema SQL that would have collided with the
  sibling project's own database on the same Postgres server).
- **`legacy_web` and `northstar_freight` were retired** once the sibling AI project moved onto this
  folder's own `northstar_web` database directly — `legacy_web` was the weaker, narrower demo of
  the same "no cross-checking" gap `northstar_web` already shows. Moved to `deletes/`, not deleted
  outright; zero changes to this folder's own remaining application code. See
  [build-log/06](build-log/06-retire-legacy-web-and-northstar-freight.md).

We also reviewed a friend's finished, similar project (a cold-chain logistics AI copilot) before
building anything — see Part 2 of the sibling project's
[docs/01-fde-background-and-reference-review.md](../../Northstar-Copilot-POC/docs/01-fde-background-and-reference-review.md)
for what was borrowed and what was deliberately done differently.

## What's next

**Move this system's database to Google Cloud SQL for PostgreSQL, then deploy on GCP** — planned
in detail (a Terraform module, Cloud SQL Auth Proxy for local connections, a "regenerate fresh"
data approach rather than dump/restore) but not yet built. A git branching scheme (one branch for
this system as-provided, one for after AI integration) was also raised and deliberately deferred.
See the root project's `README.md` for the current state of both.
