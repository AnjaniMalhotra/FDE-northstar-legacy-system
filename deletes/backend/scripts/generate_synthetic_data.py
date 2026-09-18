"""
Generates clean, realistic synthetic data for Northstar Freight: carriers, loads,
dock check-in/out events, and carrier invoices. Some invoices are deliberately
seeded with overbilled detention charges, so there's something real for the
reconciliation agent (built in Phase 3) to catch.

Output: clean CSVs in data/synthetic/. These get intentionally "uglified" into
a fake legacy schema by load_legacy_data.py — this script only produces the
clean version.
"""
# ------------------------------------------
# IMPORTS — standard library only
# ------------------------------------------
import csv
import random
from datetime import datetime, timedelta
from pathlib import Path

# ------------------------------------------
# RANDOM SEED — fixed so the generated data is identical on every run
# ------------------------------------------
random.seed(7)  # reproducible output — same data every run

# ------------------------------------------
# OUTPUT DIRECTORY — where the generated CSVs are written
# ------------------------------------------
OUT_DIR = Path(__file__).resolve().parents[2] / "data" / "synthetic"
OUT_DIR.mkdir(parents=True, exist_ok=True)

# ------------------------------------------
# CARRIER AND CITY POOLS — names and cities used to build synthetic carriers/loads
# ------------------------------------------
CARRIER_NAMES = [
    "Redline Transport", "Bluewave Freight", "Pioneer Haulers", "Summit Trucking",
    "Coastal Carriers", "Ironhorse Logistics", "Prairie Express", "Vantage Freightways",
    "Northbound Transit", "Silver Creek Trucking", "Apex Line Haul", "Cascade Freight Co",
]
CITIES = [
    "Chicago, IL", "Dallas, TX", "Atlanta, GA", "Columbus, OH", "Memphis, TN",
    "Denver, CO", "Phoenix, AZ", "Charlotte, NC", "Kansas City, MO", "Indianapolis, IN",
]

# ------------------------------------------
# DATA VOLUME CONFIG — counts and overbill rate controlling the generated dataset
# ------------------------------------------
NUM_CARRIERS = len(CARRIER_NAMES)
NUM_LOADS = 150
OVERBILL_RATE = 0.20  # ~20% of invoices get a padded detention charge

# Two carriers are repeat offenders — most of the overbilled invoices point back
# to them. This sets up the "which carriers keep doing this?" question for later.
# ------------------------------------------
# REPEAT OFFENDER IDS — carriers seeded to overbill far more often than the rest
# ------------------------------------------
REPEAT_OFFENDER_IDS = [3, 7]

# Real detention-free terms vary by carrier contract, not by load — some
# carriers negotiate a stricter 1 hour before the clock starts, others get
# 3+. A flat number for every carrier was hiding this entirely.
# ------------------------------------------
# CARRIER FREE HOURS — per-carrier detention-free contract term (hours)
# ------------------------------------------
CARRIER_FREE_HOURS = {1: 1, 2: 2, 3: 2, 4: 1, 5: 3, 6: 2, 7: 2, 8: 1, 9: 3, 10: 2, 11: 1, 12: 3}

# A carrier billing something other than the rate they agreed to at booking
# is a second, separate way an invoice can be wrong — independent of
# detention. Same repeat-offender carriers, same "most invoices are clean"
# shape, its own overbill rate so the two don't always line up on the same
# invoices.
# ------------------------------------------
# LINEHAUL OVERBILL RATE — how often billed linehaul differs from the agreed rate
# ------------------------------------------
LINEHAUL_OVERBILL_RATE = 0.15


# ------------------------------------------
# WRITE CSV — dump a list of row dicts to a CSV file using the first row's keys as headers
# ------------------------------------------
def write_csv(path: Path, rows: list[dict]):
    with open(path, "w", newline="") as f:
        writer = csv.DictWriter(f, fieldnames=rows[0].keys())
        writer.writeheader()
        writer.writerows(rows)


# ------------------------------------------
# GENERATE CARRIERS — build the synthetic carrier roster
# ------------------------------------------
def generate_carriers() -> list[dict]:
    return [
        {
            "carrier_id": i + 1,
            "carrier_name": name,
            "mc_number": f"MC-{100000 + i}",
            "safety_rating": random.choice(["Satisfactory", "Satisfactory", "Satisfactory", "Conditional"]),
            "active_since": (datetime(2018, 1, 1) + timedelta(days=random.randint(0, 2000))).date().isoformat(),
        }
        for i, name in enumerate(CARRIER_NAMES)
    ]


