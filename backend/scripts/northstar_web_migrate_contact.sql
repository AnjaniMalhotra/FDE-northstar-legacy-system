-- ====================================================================
-- NORTHSTAR WEB — CONTACT INQUIRIES
-- The one table the public marketing site (frontend/northstar_web/contact.html)
-- writes to — reachable by anonymous visitors, so it's served by its own
-- unauthenticated endpoint (POST /api/contact in
-- backend/northstar_web_api/main.py), not the generic session-gated collections
-- router. Run after scripts/northstar_web_security.sql.
-- Run: psql -d northstar_web -f scripts/northstar_web_migrate_contact.sql
-- ====================================================================

-- ------------------------------------------
-- CONTACT INQUIRIES — one row per submitted contact form
-- ------------------------------------------
CREATE TABLE IF NOT EXISTS contact_inquiries (
    id            SERIAL PRIMARY KEY,
    name          TEXT NOT NULL,
    email         TEXT NOT NULL,
    company       TEXT,
    phone         TEXT,
    subject       TEXT NOT NULL,
    message       TEXT NOT NULL,
    submitted_at  TIMESTAMP NOT NULL DEFAULT now()
);

-- ------------------------------------------
-- GRANTS — same discipline as every other table: app role read/write,
-- FDE role read-only, no one else
-- ------------------------------------------
GRANT SELECT, INSERT ON contact_inquiries TO northstar_web_app;
GRANT USAGE ON SEQUENCE contact_inquiries_id_seq TO northstar_web_app;
GRANT SELECT ON contact_inquiries TO northstar_web_fde_ro;
