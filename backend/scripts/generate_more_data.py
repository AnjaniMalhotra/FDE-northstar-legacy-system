"""
Scales up northstar_web's dataset — seed_northstar_web_data.py's 12
carriers/2 shippers/6 invoices is enough to demo the golden path, but thin
for exercising the AI at any real volume. Adds carriers/shippers/invoices
on top of that seed (never replacing it) to reach 25 carriers, 100
shippers, and 5,000 invoices total — deterministic (random.seed(7)) from a
fresh database, so re-running against a blank database reproduces the
same dataset.

Run once, after seed_northstar_web_data.py: python3 backend/scripts/generate_more_data.py
Safe to re-run against a database that's already partway there: carriers,
shippers, and invoices are each topped up independently to their own
target, so a database still holding the old ~25/50/100 dataset gets the
remaining shippers and invoices added, not skipped outright.

At thousands of invoices, one row at a time over the network is too slow —
each chain is 5-6 individual INSERTs (request, shipment, 2 dock events,
invoice, sometimes a decision), so 5,000 of them one-by-one is 25,000+
round trips. Everything below is built as plain Python dicts first, then
sent in batched multi-row `INSERT ... VALUES (...), (...), ...` statements
(see bulk_insert) — a few dozen round trips total instead.
"""
# ------------------------------------------
# IMPORTS
# ------------------------------------------
import os
import random
from datetime import datetime, timedelta
from pathlib import Path

from dotenv import load_dotenv
from sqlalchemy import create_engine, text

# ------------------------------------------
# PROJECT PATH, ENV, AND DETERMINISTIC SEED
# ------------------------------------------
project_root = Path(__file__).resolve().parents[2]
load_dotenv(project_root / ".env")
random.seed(7)

db_name = os.getenv("NORTHSTAR_WEB_DB_NAME", "northstar_web")
db_admin_user = os.getenv("DB_ADMIN_USER")
db_admin_password = os.getenv("DB_ADMIN_PASSWORD", "")

# ------------------------------------------
# BUILD DATABASE ENGINE — same two connection shapes as
# backend/northstar_web_api/db.py: a Cloud SQL Unix socket when
# INSTANCE_CONNECTION_NAME is set (Cloud Run), otherwise plain TCP.
# ------------------------------------------
instance_connection_name = os.getenv("INSTANCE_CONNECTION_NAME")
if instance_connection_name:
    socket_path = f"/cloudsql/{instance_connection_name}"
    db_url = f"postgresql+psycopg://{db_admin_user}:{db_admin_password}@/{db_name}?host={socket_path}"
else:
    db_url = (
        f"postgresql+psycopg://{db_admin_user}:{db_admin_password}"
        f"@{os.getenv('DB_HOST', 'localhost')}:{os.getenv('DB_PORT', '5432')}/{db_name}"
    )
engine = create_engine(db_url)

# ------------------------------------------
# TARGETS — total rows after this script runs, seed data included
# ------------------------------------------
TARGET_CARRIERS = 25
TARGET_SHIPPERS = 100
TARGET_INVOICES = 5_000
BATCH_SIZE = 1000  # chains built and inserted per round trip

# ------------------------------------------
# NEW CARRIERS — 13 more, continuing the existing MC-number sequence
# ------------------------------------------
NEW_CARRIERS = [
    "Granite State Freight", "Copper Trail Logistics", "Blue Ridge Carriers", "Timberline Transport",
    "Harborview Freightways", "Steel City Hauling", "Meadowbrook Logistics", "Frontier Line Haul",
    "Golden Plains Trucking", "Riverside Freight Co", "Eastgate Carriers", "Westbound Logistics",
    "Highline Trucking",
]

# ------------------------------------------
# SHIPPER NAME PARTS — enough prefix x suffix combinations (23 x 8 = 184)
# to comfortably cover TARGET_SHIPPERS without repeats; a numeric fallback
# below still guards against ever running out.
# ------------------------------------------
SHIPPER_PREFIXES = [
    "Acme", "Brightleaf", "Cedarwood", "Delta", "Evergreen", "Falcon", "Granite", "Harborline",
    "Ironclad", "Juniper", "Keystone", "Lakeside", "Meridian", "Northgate", "Oakridge", "Pinecrest",
    "Ridgeline", "Summit", "Trailhead", "Union", "Vantage", "Westfield", "Yellowstone",
]
SHIPPER_SUFFIXES = [
    "Manufacturing", "Foods", "Industries", "Supply Co", "Distributors", "Materials",
    "Logistics Group", "Trading Co",
]

