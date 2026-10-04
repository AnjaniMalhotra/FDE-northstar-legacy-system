#!/usr/bin/env bash
# Container startup: wait for Postgres to actually accept connections (not
# just for its container to start), bootstrap the database (idempotent —
# safe on every container start), then run the app.
set -euo pipefail

# ------------------------------------------
# RESOLVE THE DB HOST bootstrap.sh's psql calls will use — a Cloud SQL Unix
# socket when running on Cloud Run (INSTANCE_CONNECTION_NAME set, mounted
# at /cloudsql/<name> by the cloud_sql_instance volume in deploy/terraform/
# run.tf), otherwise plain TCP: the "db" container in docker-compose.yml,
# local Postgres, or the Cloud SQL Auth Proxy. backend/northstar_web_api/
# db.py resolves the same way, independently, for the app's own connection.
# ------------------------------------------
if [ -n "${INSTANCE_CONNECTION_NAME:-}" ]; then
    export DB_HOST="/cloudsql/${INSTANCE_CONNECTION_NAME}"
fi

echo "[entrypoint] Waiting for database at ${DB_HOST}..."
until PGPASSWORD="$DB_ADMIN_PASSWORD" pg_isready -h "$DB_HOST" -p "${DB_PORT:-5432}" -U "$DB_ADMIN_USER" >/dev/null 2>&1; do
    sleep 1
done

bash backend/scripts/bootstrap.sh

exec uvicorn backend.northstar_web_api.main:app --host 0.0.0.0 --port "${PORT:-8080}"
