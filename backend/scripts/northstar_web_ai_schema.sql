-- ------------------------------------------
-- NORTHSTAR_WEB AI SCHEMA — the AI's own tables, added on top of the
-- northstar_web database that Northstar-Legacy-System already owns and
-- provisions. Every statement here is purely additive: new tables only,
-- never an ALTER on an existing one (carriers, shipments, dock_events,
-- invoices, invoice_decisions, users, ...) — Legacy-System's own schema and
-- functionality stay untouched. Run by this project's own bootstrap.sh,
-- against a database Legacy-System's own bootstrap has already created.
-- ------------------------------------------

-- ------------------------------------------
-- DISPUTE_FLAGS — the AI's proposed/logged discrepancy flags, one per
-- shipment+charge_type. Mirrors northstar_freight's dispute_flags, keyed on
-- shipment_id instead of load_id to match northstar_web's own vocabulary.
-- ------------------------------------------
CREATE TABLE IF NOT EXISTS dispute_flags (
    flag_id             SERIAL PRIMARY KEY,
    shipment_id         INTEGER NOT NULL REFERENCES shipments(id),
    invoice_id          INTEGER NOT NULL REFERENCES invoices(id),
    carrier_id          INTEGER NOT NULL REFERENCES carriers(id),
    discrepancy_amount  NUMERIC(10,2) NOT NULL,
    tier                TEXT NOT NULL CHECK (tier IN ('TIER_1', 'TIER_2')),
    status              TEXT NOT NULL DEFAULT 'AUTO_LOGGED'
                            CHECK (status IN ('AUTO_LOGGED', 'PENDING_APPROVAL', 'APPROVED', 'REJECTED')),
    charge_type         TEXT NOT NULL DEFAULT 'DETENTION' CHECK (charge_type IN ('DETENTION', 'LINEHAUL')),
    reasoning           TEXT NOT NULL,
    tier_reason         TEXT NOT NULL DEFAULT '',
    created_at          TIMESTAMP NOT NULL DEFAULT NOW(),
    resolved_by         TEXT,
    resolved_at         TIMESTAMP,
    dispute_outcome     TEXT CHECK (dispute_outcome IN ('UPHELD', 'DENIED')),
    dispute_outcome_by  TEXT,
    dispute_outcome_at  TIMESTAMP
);

-- ------------------------------------------
-- AGENT_AUDIT_LOG — insert-only trace of every agent step. Mirrors
-- northstar_freight's agent_audit_log exactly (no schema-specific columns).
-- ------------------------------------------
CREATE TABLE IF NOT EXISTS agent_audit_log (
    log_id      SERIAL PRIMARY KEY,
    logged_at   TIMESTAMP NOT NULL DEFAULT NOW(),
    session_id  TEXT NOT NULL,
    node_name   TEXT NOT NULL,
    tool_name   TEXT NOT NULL,
    content     TEXT NOT NULL,
    trace_id    TEXT NOT NULL DEFAULT '',
    role        TEXT NOT NULL DEFAULT '',
    latency_ms  INTEGER NOT NULL DEFAULT 0,
    metadata    JSONB NOT NULL DEFAULT '{}'
);

-- ------------------------------------------
-- AI_INVOICE_REVIEWS — the AI's own review record: "did the AI look at this
-- shipment's invoice, and did a human confirm its finding." Deliberately
-- separate from Legacy-owned invoice_decisions (the real AP payment
-- decision) rather than merged into it — merging would require altering a
-- table this project doesn't own. The invoice detail view reads both,
-- side by side.
-- ------------------------------------------
CREATE TABLE IF NOT EXISTS ai_invoice_reviews (
    shipment_id  INTEGER PRIMARY KEY REFERENCES shipments(id),
    reviewed_at  TIMESTAMP NOT NULL DEFAULT NOW(),
    decision     TEXT CHECK (decision IN ('APPROVED', 'ON_HOLD')),
    decided_by   TEXT,
    decided_at   TIMESTAMP,
    ai_review    JSONB
);
