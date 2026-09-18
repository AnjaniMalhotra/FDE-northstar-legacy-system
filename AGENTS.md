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
systems this project used to also contain — has been retired; see
`docs/build-log/06-retire-legacy-web-and-northstar-freight.md`. See `README.md` for setup and
`docs/` for the full story.

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

Every build step gets a doc in `docs/build-log/`, written before the code (a short plan — what and
why) and updated after (what actually got built, and why it deviated if it did). See
`docs/build-log/README.md` for the naming convention and template.

---

## Folder structure — don't deviate without a reason

```
Northstar-Legacy-System/
├── CLAUDE.md / AGENTS.md    ← this file
├── README.md                ← setup and overview
├── requirements.txt
├── .env.example
├── backend/
│   ├── northstar_web_api/   FastAPI backend for the self-service portal below — real password
│   │                         login (Postgres pgcrypto), real sessions.
│   └── scripts/              Schema, security, and seed data for northstar_web, this project's
│                              one database. Run scripts/bootstrap.sh once.
├── frontend/
│   └── northstar_web/       The shipper/employee/carrier self-service portal — plain
│                             HTML/CSS/JS calling backend/northstar_web_api/.
├── docs/                    Problem statement, company profile, and this system's own
│                             build-log entries.
└── deletes/                 legacy_web and its supporting northstar_freight scripts, retired.
```

**One database**, this project's own: `northstar_web` (carriers, users, shipments, dock events,
invoices, invoice decisions — clean, modern column names). `legacy_web` and the separate
`northstar_freight` database it used are retired (see
`docs/build-log/06-retire-legacy-web-and-northstar-freight.md`) — the sibling AI copilot project
reads and writes `northstar_web` directly instead, via its own added-on-top tables/roles.

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

1. Does a plan doc for this step already exist in `docs/build-log/`? If not, write it first.
2. Is this the minimum code needed to teach the concept for this step? (See the 5 questions
   above.)
3. Does anything here touch permissions, data access, or an irreversible action? If yes, is it
   enforced by the database itself, not a hardcoded application check?
4. After writing the code, has the plan doc been updated with what was actually built and why?
5. Does this fit inside the existing folder structure without inventing a new top-level file?