# ------------------------------------------
# SHARED LANE/GOODS DATA — same 10 hub cities the rest of the project uses
# ------------------------------------------
HUB_CITIES = [
    "Chicago, IL", "Indianapolis, IN", "Kansas City, MO", "Dallas, TX", "Atlanta, GA",
    "Memphis, TN", "Columbus, OH", "Charlotte, NC", "Denver, CO", "Phoenix, AZ",
]
GOODS = [
    "Palletized retail merchandise", "Boxed electronics", "Crated furniture", "Packaged food & beverage",
    "Industrial hardware, palletized", "Automotive parts, palletized", "Building materials, palletized",
    "Packaged consumer goods", "Machine parts, crated", "Refrigerated produce",
]
FREE_HOURS = 2.0


# ------------------------------------------
# BULK INSERT — a multi-row INSERT ... VALUES (...), (...), ... in batches,
# optionally RETURNING one column (as a list, in insert order). The one
# bulk-write primitive every table below uses instead of per-row inserts.
# ------------------------------------------
def bulk_insert(conn, table: str, columns: list[str], rows: list[dict], returning: str | None = None) -> list:
    ids: list = []
    for start in range(0, len(rows), BATCH_SIZE):
        batch = rows[start:start + BATCH_SIZE]
        value_groups, params = [], {}
        for i, row in enumerate(batch):
            value_groups.append("(" + ", ".join(f":{col}_{i}" for col in columns) + ")")
            params.update({f"{col}_{i}": row[col] for col in columns})
        sql = f"INSERT INTO {table} ({', '.join(columns)}) VALUES {', '.join(value_groups)}"
        if returning:
            result = conn.execute(text(f"{sql} RETURNING {returning}"), params)
            ids.extend(result.scalars().all())
        else:
            conn.execute(text(sql), params)
    return ids


# ------------------------------------------
# INSERT CARRIERS — the 13 new ones, continuing MC-100012...
# ------------------------------------------
def insert_carriers(conn) -> None:
    rows = []
    for idx, name in enumerate(NEW_CARRIERS):
        oos = random.choice([0, 0, 1, 1, 2, 3])
        rows.append({
            "name": name, "mc_number": f"MC-{100012 + idx}",
            "safety_rating": "Conditional" if oos >= 5 else "Satisfactory", "oos_violations": oos,
            "insurance_status": "Active", "active_since": "2020-01-01", "detention_free_hours": 2,
            "detention_rate_per_hour": 65, "rate_factor": 0.9 + ((idx % 5) * 0.05), "elevated_risk": False,
        })
    bulk_insert(conn, "carriers",
                ["name", "mc_number", "safety_rating", "oos_violations", "insurance_status",
                 "active_since", "detention_free_hours", "detention_rate_per_hour", "rate_factor", "elevated_risk"],
                rows)


# ------------------------------------------
# INSERT SHIPPERS — new SHIPPER-portal users, up to TARGET_SHIPPERS total.
# A numeric suffix kicks in only if every prefix x suffix combo (184 of
# them) is already used — guards against ever looping forever.
# ------------------------------------------
def insert_shippers(conn, how_many: int) -> None:
    # password_hash is NOT NULL, and a bulk VALUES list can't call Postgres's
    # crypt()/gen_salt() per row — so hash the shared demo password once and
    # reuse that same hash as a literal across every row. Safe because every
    # demo shipper already logs in with the identical "demo123" password;
    # crypt()'s bcrypt comparison only needs *a* valid hash of it, and the
    # salt is embedded in the hash string itself.
    shared_hash = conn.execute(text("SELECT crypt('demo123', gen_salt('bf'))")).scalar_one()

    existing = set(conn.execute(text("SELECT company_name FROM users WHERE portal = 'SHIPPER'")).scalars().all())
    rows, attempt = [], 0
    while len(rows) < how_many:
        attempt += 1
        company = f"{random.choice(SHIPPER_PREFIXES)} {random.choice(SHIPPER_SUFFIXES)}"
        if attempt > len(SHIPPER_PREFIXES) * len(SHIPPER_SUFFIXES):
            company = f"{company} {attempt}"
        if company in existing:
            continue
        existing.add(company)
        slug = "".join(ch for ch in company.lower() if ch.isalnum())
        rows.append({"portal": "SHIPPER", "email": f"shipping@{slug}.com", "password_hash": shared_hash,
                      "name": f"Contact — {company}", "company_name": company})
    bulk_insert(conn, "users", ["portal", "email", "password_hash", "name", "company_name"], rows)