# ------------------------------------------
# GENERATE LOADS — build synthetic loads with random carrier, cities, and appointment times
# ------------------------------------------
def generate_loads() -> list[dict]:
    loads = []
    start = datetime(2026, 1, 1, 6, 0)
    for i in range(NUM_LOADS):
        carrier_id = random.randint(1, NUM_CARRIERS)
        origin, dest = random.sample(CITIES, 2)
        pickup = start + timedelta(hours=random.randint(0, 24 * 150))
        transit_hours = random.randint(8, 30)
        delivery = pickup + timedelta(hours=transit_hours)
        loads.append({
            "load_id": i + 1,
            "carrier_id": carrier_id,
            "origin_city": origin,
            "dest_city": dest,
            "pickup_appt": pickup.isoformat(sep=" "),
            "delivery_appt": delivery.isoformat(sep=" "),
            "agreed_rate": round(random.uniform(800, 3200), 2),
            "detention_free_hours": CARRIER_FREE_HOURS[carrier_id],  # varies by carrier contract
            "detention_rate_per_hour": 65.00,   # standard contract term: $65/hr after that
        })
    return loads


# ------------------------------------------
# GENERATE DOCK EVENTS — simulate arrival/departure timestamps and the real detention hours
# ------------------------------------------
def generate_dock_events(loads: list[dict]) -> tuple[list[dict], dict[int, float]]:
    """Returns dock events, and a lookup of load_id -> actual detention hours."""
    events = []
    actual_detention_by_load = {}
    event_id = 1

    for load in loads:
        delivery_appt = datetime.fromisoformat(load["delivery_appt"])
        arrival = delivery_appt + timedelta(minutes=random.randint(-10, 20))

        # Most loads have a short, normal dwell time; a handful run genuinely long.
        if random.random() < 0.15:
            dwell_hours = random.uniform(2.5, 5.0)   # a real, long wait
        else:
            dwell_hours = random.uniform(0.5, 2.0)   # within or near the free period

        departure = arrival + timedelta(hours=dwell_hours)
        actual_detention_hours = max(0.0, dwell_hours - load["detention_free_hours"])
        actual_detention_by_load[load["load_id"]] = round(actual_detention_hours, 2)

        events.append({"event_id": event_id, "load_id": load["load_id"], "event_type": "ARRIVAL", "event_ts": arrival.isoformat(sep=" ")})
        event_id += 1
        events.append({"event_id": event_id, "load_id": load["load_id"], "event_type": "DEPARTURE", "event_ts": departure.isoformat(sep=" ")})
        event_id += 1

    return events, actual_detention_by_load


# ------------------------------------------
# GENERATE INVOICES — build carrier invoices, seeding overbilled detention
# and, independently, overbilled linehaul for some
# ------------------------------------------
def generate_invoices(loads: list[dict], actual_detention_by_load: dict[int, float]) -> list[dict]:
    invoices = []
    for i, load in enumerate(loads):
        actual_hours = actual_detention_by_load[load["load_id"]]
        rate = load["detention_rate_per_hour"]

        is_repeat_offender = load["carrier_id"] in REPEAT_OFFENDER_IDS
        should_overbill = random.random() < (OVERBILL_RATE * 2.5 if is_repeat_offender else OVERBILL_RATE * 0.5)

        if should_overbill:
            billed_hours = round(actual_hours + random.uniform(1.0, 3.0), 2)
        else:
            billed_hours = actual_hours

        detention_amount = round(billed_hours * rate, 2)
        submitted = datetime.fromisoformat(load["delivery_appt"]) + timedelta(days=random.randint(1, 5))

        should_overbill_linehaul = random.random() < (LINEHAUL_OVERBILL_RATE * 2 if is_repeat_offender else LINEHAUL_OVERBILL_RATE * 0.6)
        linehaul_amount = round(load["agreed_rate"] + random.uniform(50, 400), 2) if should_overbill_linehaul else load["agreed_rate"]

        fuel_surcharge = round(load["agreed_rate"] * 0.12, 2)
        invoices.append({
            "invoice_id": i + 1,
            "load_id": load["load_id"],
            "carrier_id": load["carrier_id"],
            "submitted_date": submitted.date().isoformat(),
            "linehaul_amount": linehaul_amount,
            "detention_hours_billed": billed_hours,
            "detention_amount_billed": detention_amount,
            "fuel_surcharge_amount": fuel_surcharge,
            "total_amount": round(linehaul_amount + detention_amount + fuel_surcharge, 2),
        })
    return invoices


# ------------------------------------------
# RUN AND WRITE OUTPUT — generate all datasets and write each to its own CSV
# ------------------------------------------
if __name__ == "__main__":
    carriers = generate_carriers()
    loads = generate_loads()
    dock_events, actual_detention_by_load = generate_dock_events(loads)
    invoices = generate_invoices(loads, actual_detention_by_load)

    write_csv(OUT_DIR / "carriers.csv", carriers)
    write_csv(OUT_DIR / "loads.csv", loads)
    write_csv(OUT_DIR / "dock_events.csv", dock_events)
    write_csv(OUT_DIR / "invoices.csv", invoices)

    print(f"Generated {len(carriers)} carriers, {len(loads)} loads, "
          f"{len(dock_events)} dock events, {len(invoices)} invoices -> {OUT_DIR}")
