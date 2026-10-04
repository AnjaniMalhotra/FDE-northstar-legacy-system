"""
Scales up northstar_web's dataset — seed_northstar_web_data.py's 12
carriers/2 shippers/6 invoices is enough to demo the golden path, but thin
for exercising the AI at any real volume. Adds carriers/shippers/invoices on
top of that seed (never replacing it) to reach roughly 25 carriers, 50
shippers, 100 invoices total — deterministic (random.seed(7)) so re-running
against a fresh database reproduces the same dataset.

Run once, after seed_northstar_web_data.py: python3 backend/scripts/generate_more_data.py
Safe to re-run: skipped entirely if carriers already number 25 or more.
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
db_url = (
    f"postgresql+psycopg://{os.getenv('DB_ADMIN_USER')}:{os.getenv('DB_ADMIN_PASSWORD', '')}"
    f"@{os.getenv('DB_HOST', 'localhost')}:{os.getenv('DB_PORT', '5432')}/{db_name}"
)
engine = create_engine(db_url)

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
# NEW SHIPPERS — 48 more, built from name-part combinations for variety
# without hand-typing 48 unique company names
# ------------------------------------------
SHIPPER_PREFIXES = [
    "Acme", "Brightleaf", "Cedarwood", "Delta", "Evergreen", "Falcon", "Granite", "Harborline",
    "Ironclad", "Juniper", "Keystone", "Lakeside", "Meridian", "Northgate", "Oakridge", "Pinecrest",
]
SHIPPER_SUFFIXES = [
    "Manufacturing", "Foods", "Industries", "Supply Co", "Distributors", "Materials",
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
SHIPMENTS_TO_ADD = 93
FREE_HOURS = 2.0


# ------------------------------------------
# INSERT CARRIERS — the 13 new ones, continuing MC-100012...
# ------------------------------------------
def insert_carriers(conn) -> list[int]:
    for idx, name in enumerate(NEW_CARRIERS):
        mc = f"MC-{100012 + idx}"
        oos = random.choice([0, 0, 1, 1, 2, 3])
        conn.execute(
            text(
                "INSERT INTO carriers (name, mc_number, safety_rating, oos_violations, insurance_status,"
                " active_since, detention_free_hours, detention_rate_per_hour, rate_factor, elevated_risk)"
                " VALUES (:name, :mc, :rating, :oos, 'Active', '2020-01-01', 2, 65, :rate_factor, FALSE)"
            ),
            {"name": name, "mc": mc, "rating": "Conditional" if oos >= 5 else "Satisfactory",
             "oos": oos, "rate_factor": 0.9 + ((idx % 5) * 0.05)},
        )
    return conn.execute(text("SELECT id FROM carriers ORDER BY id")).scalars().all()


# ------------------------------------------
# INSERT SHIPPERS — 48 new SHIPPER-portal users, deduplicated company names
# ------------------------------------------
def insert_shippers(conn) -> list[int]:
    shipper_ids = []
    used_names = set()
    while len(shipper_ids) < 48:
        company = f"{random.choice(SHIPPER_PREFIXES)} {random.choice(SHIPPER_SUFFIXES)}"
        if company in used_names:
            continue
        used_names.add(company)
        slug = "".join(ch for ch in company.lower() if ch.isalnum())
        row = conn.execute(
            text(
                "INSERT INTO users (portal, email, password_hash, name, company_name)"
                " VALUES ('SHIPPER', :email, crypt('demo123', gen_salt('bf')), :name, :company) RETURNING id"
            ),
            {"email": f"shipping@{slug}.com", "name": f"Contact — {company}", "company": company},
        )
        shipper_ids.append(row.scalar_one())
    return shipper_ids


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
# INSERT ONE SHIPMENT CHAIN — request -> shipment -> dock events -> invoice
# (-> decision, if resolved). Mirrors seed_northstar_web_data.py's own
# make_approved_shipment/add_dock_event/add_invoice helpers, collapsed into
# one function since every generated shipment follows the same shape.
# ------------------------------------------
def insert_shipment_chain(conn, shipper_id: int, carrier_id: int, base_date: datetime) -> None:
    origin, dest = random.sample(HUB_CITIES, 2)
    weight = random.randint(8000, 22000)
    goods = random.choice(GOODS)
    agreed_rate = round(random.uniform(500, 2200), 2)
    pickup = base_date + timedelta(days=random.randint(0, 75), hours=random.randint(6, 10))
    delivery = pickup + timedelta(hours=random.randint(20, 30))

    req_row = conn.execute(
        text(
            "INSERT INTO shipment_requests (shipper_id, origin, dest, weight_lbs, goods_description,"
            " pickup_date, carrier_id, quoted_price, status, employee_note)"
            " VALUES (:shipper_id, :origin, :dest, :weight, :goods, :pickup_date, :carrier_id, :rate,"
            " 'APPROVED', 'Approved — carrier has capacity on this lane.') RETURNING id"
        ),
        {"shipper_id": shipper_id, "origin": origin, "dest": dest, "weight": weight, "goods": goods,
         "pickup_date": pickup.date(), "carrier_id": carrier_id, "rate": agreed_rate},
    )
    ship_row = conn.execute(
        text(
            "INSERT INTO shipments (request_id, carrier_id, origin, dest, weight_lbs, goods_description,"
            " agreed_rate, detention_free_hours, detention_rate_per_hour, pickup_appt, delivery_appt, status)"
            " VALUES (:request_id, :carrier_id, :origin, :dest, :weight, :goods, :rate, 2, 65,"
            " :pickup, :delivery, 'DELIVERED') RETURNING id"
        ),
        {"request_id": req_row.scalar_one(), "carrier_id": carrier_id, "origin": origin, "dest": dest,
         "weight": weight, "goods": goods, "rate": agreed_rate, "pickup": pickup, "delivery": delivery},
    )
    shipment_id = ship_row.scalar_one()

    scenario = pick_scenario(agreed_rate)
    arrival = delivery + timedelta(minutes=random.randint(-30, 30))
    departure = arrival + timedelta(hours=FREE_HOURS + scenario["actual_overage_hrs"])
    conn.execute(text("INSERT INTO dock_events (shipment_id, type, timestamp) VALUES (:sid, 'ARRIVAL', :ts)"),
                 {"sid": shipment_id, "ts": arrival})
    conn.execute(text("INSERT INTO dock_events (shipment_id, type, timestamp) VALUES (:sid, 'DEPARTURE', :ts)"),
                 {"sid": shipment_id, "ts": departure})

    detention_amount = round(scenario["billed_detention_hrs"] * 65, 2)
    fuel_surcharge = round(scenario["billed_linehaul"] * 0.12, 2)
    total = round(scenario["billed_linehaul"] + detention_amount + fuel_surcharge, 2)
    submitted_at = departure + timedelta(hours=random.randint(2, 10))

    status_roll = random.random()
    if scenario["has_real_discrepancy"]:
        status = "ON_HOLD" if status_roll < 0.5 else "PENDING_APPROVAL"
    else:
        status = "APPROVED" if status_roll < 0.6 else "PENDING_APPROVAL"

    inv_row = conn.execute(
        text(
            "INSERT INTO invoices (shipment_id, carrier_id, linehaul_amount, detention_hours_billed,"
            " detention_amount_billed, fuel_surcharge, total_amount, status, submitted_at)"
            " VALUES (:sid, :cid, :linehaul, :detn_hours, :detn_amt, :fuel, :total, :status, :submitted_at)"
            " RETURNING id"
        ),
        {"sid": shipment_id, "cid": carrier_id, "linehaul": scenario["billed_linehaul"],
         "detn_hours": scenario["billed_detention_hrs"], "detn_amt": detention_amount, "fuel": fuel_surcharge,
         "total": total, "status": status, "submitted_at": submitted_at},
    )
    if status in ("APPROVED", "ON_HOLD"):
        note = "Confirmed — matches agreed terms and the dock log." if status == "APPROVED" \
            else "Billed detention/linehaul doesn't match the real dock log or agreed rate — please revise and resubmit."
        conn.execute(
            text(
                "INSERT INTO invoice_decisions (invoice_id, decided_by, decision, note, at)"
                " VALUES (:iid, 'Priya Nair', :decision, :note, :at)"
            ),
            {"iid": inv_row.scalar_one(), "decision": status, "note": note,
             "at": submitted_at + timedelta(hours=random.randint(4, 24))},
        )


# ------------------------------------------
# SEED — insert everything, skipped entirely if this has already run
# ------------------------------------------
def seed_more(conn):
    carrier_count = conn.execute(text("SELECT COUNT(*) FROM carriers")).scalar_one()
    if carrier_count >= 25:
        print(f"northstar_web already has {carrier_count} carriers — skipping generate_more_data.")
        return

    all_carrier_ids = insert_carriers(conn)
    shipper_ids = insert_shippers(conn)

    base_date = datetime(2026, 7, 1)
    for _ in range(SHIPMENTS_TO_ADD):
        insert_shipment_chain(conn, random.choice(shipper_ids), random.choice(all_carrier_ids), base_date)

    print(f"generate_more_data complete: +{len(NEW_CARRIERS)} carriers ({len(all_carrier_ids)} total),"
          f" +{len(shipper_ids)} shippers ({len(shipper_ids) + 2} total), +{SHIPMENTS_TO_ADD} invoices.")


if __name__ == "__main__":
    with engine.begin() as conn:
        seed_more(conn)
