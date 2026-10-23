-- ====================================================================
-- NORTHSTAR WEB — PORTAL ACCESS REQUESTS
-- The one table frontend/northstar_web/portal-access.html's "Request
-- Access" form writes to — reachable by anonymous visitors (a company
-- with no account yet), so it's served by its own unauthenticated
-- endpoint (POST /api/portal-access-requests in
-- backend/northstar_web_api/main.py), not the generic session-gated
-- collections router. Same shape as northstar_web_migrate_contact.sql's
-- contact_inquiries, kept as its own table since this is a distinct kind
-- of inbound request (onboarding, not a general inquiry).
-- Run after scripts/northstar_web_security.sql.
-- Run: psql -d northstar_web -f scripts/northstar_web_migrate_portal_access_requests.sql
-- ====================================================================

-- ------------------------------------------
-- PORTAL ACCESS REQUESTS — one row per submitted "Request Access" form
-- ------------------------------------------
CREATE TABLE IF NOT EXISTS portal_access_requests (
    id            SERIAL PRIMARY KEY,
    company_name  TEXT NOT NULL,
    work_email    TEXT NOT NULL,
    account_type  TEXT NOT NULL,
    submitted_at  TIMESTAMP NOT NULL DEFAULT now()
);

-- ------------------------------------------
-- GRANTS — same discipline as every other table: app role read/write,
-- FDE role read-only, no one else
-- ------------------------------------------
GRANT SELECT, INSERT ON portal_access_requests TO northstar_web_app;
GRANT USAGE ON SEQUENCE portal_access_requests_id_seq TO northstar_web_app;
GRANT SELECT ON portal_access_requests TO northstar_web_fde_ro;
