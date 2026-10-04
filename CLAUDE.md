# Project Instructions — Northstar Freight Portal, with the AI Copilot Woven In

This file is read automatically at the start of every session in this project. **Read it fully
before writing any code.** It exists because this project is being *taught*, not just shipped —
every line of code needs to be something a student can read and understand, not just something
that works.

---

## What this project is

A copy of `Northstar-Legacy-System` (Northstar Freight's self-service portal) with the AI copilot
woven directly in — a chat widget, an AI Review panel on the invoice page, and native Pending
Approvals/Audit Log pages, all purely additive. `Northstar-Legacy-System` itself is untouched and
stays the clean "before" reference; this is the "after." See
`docs/01-how-the-ai-integration-works.md` for exactly what was added and why, and `README.md` for
setup.

The AI's own logic (`copilot/`, ported from the standalone `Northstar-Copilot-POC` project) runs
**inside this project's own backend** — one process, one port, no separate service to run.
`Northstar-Copilot-POC` stays a separate, standalone stakeholder-demo project; nothing here depends
on it running, and nothing there was changed to make this work. The AI's own routes are mounted
under `/api/ai/...` (see `backend/northstar_web_api/main.py`) specifically so they can never
collide with the portal's own generic `/api/{collection}` routes.

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

A significant change gets noted in `docs/01-how-the-ai-integration-works.md` — what was added and
why, and any real design tradeoff it made. `docs/` here is student-facing reference material, not a
running build log — keep it that way.

---

## Folder structure — don't deviate without a reason

```
Northstar-Legacy-With-AI/
├── CLAUDE.md                ← this file
├── README.md                ← setup and overview
├── project-overview/         The parent FDE capstone's own docs (CLAUDE.md, README.md,
│                             COMMANDS.md, prompts.md) — this project's GitHub repo only tracks
│                             this one folder of the capstone, so its wider context rides along
│                             here rather than living one level up where GitHub can't see it.
├── requirements.txt         ← the portal's own deps + the AI's stack (LangGraph, Pinecone, ...)
├── .env.example
├── copilot/                 The AI's own logic — orchestrator, tools, guardrails, reconciliation,
│                             RAG, prompts. Ported in from Northstar-Copilot-POC, unchanged.
├── data/policy/             RAG source documents + policy_config.json/access_policy.json —
│                             also ported in unchanged.
├── backend/
│   ├── northstar_web_api/   The one FastAPI app — serves the API AND (main.py, bottom of the
│   │                         file) mounts frontend/northstar_web/ as static files, so the whole
│   │                         thing is one process, one port. Its own routers (portal login, the
│   │                         generic collections API) are unchanged from Northstar-Legacy-System;
│   │                         main.py additionally mounts copilot_api's routers (see below) onto
│   │                         this same app, under /api/ai/....
│   ├── copilot_api/          The AI's own routes (chat, invoice review, Pending Approvals, Audit
│   │                         Log). No login of its own — auth.py's get_ai_user reads the
│   │                         portal's own northstar_web_session cookie and derives the AI role
│   │                         from the already-authenticated employee (copilot/identity.py's
│   │                         PORTAL_ROLE_MAP). Ported in from Northstar-Copilot-POC — route
│   │                         prefix changed "/api" → "/api/ai" (collision avoidance) and auth.py
│   │                         rewritten to drop the separate login this way needed.
│   └── scripts/              Schema/security/seed for northstar_web (unchanged from
│                              Northstar-Legacy-System — only run one folder's northstar_web_api
│                              at a time, both point at the same database), this folder's own
│                              generate_more_data.py for a larger dataset, and the AI's own
│                              additive schema/security/RAG-ingestion scripts.
├── frontend/
│   └── northstar_web/       The shipper/employee/carrier self-service portal.
│       ├── shared/js/ai_widget.js   The chat widget — no login logic of its own, just checks
│       │                             the one portal session already in place.
│       └── employee/
│           ├── ai-approvals.html, ai-audit.html   The AI's own pages, native to this portal.
│           ├── invoice-detail.html                Unchanged except one new AI Review card.
│           └── (every other page)                 Unchanged, plus the widget.
└── docs/                    This folder's own story — the AI integration — not a duplicate of
                              Northstar-Legacy-System's own portal documentation.
```

**One database**, shared with `Northstar-Legacy-System`: `northstar_web` (carriers, users,
shipments, dock events, invoices, invoice decisions), plus the AI's own additive tables
(`dispute_flags`, `ai_invoice_reviews`, `agent_audit_log`) and Postgres roles.
Nothing about the portal's own schema changes — the AI's tables/roles sit alongside it.

**Do not create new top-level files or folders without a clear reason tied to something the user
asked for.**

**Never paste a real API key or secret into chat.** If one is ever pasted, treat it as compromised
immediately.

---

## Governance & safety — no hardcoded guardrails, no hardcoded auth

The portal's own routes (`backend/northstar_web_api/`) keep the narrower story they always had:
**never hardcode authentication** (no literal username/password checks, no magic tokens in code) —
identity comes from a real login table checked by Postgres itself (`pgcrypto`), never string
comparisons in Python. Database access is enforced by real Postgres roles/GRANTs, not
application-level checks — see `backend/scripts/northstar_web_security.sql` for the read/write app
role vs. the read-only FDE role.

The AI's own routes (`backend/copilot_api/`, `copilot/`) carry the fuller 7-layer governance model
documented in `Northstar-Copilot-POC`'s own docs (the project it was ported from) — including its
own role-based access (an Analyst login can't reach Pending Approvals, the same restriction it
always enforced) and its own database roles, distinct from the portal's. The two governance stories
coexist in one codebase now but stay conceptually separate — this project's own application code
never re-implements or hardcodes either one.

---

## Before writing any new code, run this checklist

1. Does `docs/01-how-the-ai-integration-works.md` need updating to reflect this change?
2. Is this the minimum code needed to teach the concept for this step? (See the 5 questions
   above.)
3. Does anything here touch permissions, data access, or an irreversible action? If yes, is it
   enforced by the database itself, not a hardcoded application check?
4. Does this fit inside the existing folder structure without inventing a new top-level file?
