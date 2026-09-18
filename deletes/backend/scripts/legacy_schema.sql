-- ====================================================================
-- NORTHSTAR FREIGHT — "LEGACY" RAW SCHEMA
-- Purpose: simulate an old, undocumented enterprise schema, the way a real
-- FDE engagement would actually find one. Column names are deliberately
-- cryptic — this is what scripts/load_legacy_data.py loads clean data into.
-- ====================================================================

-- ------------------------------------------
-- SCHEMA — the "dbo" namespace standing in for an old enterprise system
-- ------------------------------------------
CREATE SCHEMA IF NOT EXISTS dbo;

-- ------------------------------------------
-- CARRIER MASTER — one row per trucking company
-- ------------------------------------------
CREATE TABLE IF NOT EXISTS dbo.tbl_carr_mstr (
    car_id        INTEGER PRIMARY KEY,
    car_nm        TEXT NOT NULL,
    mc_nbr        TEXT,
    sfty_rtg_cd   TEXT,
    actv_dt       DATE
);

-- ------------------------------------------
-- LOAD BOOKING — one row per shipment, with the agreed rate/detention terms
-- ------------------------------------------
CREATE TABLE IF NOT EXISTS dbo.tbl_load_bkg_raw (
    ld_id             INTEGER PRIMARY KEY,
    car_id            INTEGER REFERENCES dbo.tbl_carr_mstr(car_id),
    orig_loc_txt      TEXT,
    dest_loc_txt      TEXT,
    pu_appt_ts        TIMESTAMP,
    del_appt_ts       TIMESTAMP,
    agrd_rt_amt       NUMERIC(10, 2),
    detn_free_hrs_qty NUMERIC(5, 2),
    detn_rt_hr_amt    NUMERIC(8, 2)
);

-- ------------------------------------------
-- DOCK EVENTS — real arrival/departure timestamps, the ground truth for detention
-- ------------------------------------------
CREATE TABLE IF NOT EXISTS dbo.tbl_dock_evt_raw (
    evt_id      INTEGER PRIMARY KEY,
    ld_id       INTEGER REFERENCES dbo.tbl_load_bkg_raw(ld_id),
    evt_typ_cd  TEXT,  -- 'ARRIVAL' or 'DEPARTURE'
    evt_ts      TIMESTAMP
);

-- ------------------------------------------
-- CARRIER INVOICES — what the carrier actually billed for each load
-- ------------------------------------------
CREATE TABLE IF NOT EXISTS dbo.tbl_carr_invc_raw (
    invc_id             INTEGER PRIMARY KEY,
    ld_id               INTEGER REFERENCES dbo.tbl_load_bkg_raw(ld_id),
    car_id              INTEGER REFERENCES dbo.tbl_carr_mstr(car_id),
    subm_dt             DATE,
    linehaul_amt        NUMERIC(10, 2),
    detn_hrs_billed_qty NUMERIC(5, 2),
    detn_amt_billed     NUMERIC(10, 2),
    fuel_surchg_amt     NUMERIC(10, 2),
    tot_amt             NUMERIC(10, 2)
);
