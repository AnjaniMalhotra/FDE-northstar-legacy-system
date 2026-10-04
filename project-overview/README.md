# Northstar Freight — FDE Capstone Project

A Forward Deployed Engineer (FDE)–style AI copilot for a fictional freight brokerage: it reads
carrier invoices and rate confirmations, catches billing errors and fraud risk before payment, and
lets a human approve anything serious. Built and taught the way a real FDE engagement actually
unfolds — understand the customer's messy existing systems first, then build the AI solution
alongside them, then integrate.

## The three parts of this project

This project is now split across three places, mirroring three real, separable steps of an FDE
engagement:

| | What it is | Where |
|---|---|---|
| **1. Legacy System** | The client's world as it exists *before* any AI — a self-service portal, no AI anywhere in it. See [`Northstar-Legacy-System/docs/PROJECT_SUMMARY.md`](Northstar-Legacy-System/docs/PROJECT_SUMMARY.md). | [`Northstar-Legacy-System/`](Northstar-Legacy-System/) |
| **2. Copilot POC** | The AI system itself — the agent, its tools, guardrails, RAG, and a standalone console — pitched to the client in two stages (detention/linehaul checking first, then Pending Approvals/Carrier Risk after a checkpoint meeting). See [`Northstar-Copilot-POC/docs/PROJECT_SUMMARY.md`](Northstar-Copilot-POC/docs/PROJECT_SUMMARY.md). | [`Northstar-Copilot-POC/`](Northstar-Copilot-POC/) |
| **3. Integration** | The AI reads/writes `northstar_web` directly, and a separate, lighter-footprint integration weaves a chat widget + an AI Review panel directly into a copy of the legacy portal, nothing removed or rewritten. See [`Northstar-Legacy-With-AI/docs/PROJECT_SUMMARY.md`](Northstar-Legacy-With-AI/docs/PROJECT_SUMMARY.md). | `Northstar-Copilot-POC/` + [`Northstar-Legacy-With-AI/`](Northstar-Legacy-With-AI/) |

Each of these folders is fully standalone — its own `README.md`, `requirements.txt`,
`.env.example`, and setup script. Start there for how to actually run any of them.
`Northstar-Legacy-With-AI/` is a copy of `Northstar-Legacy-System/` with the AI woven in —
`Northstar-Legacy-System/` itself is never touched, so it stays the clean "before" reference.

## Why freight, and why this specific company

The course teaches the FDE role — engineers who embed with a customer, learn their real (usually
messy) systems, and ship a working AI solution rather than a generic product. Freight brokerage was
chosen after surveying eight freight-adjacent verticals because a broker's data is genuinely messy — legacy systems, disconnected teams, manual documents —
the exact conditions that make the FDE role necessary. Northstar Freight doesn't own trucks; it
matches shippers who need freight moved with a network of carriers, earning the thin margin between
what it charges and what it pays — a margin that leaks constantly through billing mismatches and
fraud hidden inside PDFs and disconnected systems.

## Next planned steps

- **Deploy `Northstar-Legacy-System` to GCP** — Docker, Terraform (Cloud SQL, Secret Manager,
  Artifact Registry, Cloud Run), and the setup script are all built and verified locally
  (`docker compose up`); the actual `deploy/setup_gcp.sh` run against a live GCP project hasn't
  happened yet. See `Northstar-Legacy-System/README.md`.
- **A proper Compliance portal role**, a change still owed to `Northstar-Legacy-System` itself —
  deferred until it can land on `Northstar-Legacy-System`'s own `ai-integration` git branch (already
  created, in its own GitHub repo), so that project's `main` stays untouched until then.
  `Northstar-Legacy-With-AI/` is meant to become that branch's actual content once verified.

## Governance & code-quality philosophy (applies across all three parts)

Anything that reads sensitive data or takes a real action goes through a 7-layer governance model
— identity, data governance, guardrail/policy checks, tool authorization, agent reasoning
oversight, observability/audit, and human escalation — never hardcoded `if` logic, always an
inspectable rule table or router. Code quality here means the *minimum* code needed to teach each
concept, not the most complete or clever solution — see each subfolder's own `CLAUDE.md` for the
exact rules.
