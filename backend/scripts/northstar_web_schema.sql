-- ====================================================================
-- NORTHSTAR WEB — DATABASE SCHEMA
-- This project's one database, for frontend/northstar_web/ (the shipper/
-- employee/carrier site). Clean, readable table/column names — a modern
-- system built from scratch. The sibling AI copilot project reads and
-- writes this same database directly now too, via its own added-on-top
-- tables/roles (see docs/build-log/06-retire-legacy-web-and-northstar-freight.md)
-- — nothing in this file changes to accommodate that.
-- Run via backend/scripts/bootstrap.sh, which creates the database (named by
-- $NORTHSTAR_WEB_DB_NAME, not hardcoded) and connects to it before running
-- this file.
-- ====================================================================

-- ------------------------------------------
-- PGCRYPTO — same technique scripts/migrate_identity_v4.sql already uses
-- for password hashing, so no new Python auth library is needed
-- ------------------------------------------
CREATE EXTENSION IF NOT EXISTS pgcrypto;

-- ------------------------------------------
-- CARRIERS — the vetted carrier network
-- ------------------------------------------
CREATE TABLE IF NOT EXISTS carriers (
    id                       SERIAL PRIMARY KEY,
    name                     TEXT NOT NULL,
    mc_number                TEXT NOT NULL,
    safety_rating            TEXT NOT NULL,
    oos_violations           INTEGER NOT NULL DEFAULT 0,
    insurance_status         TEXT NOT NULL,
    active_since             DATE,
    detention_free_hours     NUMERIC(5, 2) NOT NULL DEFAULT 2,
    detention_rate_per_hour  NUMERIC(8, 2) NOT NULL DEFAULT 65,
    rate_factor              NUMERIC(4, 2) NOT NULL DEFAULT 1.0,
    elevated_risk            BOOLEAN NOT NULL DEFAULT FALSE
);

-- ------------------------------------------
-- USERS — one table for all three portals (shipper/employee/carrier logins)
-- ------------------------------------------
CREATE TABLE IF NOT EXISTS users (
    id             SERIAL PRIMARY KEY,
    portal         TEXT NOT NULL CHECK (portal IN ('SHIPPER', 'EMPLOYEE', 'CARRIER')),
    role           TEXT,  -- only meaningful for portal = 'EMPLOYEE'
    email          TEXT NOT NULL UNIQUE,
    password_hash  TEXT NOT NULL,
    name           TEXT NOT NULL,
    company_name   TEXT,
    carrier_id     INTEGER REFERENCES carriers(id)
);

-- ------------------------------------------
-- SESSIONS — opaque server-issued tokens, checked on every API request
-- ------------------------------------------
CREATE TABLE IF NOT EXISTS sessions (
    token       TEXT PRIMARY KEY,
    user_id     INTEGER NOT NULL REFERENCES users(id),
    created_at  TIMESTAMP NOT NULL DEFAULT now(),
    expires_at  TIMESTAMP NOT NULL
);

-- ------------------------------------------
-- SHIPMENT REQUESTS — a shipper's booking ask, before Operations decides
-- ------------------------------------------
CREATE TABLE IF NOT EXISTS shipment_requests (
    id                SERIAL PRIMARY KEY,
    shipper_id        INTEGER NOT NULL REFERENCES users(id),
    origin            TEXT NOT NULL,
    dest              TEXT NOT NULL,
    weight_lbs        INTEGER NOT NULL,
    goods_description TEXT NOT NULL,
    pickup_date       DATE NOT NULL,
    carrier_id        INTEGER NOT NULL REFERENCES carriers(id),
    quoted_price      NUMERIC(10, 2) NOT NULL,
    status            TEXT NOT NULL DEFAULT 'PENDING_REVIEW',
    employee_note     TEXT NOT NULL DEFAULT ''
);

-- ------------------------------------------
-- SHIPMENTS — created once a request is approved
-- ------------------------------------------
CREATE TABLE IF NOT EXISTS shipments (
    id                       SERIAL PRIMARY KEY,
    request_id               INTEGER REFERENCES shipment_requests(id),
    carrier_id               INTEGER NOT NULL REFERENCES carriers(id),
    origin                   TEXT NOT NULL,
    dest                     TEXT NOT NULL,
    weight_lbs               INTEGER,
    goods_description        TEXT,
    agreed_rate               NUMERIC(10, 2) NOT NULL,
    detention_free_hours      NUMERIC(5, 2) NOT NULL,
    detention_rate_per_hour   NUMERIC(8, 2) NOT NULL,
    pickup_appt               TIMESTAMP,
    delivery_appt             TIMESTAMP,
    status                    TEXT NOT NULL DEFAULT 'SCHEDULED'
);

-- ------------------------------------------
-- DOCK EVENTS — real arrival/departure, auto-captured on delivery
-- ------------------------------------------
CREATE TABLE IF NOT EXISTS dock_events (
    id           SERIAL PRIMARY KEY,
    shipment_id  INTEGER NOT NULL REFERENCES shipments(id),
    type         TEXT NOT NULL CHECK (type IN ('ARRIVAL', 'DEPARTURE')),
    timestamp    TIMESTAMP NOT NULL
);

-- ------------------------------------------
-- INVOICES — what the carrier billed for a delivered shipment
-- ------------------------------------------
CREATE TABLE IF NOT EXISTS invoices (
    id                        SERIAL PRIMARY KEY,
    shipment_id               INTEGER NOT NULL REFERENCES shipments(id),
    carrier_id                INTEGER NOT NULL REFERENCES carriers(id),
    linehaul_amount           NUMERIC(10, 2) NOT NULL,
    detention_hours_billed    NUMERIC(5, 2) NOT NULL DEFAULT 0,
    detention_amount_billed   NUMERIC(10, 2) NOT NULL DEFAULT 0,
    fuel_surcharge            NUMERIC(10, 2) NOT NULL DEFAULT 0,
    total_amount              NUMERIC(10, 2) NOT NULL,
    status                    TEXT NOT NULL DEFAULT 'PENDING_APPROVAL',
    submitted_at              TIMESTAMP NOT NULL DEFAULT now()
);

-- ------------------------------------------
-- INVOICE DECISIONS — the approve/hold/revise history for one invoice
-- ------------------------------------------
CREATE TABLE IF NOT EXISTS invoice_decisions (
    id          SERIAL PRIMARY KEY,
    invoice_id  INTEGER NOT NULL REFERENCES invoices(id),
    decided_by  TEXT NOT NULL,
    decision    TEXT NOT NULL,  -- 'APPROVED' | 'ON_HOLD' | 'REVISED'
    note        TEXT,
    at          TIMESTAMP NOT NULL DEFAULT now()
);