# ------------------------------------------
# PICK SCENARIO — what actually happened at the dock vs. what the carrier
# billed. Weighted so most invoices are clean, a minority is under-
# threshold noise, and a meaningful minority is a real verified
# discrepancy — so the AI has real material to find, not an empty dataset.
# ------------------------------------------
def pick_scenario(agreed_rate: float) -> dict:
    roll = random.random()
    if roll < 0.70:  # clean — billed matches actual, within rounding
        actual_overage_hrs = round(random.uniform(0, 1.5), 2)
        return {"actual_overage_hrs": actual_overage_hrs, "billed_detention_hrs": actual_overage_hrs,
                "billed_linehaul": agreed_rate, "has_real_discrepancy": False}
    if roll < 0.85:  # under-threshold noise — never flagged
        actual_overage_hrs = round(random.uniform(0, 1.5), 2)
        return {"actual_overage_hrs": actual_overage_hrs,
                "billed_detention_hrs": round(actual_overage_hrs + random.uniform(0.05, 0.2), 2),
                "billed_linehaul": round(agreed_rate + random.uniform(1, 20), 2), "has_real_discrepancy": False}
    if roll < 0.93:  # real detention overcharge
        actual_overage_hrs = round(random.uniform(0, 1.0), 2)
        return {"actual_overage_hrs": actual_overage_hrs,
                "billed_detention_hrs": round(actual_overage_hrs + random.uniform(1.0, 3.0), 2),
                "billed_linehaul": agreed_rate, "has_real_discrepancy": True}
    # real linehaul overcharge
    actual_overage_hrs = round(random.uniform(0, 1.5), 2)
    return {"actual_overage_hrs": actual_overage_hrs, "billed_detention_hrs": actual_overage_hrs,
            "billed_linehaul": round(agreed_rate + random.uniform(40, 300), 2), "has_real_discrepancy": True}


# ------------------------------------------
# BUILD ONE CHAIN'S DATA — pure Python, no SQL. Everything a shipment
# needs, computed up front so a whole batch can be built before any
# INSERT runs. Spread across ~2 years so 50,000 rows don't all land on
# the same few weeks.
# ------------------------------------------
def build_chain(shipper_id: int, carrier_id: int, base_date: datetime) -> dict:
    origin, dest = random.sample(HUB_CITIES, 2)
    agreed_rate = round(random.uniform(500, 2200), 2)
    pickup = base_date + timedelta(days=random.randint(0, 730), hours=random.randint(6, 10))
    delivery = pickup + timedelta(hours=random.randint(20, 30))
    scenario = pick_scenario(agreed_rate)
    arrival = delivery + timedelta(minutes=random.randint(-30, 30))
    departure = arrival + timedelta(hours=FREE_HOURS + scenario["actual_overage_hrs"])

    detention_amount = round(scenario["billed_detention_hrs"] * 65, 2)
    fuel_surcharge = round(scenario["billed_linehaul"] * 0.12, 2)
    total = round(scenario["billed_linehaul"] + detention_amount + fuel_surcharge, 2)
    submitted_at = departure + timedelta(hours=random.randint(2, 10))

    status_roll = random.random()
    if scenario["has_real_discrepancy"]:
        status = "ON_HOLD" if status_roll < 0.5 else "PENDING_APPROVAL"
    else:
        status = "APPROVED" if status_roll < 0.6 else "PENDING_APPROVAL"

    return {
        "shipper_id": shipper_id, "carrier_id": carrier_id, "origin": origin, "dest": dest,
        "weight_lbs": random.randint(8000, 22000), "goods_description": random.choice(GOODS),
        "agreed_rate": agreed_rate, "pickup": pickup, "delivery": delivery, "arrival": arrival,
        "departure": departure, "billed_linehaul": scenario["billed_linehaul"],
        "billed_detention_hrs": scenario["billed_detention_hrs"], "detention_amount": detention_amount,
        "fuel_surcharge": fuel_surcharge, "total": total, "status": status, "submitted_at": submitted_at,
    }


