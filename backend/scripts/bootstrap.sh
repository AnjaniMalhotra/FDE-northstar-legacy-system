#!/usr/bin/env bash
# One-shot bootstrap for the portal AND the AI copilot — one database, one
# set of setup scripts. Safe to re-run: every .sql file guards its own
# CREATE/ADD statements, and the one non-idempotent step (seeding
# northstar_web) is skipped if it looks like it already ran.
set -euo pipefail

cd "$(dirname "$0")/.."   # backend/

# ------------------------------------------
# CONNECTION ENV — point psql at Postgres using the admin login. DB_PORT
# defaults to 5432 even for the Cloud SQL Unix socket case (DB_HOST set to
# a socket directory by docker-entrypoint.sh) — libpq still needs a port
# number to build the actual socket filename (.s.PGSQL.<port>), and Cloud
# Run's own environment never sets DB_PORT at all (only INSTANCE_CONNECTION_NAME).
# ------------------------------------------
export PGHOST="$DB_HOST"
export PGPORT="${DB_PORT:-5432}"
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
psql -d "${NORTHSTAR_WEB_DB_NAME:-northstar_web}" \
    -v app_password="$NORTHSTAR_WEB_APP_PASSWORD" \
    -v fde_password="$NORTHSTAR_WEB_FDE_PASSWORD" \
    -f scripts/northstar_web_security.sql
psql -d "${NORTHSTAR_WEB_DB_NAME:-northstar_web}" -f scripts/northstar_web_migrate_contact.sql

WEB_ROW_COUNT=$(psql -d "${NORTHSTAR_WEB_DB_NAME:-northstar_web}" -tAc "SELECT COUNT(*) FROM carriers" 2>/dev/null || echo 0)
if [ "$WEB_ROW_COUNT" -eq 0 ]; then
    echo "[bootstrap] No northstar_web data found — seeding starter data..."
    python3 scripts/seed_northstar_web_data.py
else
    echo "[bootstrap] northstar_web data already seeded ($WEB_ROW_COUNT carriers) — skipping starter seed."
fi

echo "[bootstrap] Scaling up to the full demo dataset (25 carriers, 100 shippers, 5,000 invoices)..."
python3 scripts/generate_more_data.py

# ------------------------------------------
# AI COPILOT — purely additive tables/roles on top of the same database
# ------------------------------------------
echo "[bootstrap] Applying the AI copilot's own additive schema and security..."
psql -d "${NORTHSTAR_WEB_DB_NAME:-northstar_web}" -f scripts/northstar_web_ai_schema.sql
psql -d "${NORTHSTAR_WEB_DB_NAME:-northstar_web}" \
    -v agent_password="$DB_AGENT_PASSWORD" \
    -v analyst_password="$DB_ANALYST_PASSWORD" \
    -v manager_password="$DB_MANAGER_PASSWORD" \
    -v admin_password="$DB_HUMAN_ADMIN_PASSWORD" \
    -f scripts/northstar_web_ai_security.sql

if [ -n "${PINECONE_API_KEY:-}" ]; then
    echo "[bootstrap] Ingesting policy documents into Pinecone..."
    python3 scripts/ingest_policy_documents.py
else
    echo "[bootstrap] PINECONE_API_KEY not set — skipping RAG ingestion. The agent's"
    echo "[bootstrap] policy search will not work until this is set and re-run."
fi

echo "[bootstrap] Done."
