# Project Instructions — Northstar Legacy System

This file is read automatically at the start of every session in this project. **Read it fully
before writing any code.** It exists because this project is being *taught*, not just shipped —
every line of code needs to be something a student can read and understand, not just something
that works.

---

## What this project is

The "before FDE" world of Northstar Freight, a fictional freight brokerage: a self-service portal —
no AI anywhere in this project. This is the standalone sibling to `Northstar-Copilot-POC` (the AI
system, built separately, reading and writing this project's `northstar_web` database directly, via
its own separate, restricted Postgres roles). `legacy_web` — the five disconnected "before FDE"
systems this project used to also contain — has been retired; the one remaining portal,
`northstar_web`, now covers the same "no cross-checking" gap over the full booking → invoice
workflow. See `README.md` for setup and `docs/` for the full story.

---

## The one rule that matters most: write the *minimum* code that teaches the concept

This is a teaching project. A working solution that takes 300 lines when 40 would do is a
**failure**, even if it runs correctly — because nobody can teach it or learn from it. Before
writing code for any step, check:

1. **Could a student read this file top-to-bottom in under ~2 minutes and understand it?** If not,
   it's doing too much.
2. **Is any function longer than ~30–40 lines?** That's a signal it's doing more than one thing —
   split it, or simplify the requirement instead of the code.
3. **Am I building something "just in case," or handling a scenario that can't actually happen
   here?** Delete it. This is a mock/teaching environment — it doesn't need production-grade
   defensive code for inputs that will never occur.
4. **Am I reaching for a custom abstraction, framework, or config system where a plain function or
   a well-known library would do?** Use the plain version. Abstractions are earned by repetition,
   not built in advance.
5. **Does understanding this require a concept we haven't taught yet in the course?** If so,
   simplify until it only needs what's already been covered.

When in doubt, write **less** code and **more** explanation in the accompanying doc (see below).

**Every logical block of code gets a banner comment, in every file, wherever it's possible to add
one:**

```
# ------------------------------------------
# SHORT LABEL — one clause on what this block does
# ------------------------------------------
```

Use the file's own comment syntax (`#` for Python/shell/SQL). This sits *alongside* the existing
"explain why, not what" rule for inline comments — the banner names the block, a targeted inline
comment carries the non-obvious reasoning.

---

## Documentation is not optional — it's part of every step

A significant change gets reflected in the relevant `docs/` file — what changed and why. `docs/`
here is student-facing reference material (company profile, glossary, architecture, security
model), not a running build log — keep it that way; see `docs/PROJECT_SUMMARY.md` for the current
structure.

---

## Folder structure — don't deviate without a reason

```
Northstar-Legacy-System/
├── CLAUDE.md                ← this file
├── README.md                ← what this is and how to try it (Docker or GCP)
├── project-overview/         The parent FDE capstone's own docs (CLAUDE.md, README.md,
│                             COMMANDS.md, prompts.md) — this project's GitHub repo only tracks
│                             this one folder of the capstone, so its wider context rides along
│                             here rather than living one level up where GitHub can't see it.
├── requirements.txt
├── .env.example
├── Dockerfile / docker-compose.yml / docker-entrypoint.sh / .dockerignore
│                             One image serves both the API and the static site — see
│                             backend/northstar_web_api/main.py. docker-entrypoint.sh runs
│                             backend/scripts/bootstrap.sh on every container start (idempotent).
├── deploy/
│   ├── terraform/            Cloud SQL, Secret Manager, Artifact Registry, Cloud Run — see
│   │                          deploy/terraform/versions.tf for the provider/module layout.
│   └── setup_gcp.sh          First-time GCP deploy: terraform apply, build+push the image via
│                              Cloud Build, terraform apply again with the real image.
├── backend/
│   ├── northstar_web_api/   FastAPI backend for the self-service portal below — real password
│   │                         login (Postgres pgcrypto), real sessions — plus (main.py, bottom of
│   │                         the file) mounts frontend/northstar_web/ as static files, so the API
│   │                         and the site are one process, one port, no CORS to configure.
│   └── scripts/              Schema, security, seed data, and the larger demo dataset
│                              (generate_more_data.py) for northstar_web, this project's one
│                              database. Run scripts/bootstrap.sh once — it runs all of these,
│                              in order, idempotently.
├── frontend/
│   └── northstar_web/       The shipper/employee/carrier self-service portal — plain
│                             HTML/CSS/JS calling a relative `/api` (see shared/js/db.js,
│                             shared/js/auth.js) — works unchanged locally, in Docker, or on
│                             Cloud Run since the API and the site always share one origin.
└── docs/                    Company profile, glossary, portal architecture, and security model —
                              see docs/PROJECT_SUMMARY.md to start.
```

**One database**, this project's own: `northstar_web` (carriers, users, shipments, dock events,
invoices, invoice decisions — clean, modern column names). `legacy_web` and the separate
`northstar_freight` database it used are retired — the sibling AI copilot project reads and writes
`northstar_web` directly instead, via its own added-on-top tables/roles. Locally or in Docker this
is plain Postgres; in GCP it's the exact same schema and roles running on Cloud SQL — see
`backend/northstar_web_api/db.py` for how the app picks between a Unix socket (Cloud Run + Cloud
SQL) and plain TCP (everywhere else) based on whether `INSTANCE_CONNECTION_NAME` is set.

**Do not create new top-level files or folders without a clear reason tied to something the user
asked for.**

**Never paste a real API key or secret into chat.** If one is ever pasted, treat it as compromised
immediately.

---

## Governance & safety — no hardcoded guardrails, no hardcoded auth

This project has no AI — the governance model it demonstrates is narrower: **never hardcode
authentication** (no literal username/password checks, no magic tokens in code) — identity comes
from a real login table checked by Postgres itself (`pgcrypto`), never string comparisons in
Python. Database access is enforced by real Postgres roles/GRANTs, not application-level checks —
see `backend/scripts/northstar_web_security.sql` for the read/write app role vs. the read-only FDE
role.

---

## Before writing any new code, run this checklist

1. Does a `docs/` file need updating to reflect this change?
2. Is this the minimum code needed to teach the concept for this step? (See the 5 questions
   above.)
3. Does anything here touch permissions, data access, or an irreversible action? If yes, is it
   enforced by the database itself, not a hardcoded application check?
4. Does this fit inside the existing folder structure without inventing a new top-level file?
