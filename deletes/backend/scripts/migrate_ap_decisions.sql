-- ====================================================================
-- NORTHSTAR FREIGHT — AP INVOICE DECISION LOG
-- Purpose: the one new legacy table needed for the legacy web simulation
-- (backend/legacy_web/) to record a real Approve/Hold decision on an invoice.
-- Same cryptic-legacy-column-name convention as scripts/legacy_schema.sql.
-- ====================================================================

-- ------------------------------------------
-- AP DECISIONS — one row per Approve/Hold decision made on an invoice
-- ------------------------------------------
CREATE TABLE IF NOT EXISTS dbo.tbl_ap_invc_dcsn_raw (
    dcsn_id       SERIAL PRIMARY KEY,
    invc_id       INTEGER REFERENCES dbo.tbl_carr_invc_raw(invc_id),
    dcsn_cd       TEXT NOT NULL,  -- 'APPROVED' or 'HOLD'
    dcsn_by_txt   TEXT NOT NULL,  -- free-text name, no real identity system here
    dcsn_note_txt TEXT,
    dcsn_ts       TIMESTAMP NOT NULL DEFAULT now()
);