# ------------------------------------------
# INSERT ONE BATCH OF CHAINS — request -> shipment -> dock events -> invoice
# -> decision, each stage bulk-inserted, feeding the previous stage's
# RETURNING ids into the next.
# ------------------------------------------
def insert_chain_batch(conn, chains: list[dict]) -> None:
    request_ids = bulk_insert(
        conn, "shipment_requests",
        ["shipper_id", "origin", "dest", "weight_lbs", "goods_description", "pickup_date",
         "carrier_id", "quoted_price", "status", "employee_note"],
        [{"shipper_id": c["shipper_id"], "origin": c["origin"], "dest": c["dest"], "weight_lbs": c["weight_lbs"],
          "goods_description": c["goods_description"], "pickup_date": c["pickup"].date(),
          "carrier_id": c["carrier_id"], "quoted_price": c["agreed_rate"], "status": "APPROVED",
          "employee_note": "Approved — carrier has capacity on this lane."} for c in chains],
        returning="id",
    )
    shipment_ids = bulk_insert(
        conn, "shipments",
        ["request_id", "carrier_id", "origin", "dest", "weight_lbs", "goods_description", "agreed_rate",
         "detention_free_hours", "detention_rate_per_hour", "pickup_appt", "delivery_appt", "status"],
        [{"request_id": rid, "carrier_id": c["carrier_id"], "origin": c["origin"], "dest": c["dest"],
          "weight_lbs": c["weight_lbs"], "goods_description": c["goods_description"], "agreed_rate": c["agreed_rate"],
          "detention_free_hours": 2, "detention_rate_per_hour": 65, "pickup_appt": c["pickup"],
          "delivery_appt": c["delivery"], "status": "DELIVERED"} for rid, c in zip(request_ids, chains)],
        returning="id",
    )

    dock_rows = []
    for sid, c in zip(shipment_ids, chains):
        dock_rows.append({"shipment_id": sid, "type": "ARRIVAL", "timestamp": c["arrival"]})
        dock_rows.append({"shipment_id": sid, "type": "DEPARTURE", "timestamp": c["departure"]})
    bulk_insert(conn, "dock_events", ["shipment_id", "type", "timestamp"], dock_rows)

    invoice_ids = bulk_insert(
        conn, "invoices",
        ["shipment_id", "carrier_id", "linehaul_amount", "detention_hours_billed",
         "detention_amount_billed", "fuel_surcharge", "total_amount", "status", "submitted_at"],
        [{"shipment_id": sid, "carrier_id": c["carrier_id"], "linehaul_amount": c["billed_linehaul"],
          "detention_hours_billed": c["billed_detention_hrs"], "detention_amount_billed": c["detention_amount"],
          "fuel_surcharge": c["fuel_surcharge"], "total_amount": c["total"], "status": c["status"],
          "submitted_at": c["submitted_at"]} for sid, c in zip(shipment_ids, chains)],
        returning="id",
    )

    decision_rows = []
    for iid, c in zip(invoice_ids, chains):
        if c["status"] not in ("APPROVED", "ON_HOLD"):
            continue
        note = "Confirmed — matches agreed terms and the dock log." if c["status"] == "APPROVED" \
            else "Billed detention/linehaul doesn't match the real dock log or agreed rate — please revise and resubmit."
        decision_rows.append({"invoice_id": iid, "decided_by": "Priya Nair", "decision": c["status"],
                               "note": note, "at": c["submitted_at"] + timedelta(hours=random.randint(4, 24))})
    bulk_insert(conn, "invoice_decisions", ["invoice_id", "decided_by", "decision", "note", "at"], decision_rows)


# ------------------------------------------
# SEED — top up carriers, shippers, and invoices independently, each to
# its own target, so a re-run against a partially-scaled database only
# adds what's still missing.
# ------------------------------------------
def seed_more(conn):
    carrier_count = conn.execute(text("SELECT COUNT(*) FROM carriers")).scalar_one()
    if carrier_count < TARGET_CARRIERS:
        insert_carriers(conn)
        print(f"carriers: {carrier_count} -> {TARGET_CARRIERS}")
    else:
        print(f"carriers already at {carrier_count} (target {TARGET_CARRIERS}) — skipping.")

    shipper_count = conn.execute(text("SELECT COUNT(*) FROM users WHERE portal = 'SHIPPER'")).scalar_one()
    if shipper_count < TARGET_SHIPPERS:
        insert_shippers(conn, TARGET_SHIPPERS - shipper_count)
        print(f"shippers: {shipper_count} -> {TARGET_SHIPPERS}")
    else:
        print(f"shippers already at {shipper_count} (target {TARGET_SHIPPERS}) — skipping.")

    invoice_count = conn.execute(text("SELECT COUNT(*) FROM invoices")).scalar_one()
    if invoice_count >= TARGET_INVOICES:
        print(f"invoices already at {invoice_count} (target {TARGET_INVOICES}) — skipping.")
        return

    all_carrier_ids = conn.execute(text("SELECT id FROM carriers ORDER BY id")).scalars().all()
    all_shipper_ids = conn.execute(text("SELECT id FROM users WHERE portal = 'SHIPPER' ORDER BY id")).scalars().all()
    base_date = datetime(2024, 10, 1)
    to_add = TARGET_INVOICES - invoice_count
    added = 0
    while added < to_add:
        batch_n = min(BATCH_SIZE, to_add - added)
        chains = [build_chain(random.choice(all_shipper_ids), random.choice(all_carrier_ids), base_date)
                  for _ in range(batch_n)]
        insert_chain_batch(conn, chains)
        added += batch_n
        print(f"invoices: +{added}/{to_add}", end="\r")
    print(f"\ninvoices: {invoice_count} -> {invoice_count + added}")


if __name__ == "__main__":
    with engine.begin() as conn:
        seed_more(conn)
