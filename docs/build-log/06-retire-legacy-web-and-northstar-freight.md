# 06 — Retire legacy_web and northstar_freight

**Status:** done

## What we're building (written before the code)

`legacy_web` (the five disconnected "before FDE" branded systems — AP, TMS, DockTrak, Carrier
Master, TransCheck) was this project's first, narrower demonstration of "no AI, no
cross-checking." `northstar_web` (the newer self-service portal, built afterward) shows the exact
same pain point over more of the company's real workflow — booking through invoicing — and is
where the sibling AI copilot project is now actually integrating (see the sibling project's
`docs/build-log/07-point-ai-at-northstar-web.md`). Keeping both legacy demos around is redundant
once the AI reads `northstar_web` directly, so `legacy_web` and the separate `northstar_freight`
database it (and, until now, the AI) used are being retired — moved to `deletes/`, not deleted
outright.

This is purely a retirement of dead code and a dead database on this project's own side — it does
not change anything about how `northstar_web_api`/`frontend/northstar_web` work, and it happens
*after* the AI's own rewiring onto `northstar_web` was already verified working end to end.

## What we actually built (written after the code)

Moved to `deletes/`: `backend/legacy_web/` (the whole five-system FastAPI app), the standalone
`backend/legacy_carrier_safety.py` mock only that app imported, and
`backend/scripts/legacy_schema.sql` / `generate_synthetic_data.py` / `load_legacy_data.py` /
`migrate_ap_decisions.sql` — every script that provisioned `northstar_freight` or the one
`legacy_web`-specific table (`dbo.tbl_ap_invc_dcsn_raw`) on top of it.

`backend/scripts/bootstrap.sh` rewritten to drop the entire "legacy database" section — it now only
creates/migrates/seeds `northstar_web`, this project's one remaining database. `.env`/`.env.example`
lost the now-unused `DB_NAME=northstar_freight` line (`DB_ADMIN_USER`/`DB_ADMIN_PASSWORD` stay —
still needed for `northstar_web`'s own setup). `backend/scripts/README.md`,
`frontend/northstar_web/README.md`, `backend/northstar_web_api/db.py`'s module docstring, this
project's own root `README.md`/`CLAUDE.md`/`AGENTS.md` all updated to stop describing a two-database,
two-legacy-system project.

Verified nothing else in the codebase actually depended on either retired piece before moving
anything: grepped for imports of `legacy_carrier_safety` (only `legacy_web/routes/safety.py` used
it) and for any reference to `legacy_web` outside itself (found only comments/docs, no functional
coupling — `northstar_web_api` and `legacy_web` were already fully independent siblings, a legacy
of the earlier standalone carve-out). Stopped the running `legacy_web` process (port 8001) as the
last step.

## Key decisions

**Moved to `deletes/`, not deleted outright.** Consistent with how every other superseded piece of
this project has been retired (the original combined source tree, the pre-split `docs/`) — kept for
reference rather than lost.

**No functional changes anywhere else in this project.** `northstar_web_api` and
`frontend/northstar_web` are untouched beyond doc/comment accuracy — they never depended on
`legacy_web` or `northstar_freight` to begin with (confirmed by the dependency check above, not
assumed), so retiring both was a pure subtraction, not a refactor.

**Sequenced after the AI's own migration, not before.** `Northstar-Copilot-POC` was fully rewired
onto `northstar_web` and verified working (real login, a full reconciliation + flag-logging round
trip, RBAC integration tests) before this project's own `legacy_web`/`northstar_freight` were
touched — so at no point was there a window where the AI's old data source was gone and its new one
wasn't confirmed working yet.
