#!/usr/bin/env bash
# One-shot legacy-system bootstrap. Sequences the steps documented in
# README.md, in order. Safe to re-run: every .sql file guards its own
# CREATE/ADD statements, and the one non-idempotent step (seeding
# northstar_web) is skipped if it looks like it already ran. No AI/POC
# setup here — see the separate copilot repo for that (and see
# docs/build-log/06-retire-legacy-web-and-northstar-freight.md for why this
# script no longer provisions a second, legacy-shaped database at all).
set -euo pipefail

cd "$(dirname "$0")/.."   # backend/

# ------------------------------------------
# CONNECTION ENV — point psql at Postgres using the admin login
# ------------------------------------------
export PGHOST="$DB_HOST"
export PGPORT="$DB_PORT"
export PGUSER="$DB_ADMIN_USER"
export PGPASSWORD="$DB_ADMIN_PASSWORD"

# ------------------------------------------
# NORTHSTAR_WEB DATABASE — schema, security, and seed data for the
# self-service portal, this project's one remaining database
# ------------------------------------------
echo "[bootstrap] Ensuring database '${NORTHSTAR_WEB_DB_NAME:-northstar_web}' exists..."
psql -d postgres -tc "SELECT 1 FROM pg_database WHERE datname = '${NORTHSTAR_WEB_DB_NAME:-northstar_web}'" | grep -q 1 \
    || psql -d postgres -c "CREATE DATABASE ${NORTHSTAR_WEB_DB_NAME:-northstar_web}"

echo "[bootstrap] Setting up northstar_web database..."
psql -d "${NORTHSTAR_WEB_DB_NAME:-northstar_web}" -f scripts/northstar_web_schema.sql
psql -d "${NORTHSTAR_WEB_DB_NAME:-northstar_web}" -f scripts/northstar_web_security.sql
psql -d "${NORTHSTAR_WEB_DB_NAME:-northstar_web}" -f scripts/northstar_web_migrate_contact.sql

WEB_ROW_COUNT=$(psql -d "${NORTHSTAR_WEB_DB_NAME:-northstar_web}" -tAc "SELECT COUNT(*) FROM carriers" 2>/dev/null || echo 0)
if [ "$WEB_ROW_COUNT" -eq 0 ]; then
    echo "[bootstrap] No northstar_web data found — seeding..."
    python3 scripts/seed_northstar_web_data.py
else
    echo "[bootstrap] northstar_web data already seeded ($WEB_ROW_COUNT carriers) — skipping."
fi

echo "[bootstrap] Done."
