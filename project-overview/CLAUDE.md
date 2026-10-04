# Project Instructions — Northstar Freight

This file is read automatically at the start of every session in this project. **Read it fully
before writing any code.** It exists because this project is being *taught*, not just shipped —
every line of code needs to be something a student can read and understand, not just something
that works.

---

## What this project is

Northstar Freight is a fictional freight brokerage. We're building a Forward Deployed Engineer
(FDE)–style AI copilot that reads carrier invoices/rate confirmations, catches billing errors and
fraud risk before payment, and lets a human approve anything serious. Full details: see `README.md`
and the docs linked from it.

The project is split into three parts, mirroring how a real FDE engagement unfolds:
**1. Legacy System** (`Northstar-Legacy-System/` — a fully standalone project: understand the
customer and their existing pre-AI environment, build a faithful simulation of it, no AI anywhere
in it); **2. Standalone Copilot POC** (`Northstar-Copilot-POC/` — also fully standalone: build the
AI system, make it safe and reliable, pitch it to stakeholders — deliberately *not* wired into the
legacy system); **3. Integration** (underway, two layers — the AI reads/writes `northstar_web`
directly in `Northstar-Copilot-POC/`, `legacy_web` retired as a result; and, separately,
`Northstar-Legacy-With-AI/`, a copy of the legacy portal with a chat widget and AI review panel
woven in additively, nothing removed or rewritten; a handoff package still to come). Don't jump
ahead — code for a later phase shouldn't appear before its phase's groundwork exists. **Each
standalone folder has its own `CLAUDE.md`** with the folder-structure details specific to what's
actually inside it — read that one too when working inside any of them; this root file covers the
philosophy and rules that apply everywhere, plus this top level's own layout.

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

When in doubt, write **less** code and **more** explanation in the accompanying doc (see below). A
short script with a clear comment explaining *why* teaches better than a clever one-liner or an
over-engineered class hierarchy.

**Every logical block of code gets a banner comment, in every file, wherever it's possible to add
one.** This project is read by students seeing the code for the first time — a labeled block
(imports, a function, a SQL statement, a config section) is faster to orient in than an unlabeled
wall of code. Format:

```
# ------------------------------------------
# SHORT LABEL — one clause on what this block does
# ------------------------------------------
```

Use the file's own comment syntax (`#` for Python/shell/SQL, `--` for `.sql` files that already
lean on SQL-style comments, etc.). This sits *alongside* the existing "explain why, not what" rule
for inline comments — the banner names the block, a targeted inline comment (where one already
exists) still carries the non-obvious reasoning. Keep the label itself short (a few words) so it
reads as a label, not a paragraph.

---

## Documentation is not optional — it's part of every step

A significant change gets reflected in the relevant folder's `docs/` — not as a build diary, but as
an update to whichever concept doc it actually affects (company profile, architecture, glossary,
governance, ...). Each of the three project folders keeps its own `docs/` capped at 5-6 flat files,
written for a student studying the concept, not for tracking what was built when — see each
folder's own `docs/PROJECT_SUMMARY.md` for its current structure.

---

## Top-level folder structure — don't deviate without a reason

```
FDE-Freight Project/
├── CLAUDE.md                      ← this file
├── README.md                      ← the one kept overview: what this project is, its three parts,
│                                     next planned steps
├── COMMANDS.md                    ← real, tested commands for deploying/tearing down both GCP
│                                     deployments (Legacy-System, Legacy-With-AI)
├── prompts.md                     ← architecture-diagram prompts for this project, grounded in
│                                     its real code (not generic placeholders)
├── Northstar-Legacy-System/       ← fully standalone: the "before FDE" world, own docs/ (see its
│                                     own CLAUDE.md) — never touched to integrate the AI
├── Northstar-Copilot-POC/         ← fully standalone: the AI copilot POC, own docs/ (see its own
│                                     CLAUDE.md)
└── Northstar-Legacy-With-AI/      ← a copy of Northstar-Legacy-System with the AI copilot woven
                                      in additively (chat widget + AI review panel) — the concrete
                                      Phase 3 deliverable, own docs/ (see its own CLAUDE.md)
```

The RAG policy source documents (`data/policy/`) live **inside** each project that actually reads
them — `Northstar-Copilot-POC/data/policy/` and `Northstar-Legacy-With-AI/data/policy/` — kept in
sync with each other by hand when a policy changes, not duplicated from a shared root copy.
`Northstar-Legacy-System` has no AI and no `data/` folder at all.

**Do not create new top-level files or folders without a clear reason tied to something the user
asked for.** If a new file seems needed, prefer adding it under an existing folder over inventing a
new top-level location — and prefer adding it inside whichever of the two standalone folders it
actually belongs to, not at this root.

**Never paste a real API key or secret into chat.** If one is ever pasted, treat it as compromised
immediately — the user should revoke/rotate it right away, and it should never be written into any
file.

---

## Governance & safety — no hardcoded guardrails, no hardcoded auth

Full model: `Northstar-Copilot-POC/docs/05-governance-and-safety.md` (since this is specifically
about the AI system) — 7 layers: identity, data governance, guardrail/policy checks, tool
authorization, agent reasoning oversight, observability/audit, human escalation.

The short version, for every piece of code touching safety/permissions:

- **Never write a permission or policy check as a bare `if` buried inside business logic.** Route
  decisions through a small, separate, inspectable structure — a policy table, a permission
  matrix, or a graph-based router. A new rule should mean *adding a row to a table or a new graph
  edge*, not writing new branching code.
- **Never hardcode authentication** (no literal username/password checks, no magic tokens in
  code). Identity should come from one consistent identity/claims object that every layer reads —
  even in a mocked/teaching version, mock it as a structured object, not string comparisons.
- **High-stakes actions (payment holds, blocking a carrier, anything above an agreed cost
  threshold) always require the Human-in-the-Loop approval layer.** This is not a suggestion —
  it's the one guardrail that should never be bypassed, even in a demo.

---

## Before writing any new code, run this checklist

1. Does a `docs/` file in the relevant folder need updating to reflect this change?
2. Is this the minimum code needed to teach the concept for this step? (See the 5 questions
   above.)
3. Does anything here touch permissions, data access, or an irreversible action? If yes, does it
   go through the governance layers above — not a hardcoded check?
4. Does this fit inside the existing folder structure — of whichever of the three standalone
   projects it belongs to — without inventing a new top-level file?
