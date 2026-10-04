-- ====================================================================
-- NORTHSTAR WEB — DATABASE-ENFORCED SECURITY
-- Two roles, same discipline as scripts/setup_views_and_security.sql:
-- one read/write login for the FastAPI backend's own connection, and one
-- strictly read-only login for an FDE (human, or the AI copilot) to
-- connect to directly — no shared admin login, nothing granted "just in
-- case." Run after scripts/northstar_web_schema.sql.
--
-- Both passwords are psql variables, not hardcoded literals, so the same
-- script works unchanged against a local database or a fresh one with a
-- generated password. bootstrap.sh passes them in; run by hand with:
--   psql -d northstar_web -v app_password="$NORTHSTAR_WEB_APP_PASSWORD" \
--        -v fde_password="$NORTHSTAR_WEB_FDE_PASSWORD" \
--        -f scripts/northstar_web_security.sql
-- ====================================================================

-- ------------------------------------------
-- APP ROLE — the FastAPI backend's own identity; full read/write
-- ------------------------------------------
-- psql doesn't interpolate :'variables' inside a dollar-quoted DO $$ ... $$
-- block, so role creation is a \gexec instead: the SELECT below is built
-- (with the password already substituted) only when the role is missing,
-- and \gexec runs whatever comes back as SQL. The ALTER after it always
-- runs, so a rerun stays in sync with whatever password was just passed in.
SELECT 'CREATE ROLE northstar_web_app WITH LOGIN PASSWORD ' || quote_literal(:'app_password')
WHERE NOT EXISTS (SELECT FROM pg_catalog.pg_roles WHERE rolname = 'northstar_web_app')
\gexec

ALTER ROLE northstar_web_app WITH PASSWORD :'app_password';

GRANT USAGE ON SCHEMA public TO northstar_web_app;
GRANT SELECT, INSERT, UPDATE, DELETE ON ALL TABLES IN SCHEMA public TO northstar_web_app;
GRANT USAGE ON ALL SEQUENCES IN SCHEMA public TO northstar_web_app;

-- ------------------------------------------
-- FDE ROLE — strictly read-only; this is the login a real FDE (or the AI
-- copilot) connects to the database with directly, bypassing the API
-- entirely — same pattern as northstar_agent_ro on the other database.
-- ------------------------------------------
SELECT 'CREATE ROLE northstar_web_fde_ro WITH LOGIN PASSWORD ' || quote_literal(:'fde_password')
WHERE NOT EXISTS (SELECT FROM pg_catalog.pg_roles WHERE rolname = 'northstar_web_fde_ro')
\gexec

ALTER ROLE northstar_web_fde_ro WITH PASSWORD :'fde_password';

GRANT USAGE ON SCHEMA public TO northstar_web_fde_ro;
GRANT SELECT ON ALL TABLES IN SCHEMA public TO northstar_web_fde_ro;
-- No INSERT/UPDATE/DELETE grant at all — enforced by Postgres itself, not
-- by anything an FDE's own client could choose to skip.

-- Column-level restriction: no login should ever be able to read another
-- user's password hash back out, including the FDE role or the app role's
-- own general SELECT — application code fetches by exact email during
-- login, but nothing should ever list password_hash in bulk.
REVOKE SELECT ON users FROM northstar_web_fde_ro;
GRANT SELECT (id, portal, role, email, name, company_name, carrier_id) ON users TO northstar_web_fde_ro;
