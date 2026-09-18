"""
Loads the clean synthetic CSVs (data/synthetic/) into the "legacy" raw tables
(scripts/legacy_schema.sql), renaming every column to its cryptic legacy code
along the way. This is the entire "messy legacy system" simulation — no real
old system needed, just deliberate obfuscation of clean data.

Run scripts/generate_synthetic_data.py first.
"""
# ------------------------------------------
# IMPORTS — standard library, env loading, pandas, and the DB engine
# ------------------------------------------
import os
from pathlib import Path

import pandas as pd
from dotenv import load_dotenv
from sqlalchemy import create_engine

# ------------------------------------------
# PROJECT PATH AND ENV — load .env from the project root
# ------------------------------------------
project_root = Path(__file__).resolve().parents[2]
load_dotenv(project_root / ".env")

DATA_DIR = project_root / "data" / "synthetic"

# ------------------------------------------
# DATABASE CONNECTION — admin engine used to load into the raw legacy tables
# ------------------------------------------
db_url = (
    f"postgresql+psycopg://{os.getenv('DB_ADMIN_USER')}:{os.getenv('DB_ADMIN_PASSWORD')}"
    f"@{os.getenv('DB_HOST', 'localhost')}:{os.getenv('DB_PORT', '5432')}/{os.getenv('DB_NAME')}"
)
engine = create_engine(db_url)

# clean CSV column -> ugly legacy column, per raw table
# ------------------------------------------
# TABLE COLUMN MAP — clean CSV column names mapped to their cryptic legacy equivalents
# ------------------------------------------
TABLE_COLUMN_MAP = {
    "tbl_carr_mstr": {
        "carrier_id": "car_id", "carrier_name": "car_nm", "mc_number": "mc_nbr",
        "safety_rating": "sfty_rtg_cd", "active_since": "actv_dt",
    },
    "tbl_load_bkg_raw": {
        "load_id": "ld_id", "carrier_id": "car_id", "origin_city": "orig_loc_txt",
        "dest_city": "dest_loc_txt", "pickup_appt": "pu_appt_ts", "delivery_appt": "del_appt_ts",
        "agreed_rate": "agrd_rt_amt", "detention_free_hours": "detn_free_hrs_qty",
        "detention_rate_per_hour": "detn_rt_hr_amt",
    },
    "tbl_dock_evt_raw": {
        "event_id": "evt_id", "load_id": "ld_id", "event_type": "evt_typ_cd", "event_ts": "evt_ts",
    },
    "tbl_carr_invc_raw": {
        "invoice_id": "invc_id", "load_id": "ld_id", "carrier_id": "car_id",
        "submitted_date": "subm_dt", "linehaul_amount": "linehaul_amt",
        "detention_hours_billed": "detn_hrs_billed_qty", "detention_amount_billed": "detn_amt_billed",
        "fuel_surcharge_amount": "fuel_surchg_amt", "total_amount": "tot_amt",
    },
}

# ------------------------------------------
# CSV FOR TABLE — which source CSV feeds each raw legacy table
# ------------------------------------------
CSV_FOR_TABLE = {
    "tbl_carr_mstr": "carriers.csv",
    "tbl_load_bkg_raw": "loads.csv",
    "tbl_dock_evt_raw": "dock_events.csv",
    "tbl_carr_invc_raw": "invoices.csv",
}

# Columns (post-rename, ugly legacy names) that must be parsed as real
# dates/timestamps rather than plain strings, or Postgres rejects the insert.
# ------------------------------------------
# DATE COLUMNS — columns that need explicit datetime parsing per table
# ------------------------------------------
DATE_COLUMNS = {
    "tbl_carr_mstr": ["actv_dt"],
    "tbl_load_bkg_raw": ["pu_appt_ts", "del_appt_ts"],
    "tbl_dock_evt_raw": ["evt_ts"],
    "tbl_carr_invc_raw": ["subm_dt"],
}

# Load order matters: carriers and loads first, so foreign keys resolve.
# ------------------------------------------
# LOAD ORDER — table load sequence so foreign keys resolve correctly
# ------------------------------------------
LOAD_ORDER = ["tbl_carr_mstr", "tbl_load_bkg_raw", "tbl_dock_evt_raw", "tbl_carr_invc_raw"]

# ------------------------------------------
# RUN — read each CSV, rename/parse columns, and load it into its legacy table
# ------------------------------------------
if __name__ == "__main__":
    with engine.begin() as conn:
        for table_name in LOAD_ORDER:
            csv_path = DATA_DIR / CSV_FOR_TABLE[table_name]
            df = pd.read_csv(csv_path).rename(columns=TABLE_COLUMN_MAP[table_name])
            for col in DATE_COLUMNS[table_name]:
                df[col] = pd.to_datetime(df[col], format="ISO8601")
            df.to_sql(table_name, conn, schema="dbo", if_exists="append", index=False)
            print(f"Loaded {len(df)} rows into dbo.{table_name}")

    print("Legacy data load complete.")
