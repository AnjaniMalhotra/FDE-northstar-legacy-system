# 02 — Synthetic Legacy System & Database-Enforced Security

**Status:** done — built and tested end to end

## What we're building (the plan)

A fake "legacy" freight brokerage database: take clean, realistic data, deliberately rename every
column into cryptic legacy-style codes, and load it into a real database. Then, on top of that
mess, build clean semantic views and a locked-down database login the AI agent will use — enforced
by Postgres itself, not an `if` check in Python. This gives us something real to reconcile later:
carrier invoices that sometimes overbill detention charges, checkable against actual dock
arrival/departure timestamps.

## What we actually built

**Local database:** `northstar_freight`, Postgres 15, no Docker needed.

**Synthetic data** (`generate_synthetic_data.py` → `data/synthetic/*.csv`, gitignored): 12
carriers, 150 loads, 300 dock events, 150 invoices. ~20% of invoices are seeded with an inflated
detention charge; two carriers (IDs 3 and 7) are "repeat offenders" who account for most of them —
something for a later fraud/risk-pattern feature to find. Deterministic (seeded random).

**The "legacy" schema** (`legacy_schema.sql`): four tables in a `dbo` schema, with intentionally
cryptic column names — e.g. `tbl_carr_invc_raw.detn_hrs_billed_qty` instead of
`detention_hours_billed`. Genuinely what a "data archaeology" first look feels like.

**The loader** (`load_legacy_data.py`): reads the clean CSVs, renames every column to its ugly
legacy equivalent, loads into the `dbo` tables.

**Clean semantic views + real RBAC** (`setup_views_and_security.sql`): a `northstar_views` schema
with readable views (`vw_carriers`, `vw_loads`, `vw_dock_events`, `vw_carrier_invoices`)
translating the legacy columns back to plain English; an append-only `agent_audit_log` table; a
dedicated Postgres login, `northstar_agent_ro`, granted `SELECT` on the four views and
`INSERT`-only on the audit log, with `REVOKE ALL` on the entire `dbo` schema — the **only**
identity the AI agent ever connects as.

**Verified, not assumed** — connected as `northstar_agent_ro` and confirmed: ✅ can read the clean
views, ❌ cannot read the raw `dbo` tables (`permission denied for schema dbo`), ✅ can insert into
the audit log, ❌ cannot delete from it (`permission denied`).

## Two real bugs hit and fixed

1. **`psycopg[binary]` rejected date strings from the CSV as a type mismatch.** Pandas passed
   dates as plain text; Postgres expected real `DATE`/`TIMESTAMP` values. Fixed by explicitly
   parsing those columns with `pd.to_datetime(..., format="ISO8601")` before loading.
2. **Granting `INSERT` on the audit log table wasn't enough — the insert still failed.** A
   `SERIAL` primary key is backed by a hidden sequence, and Postgres requires a *separate*
   `GRANT USAGE ON SEQUENCE ...` for anything to insert into a table that auto-generates IDs. Easy
   to miss, a good real-world RBAC lesson: permissions can be more granular than they look.

## Key decisions

- **Postgres over SQLite:** SQLite can't do multi-role `GRANT`/`DENY` — no concept of a separate
  low-privilege login inside a single file. The whole point of this step is teaching
  *database-enforced* RBAC, so Postgres was the only real option.
- **Detention as the one pain point, not "all invoice errors":** matches the scope decision from
  [01-kickoff-and-scoping.md](01-kickoff-and-scoping.md) — a focused, checkable target beats a
  vague "find anything wrong" mandate.
