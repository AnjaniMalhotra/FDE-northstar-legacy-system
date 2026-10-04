-- ------------------------------------------
-- NORTHSTAR_WEB AI SECURITY — 4 new, purely additive Postgres roles (1
-- agent + 3 human) so AI data access is enforced by the database itself,
-- not application-level `if role == ...` checks — the same principle
-- already used for northstar_freight (scripts' setup_views_and_security.sql
-- / migrate_identity_v3.sql there). These roles are new logins on top of
-- northstar_web; they never touch northstar_web_app or northstar_web_fde_ro,
-- and every GRANT below is SELECT-only on Legacy-owned tables — no ALTER,
-- no write access to anything this project doesn't own.
--
-- All 4 passwords are psql variables, not hardcoded literals, so the same
-- script works unchanged against a local database or a fresh one with a
-- generated password (same pattern as northstar_web_security.sql). Run
-- by hand with:
--   psql -d northstar_web -v agent_password="$DB_AGENT_PASSWORD" \
--        -v analyst_password="$DB_ANALYST_PASSWORD" \
--        -v manager_password="$DB_MANAGER_PASSWORD" \
--        -v admin_password="$DB_HUMAN_ADMIN_PASSWORD" \
--        -f scripts/northstar_web_ai_security.sql
-- ------------------------------------------

-- ------------------------------------------
-- AGENT ROLE — the AI's own restricted connection (copilot/database.py).
-- Read-only on Legacy's existing tables; insert-only on the AI's own 4
-- tables (never reads dispute_flags/agent_audit_log back — mirrors
-- northstar_agent_ro's exact shape on northstar_freight).
--
-- psql doesn't interpolate :'variables' inside a dollar-quoted DO $$ ... $$
-- block, so role creation is a \gexec instead: the SELECT below is built
-- (with the password already substituted) only when the role is missing,
-- and \gexec runs whatever comes back as SQL. The ALTER after it always
-- runs, so a rerun stays in sync with whatever password was just passed in.
-- ------------------------------------------
SELECT 'CREATE ROLE northstar_web_agent WITH LOGIN PASSWORD ' || quote_literal(:'agent_password')
WHERE NOT EXISTS (SELECT FROM pg_catalog.pg_roles WHERE rolname = 'northstar_web_agent')
\gexec

ALTER ROLE northstar_web_agent WITH PASSWORD :'agent_password';

GRANT USAGE ON SCHEMA public TO northstar_web_agent;
GRANT SELECT ON carriers, shipments, dock_events, invoices, invoice_decisions TO northstar_web_agent;
GRANT SELECT, INSERT ON dispute_flags, ai_invoice_reviews TO northstar_web_agent;
GRANT INSERT ON agent_audit_log TO northstar_web_agent;
GRANT USAGE ON dispute_flags_flag_id_seq, agent_audit_log_log_id_seq TO northstar_web_agent;

-- ------------------------------------------
-- ANALYST — reviews invoices, proposes flags via the agent. Read-only
-- everywhere, including the AI's own tables (log_dispute_flag always
-- writes through the agent's own role, never the human's). Also the one
-- role permitted to read users.password_hash, used only by
-- copilot/identity.py's authenticate() to check a login for ANY role —
-- mirrors northstar_freight's identical ANALYST-only password_hash grant.
-- ------------------------------------------
SELECT 'CREATE ROLE northstar_web_analyst WITH LOGIN PASSWORD ' || quote_literal(:'analyst_password')
WHERE NOT EXISTS (SELECT FROM pg_catalog.pg_roles WHERE rolname = 'northstar_web_analyst')
\gexec

ALTER ROLE northstar_web_analyst WITH PASSWORD :'analyst_password';

GRANT USAGE ON SCHEMA public TO northstar_web_analyst;
GRANT SELECT ON carriers, shipments, dock_events, invoices, invoice_decisions TO northstar_web_analyst;
GRANT SELECT ON dispute_flags, ai_invoice_reviews TO northstar_web_analyst;
GRANT SELECT (id, portal, role, email, name, company_name, carrier_id, password_hash) ON users TO northstar_web_analyst;

-- ------------------------------------------
-- MANAGER — everything Analyst has, plus resolving a pending flag
-- (Approve/Reject) and recording the human Approve/Hold decision on an
-- AI-reviewed invoice. No access to dispute_outcome
-- — those stay Admin-only (see below).
-- ------------------------------------------
SELECT 'CREATE ROLE northstar_web_manager WITH LOGIN PASSWORD ' || quote_literal(:'manager_password')
WHERE NOT EXISTS (SELECT FROM pg_catalog.pg_roles WHERE rolname = 'northstar_web_manager')
\gexec

ALTER ROLE northstar_web_manager WITH PASSWORD :'manager_password';

GRANT USAGE ON SCHEMA public TO northstar_web_manager;
GRANT SELECT ON carriers, shipments, dock_events, invoices, invoice_decisions TO northstar_web_manager;
GRANT SELECT ON dispute_flags, ai_invoice_reviews, agent_audit_log TO northstar_web_manager;
GRANT UPDATE (status, resolved_by, resolved_at) ON dispute_flags TO northstar_web_manager;
GRANT UPDATE (decision, decided_by, decided_at) ON ai_invoice_reviews TO northstar_web_manager;
GRANT SELECT (id, portal, role, email, name, company_name, carrier_id) ON users TO northstar_web_manager;

-- ------------------------------------------
-- ADMIN — everything Manager has, plus the one capability the AI's
-- original design gave a separate COMPLIANCE role (recording a dispute
-- outcome). COMPLIANCE itself is a known, deliberate gap this pass — see
-- the build-log entry — since adding it would mean creating a new portal
-- login, which is off-limits here.
-- ------------------------------------------
SELECT 'CREATE ROLE northstar_web_admin WITH LOGIN PASSWORD ' || quote_literal(:'admin_password')
WHERE NOT EXISTS (SELECT FROM pg_catalog.pg_roles WHERE rolname = 'northstar_web_admin')
\gexec

ALTER ROLE northstar_web_admin WITH PASSWORD :'admin_password';

GRANT USAGE ON SCHEMA public TO northstar_web_admin;
GRANT SELECT ON carriers, shipments, dock_events, invoices, invoice_decisions TO northstar_web_admin;
GRANT SELECT ON dispute_flags, ai_invoice_reviews, agent_audit_log TO northstar_web_admin;
GRANT UPDATE (status, resolved_by, resolved_at, dispute_outcome, dispute_outcome_by, dispute_outcome_at) ON dispute_flags TO northstar_web_admin;
GRANT UPDATE (decision, decided_by, decided_at) ON ai_invoice_reviews TO northstar_web_admin;
GRANT SELECT (id, portal, role, email, name, company_name, carrier_id) ON users TO northstar_web_admin;
