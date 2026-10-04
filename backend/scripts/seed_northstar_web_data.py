"""
Seeds the northstar_web database with the same starter dataset previously
built into frontend/northstar_web/shared/js/seed-data.js — same carriers, demo
logins, and the full set of request/shipment/invoice scenarios (pending,
rejected, scheduled, enroute, at-dock, delivered-needs-invoice, clean
approved, on-hold, the full revise-and-resubmit loop, and a missing-dock-
events edge case) — so the site isn't empty on first run.

Passwords are hashed with Postgres's own pgcrypto (crypt/gen_salt), the
same technique scripts/migrate_identity_v4.sql already uses.

Run once, after scripts/northstar_web_schema.sql and
scripts/northstar_web_security.sql: python3 scripts/seed_northstar_web_data.py
Safe to re-run: skipped entirely if carriers already exist.
"""
# ------------------------------------------
# IMPORTS
# ------------------------------------------
import os
from pathlib import Path

from dotenv import load_dotenv
from sqlalchemy import create_engine, text

# ------------------------------------------
# PROJECT PATH AND ENV
# ------------------------------------------
project_root = Path(__file__).resolve().parents[2]
load_dotenv(project_root / ".env")

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
# CARRIER SEED — same 12 carriers, same MC numbers, as the rest of the project
# ------------------------------------------
CARRIER_SEED = [
    {"name": "Redline Transport", "mc_number": "MC-100000", "oos_violations": 1, "insurance_status": "Active"},
    {"name": "Bluewave Freight", "mc_number": "MC-100001", "oos_violations": 0, "insurance_status": "Active"},
    {"name": "Pioneer Haulers", "mc_number": "MC-100002", "oos_violations": 5, "insurance_status": "Active", "elevated_risk": True},
    {"name": "Summit Trucking", "mc_number": "MC-100003", "oos_violations": 1, "insurance_status": "Active"},
    {"name": "Coastal Carriers", "mc_number": "MC-100004", "oos_violations": 0, "insurance_status": "Active"},
    {"name": "Ironhorse Logistics", "mc_number": "MC-100005", "oos_violations": 2, "insurance_status": "Active"},
    {"name": "Prairie Express", "mc_number": "MC-100006", "oos_violations": 6, "insurance_status": "Expired", "elevated_risk": True},
    {"name": "Vantage Freightways", "mc_number": "MC-100007", "oos_violations": 3, "insurance_status": "Active"},
    {"name": "Northbound Transit", "mc_number": "MC-100008", "oos_violations": 0, "insurance_status": "Active"},
    {"name": "Silver Creek Trucking", "mc_number": "MC-100009", "oos_violations": 1, "insurance_status": "Active"},
    {"name": "Apex Line Haul", "mc_number": "MC-100010", "oos_violations": 0, "insurance_status": "Active"},
    {"name": "Cascade Freight Co", "mc_number": "MC-100011", "oos_violations": 1, "insurance_status": "Active"},
]


# ------------------------------------------
# SEED — insert everything inside one transaction
# ------------------------------------------
def seed(conn):
    already = conn.execute(text("SELECT COUNT(*) FROM carriers")).scalar_one()
    if already:
        print(f"northstar_web already has {already} carriers — skipping seed.")
        return

    # ------------------------------------------
    # CARRIERS
    # ------------------------------------------
    carrier_ids = {}
    for idx, c in enumerate(CARRIER_SEED):
        row = conn.execute(
            text(
                "INSERT INTO carriers (name, mc_number, safety_rating, oos_violations, insurance_status,"
                " active_since, detention_free_hours, detention_rate_per_hour, rate_factor, elevated_risk)"
                " VALUES (:name, :mc_number, :safety_rating, :oos_violations, :insurance_status,"
                " '2019-01-01', 2, 65, :rate_factor, :elevated_risk) RETURNING id"
            ),
            {
                **c,
                "safety_rating": "Conditional" if c["oos_violations"] >= 5 else "Satisfactory",
                "rate_factor": 0.9 + ((idx % 5) * 0.05),
                "elevated_risk": c.get("elevated_risk", False),
            },
        )
        carrier_ids[c["name"]] = row.scalar_one()

    def carrier_id(name):
        return carrier_ids[name]

    # ------------------------------------------
    # USERS — demo accounts for all three portals, real hashed passwords
    # ------------------------------------------
    def insert_user(portal, email, password, name, role=None, company_name=None, carrier_id_val=None):
        row = conn.execute(
            text(
                "INSERT INTO users (portal, role, email, password_hash, name, company_name, carrier_id)"
                " VALUES (:portal, :role, :email, crypt(:password, gen_salt('bf')), :name, :company_name, :carrier_id)"
                " RETURNING id"
            ),
            {"portal": portal, "role": role, "email": email, "password": password,
             "name": name, "company_name": company_name, "carrier_id": carrier_id_val},
        )
        return row.scalar_one()

    shipper_a = insert_user("SHIPPER", "shipper@acmemfg.com", "demo123", "Dana Whitfield", company_name="Acme Manufacturing")
    shipper_b = insert_user("SHIPPER", "logistics@brightleaf.com", "demo123", "Marcus Ito", company_name="Brightleaf Foods")

    insert_user("EMPLOYEE", "ops@northstarfreight.com", "demo123", "Jordan Reyes", role="OPERATIONS")
    insert_user("EMPLOYEE", "ap@northstarfreight.com", "demo123", "Priya Nair", role="ACCOUNTS_PAYABLE")
    insert_user("EMPLOYEE", "admin@northstarfreight.com", "demo123", "Sam Okafor", role="ADMIN")

    for name, cid in carrier_ids.items():
        slug = "".join(ch for ch in name.lower() if ch.isalpha())
        insert_user("CARRIER", f"dispatch@{slug}.com", "demo123", name, company_name=name, carrier_id_val=cid)

    # ------------------------------------------
    # HELPERS — build a full request -> shipment -> dock events -> invoice chain
    # ------------------------------------------
    def make_pending_request(shipper_id, origin, dest, weight_lbs, goods, pickup_date, cname, quoted_price):
        conn.execute(
            text(
                "INSERT INTO shipment_requests (shipper_id, origin, dest, weight_lbs, goods_description,"
                " pickup_date, carrier_id, quoted_price, status, employee_note)"
                " VALUES (:shipper_id, :origin, :dest, :weight_lbs, :goods, :pickup_date, :carrier_id, :quoted_price, 'PENDING_REVIEW', '')"
            ),
            {"shipper_id": shipper_id, "origin": origin, "dest": dest, "weight_lbs": weight_lbs,
             "goods": goods, "pickup_date": pickup_date, "carrier_id": carrier_id(cname), "quoted_price": quoted_price},
        )

    def make_approved_shipment(shipper_id, origin, dest, weight_lbs, goods, pickup_date, cname,
                                quoted_price, shipment_status, pickup_appt, delivery_appt):
        cid = carrier_id(cname)
        req_row = conn.execute(
            text(
                "INSERT INTO shipment_requests (shipper_id, origin, dest, weight_lbs, goods_description,"
                " pickup_date, carrier_id, quoted_price, status, employee_note)"
                " VALUES (:shipper_id, :origin, :dest, :weight_lbs, :goods, :pickup_date, :carrier_id, :quoted_price,"
                " 'APPROVED', 'Approved — carrier has capacity on this lane.') RETURNING id"
            ),
            {"shipper_id": shipper_id, "origin": origin, "dest": dest, "weight_lbs": weight_lbs,
             "goods": goods, "pickup_date": pickup_date, "carrier_id": cid, "quoted_price": quoted_price},
        )
        request_id = req_row.scalar_one()
        ship_row = conn.execute(
            text(
                "INSERT INTO shipments (request_id, carrier_id, origin, dest, weight_lbs, goods_description,"
                " agreed_rate, detention_free_hours, detention_rate_per_hour, pickup_appt, delivery_appt, status)"
                " VALUES (:request_id, :carrier_id, :origin, :dest, :weight_lbs, :goods, :agreed_rate, 2, 65,"
                " :pickup_appt, :delivery_appt, :status) RETURNING id"
            ),
            {"request_id": request_id, "carrier_id": cid, "origin": origin, "dest": dest, "weight_lbs": weight_lbs,
             "goods": goods, "agreed_rate": quoted_price, "pickup_appt": pickup_appt,
             "delivery_appt": delivery_appt, "status": shipment_status},
        )
        return ship_row.scalar_one()

    def add_dock_event(shipment_id, event_type, timestamp):
        conn.execute(
            text("INSERT INTO dock_events (shipment_id, type, timestamp) VALUES (:sid, :type, :ts)"),
            {"sid": shipment_id, "type": event_type, "ts": timestamp},
        )

    def add_invoice(shipment_id, cname, linehaul, detn_hours, detn_amt, fuel, total, status, submitted_at, decisions):
        inv_row = conn.execute(
            text(
                "INSERT INTO invoices (shipment_id, carrier_id, linehaul_amount, detention_hours_billed,"
                " detention_amount_billed, fuel_surcharge, total_amount, status, submitted_at)"
                " VALUES (:sid, :cid, :linehaul, :detn_hours, :detn_amt, :fuel, :total, :status, :submitted_at) RETURNING id"
            ),
            {"sid": shipment_id, "cid": carrier_id(cname), "linehaul": linehaul, "detn_hours": detn_hours,
             "detn_amt": detn_amt, "fuel": fuel, "total": total, "status": status, "submitted_at": submitted_at},
        )
        invoice_id = inv_row.scalar_one()
        for d in decisions:
            conn.execute(
                text(
                    "INSERT INTO invoice_decisions (invoice_id, decided_by, decision, note, at)"
                    " VALUES (:iid, :decided_by, :decision, :note, :at)"
                ),
                {"iid": invoice_id, **d},
            )

    # ------------------------------------------
    # PENDING BOOKING REQUESTS
    # ------------------------------------------
    make_pending_request(shipper_a, "Denver, CO", "Phoenix, AZ", 12000, "Industrial hardware, palletized", "2026-09-20", "Pioneer Haulers", 1180.0)
    make_pending_request(shipper_b, "Charlotte, NC", "Memphis, TN", 9800, "Palletized canned goods, 14 pallets", "2026-09-22", "Cascade Freight Co", 950.0)
    make_pending_request(shipper_a, "Phoenix, AZ", "Denver, CO", 16500, "Retail apparel, boxed", "2026-09-25", "Summit Trucking", 1210.0)
    make_pending_request(shipper_b, "Charlotte, NC", "Atlanta, GA", 8000, "Furniture, crated", "2026-09-18", "Apex Line Haul", 610.0)

    # ------------------------------------------
    # REJECTED BOOKING REQUEST
    # ------------------------------------------
    conn.execute(
        text(
            "INSERT INTO shipment_requests (shipper_id, origin, dest, weight_lbs, goods_description, pickup_date,"
            " carrier_id, quoted_price, status, employee_note)"
            " VALUES (:shipper_id, 'Columbus, OH', 'Kansas City, MO', 21000, 'Automotive parts, palletized', '2026-09-10',"
            " :carrier_id, 1340.0, 'REJECTED',"
            " 'Silver Creek Trucking doesn''t have available capacity on this lane for the requested date —"
            " please resubmit with a pickup date after Sept 25, or choose a different carrier.')"
        ),
        {"shipper_id": shipper_a, "carrier_id": carrier_id("Silver Creek Trucking")},
    )

    # ------------------------------------------
    # APPROVED, SCHEDULED
    # ------------------------------------------
    make_approved_shipment(shipper_a, "Chicago, IL", "Columbus, OH", 14000, "Electronics, palletized, 10 pallets", "2026-09-12",
                            "Redline Transport", 830.0, "SCHEDULED", "2026-09-12T08:00", "2026-09-13T10:00")

    # ------------------------------------------
    # APPROVED, ENROUTE
    # ------------------------------------------
    make_approved_shipment(shipper_b, "Atlanta, GA", "Charlotte, NC", 10200, "Packaged food & beverage", "2026-09-05",
                            "Coastal Carriers", 480.0, "ENROUTE", "2026-09-05T07:30", "2026-09-05T14:00")

    # ------------------------------------------
    # APPROVED, AT_DOCK (arrival only)
    # ------------------------------------------
    at_dock = make_approved_shipment(shipper_a, "Memphis, TN", "Columbus, OH", 17500, "Warehouse racking, palletized", "2026-09-06",
                                      "Northbound Transit", 990.0, "AT_DOCK", "2026-09-06T09:00", "2026-09-07T11:00")
    add_dock_event(at_dock, "ARRIVAL", "2026-09-07T11:00")

    # ------------------------------------------
    # APPROVED, DELIVERED — needs an invoice
    # ------------------------------------------
    needs_invoice = make_approved_shipment(shipper_b, "Kansas City, MO", "Dallas, TX", 22000, "Palletized retail merchandise", "2026-09-01",
                                            "Pioneer Haulers", 2100.0, "DELIVERED", "2026-09-01T08:00", "2026-09-02T10:00")
    add_dock_event(needs_invoice, "ARRIVAL", "2026-09-02T10:00")
    add_dock_event(needs_invoice, "DEPARTURE", "2026-09-02T14:15")

    # ------------------------------------------
    # DELIVERED, INVOICE PENDING_APPROVAL — fresh, clean
    # ------------------------------------------
    clean_pending = make_approved_shipment(shipper_a, "Indianapolis, IN", "Charlotte, NC", 13500, "Packaged hardware", "2026-08-25",
                                            "Vantage Freightways", 900.0, "DELIVERED", "2026-08-25T08:00", "2026-08-26T09:30")
    add_dock_event(clean_pending, "ARRIVAL", "2026-08-26T09:30")
    add_dock_event(clean_pending, "DEPARTURE", "2026-08-26T10:45")
    add_invoice(clean_pending, "Vantage Freightways", 900.0, 1.25, 0.0, 108.0, 1008.0, "PENDING_APPROVAL", "2026-08-26T15:00", [])

    # ------------------------------------------
    # DELIVERED, INVOICE APPROVED — clean, resolved
    # ------------------------------------------
    clean_approved = make_approved_shipment(shipper_b, "Chicago, IL", "Indianapolis, IN", 18000, "Packaged consumer goods", "2026-08-14",
                                             "Redline Transport", 1450.0, "DELIVERED", "2026-08-14T09:00", "2026-08-15T11:00")
    add_dock_event(clean_approved, "ARRIVAL", "2026-08-15T11:00")
    add_dock_event(clean_approved, "DEPARTURE", "2026-08-15T12:30")
    add_invoice(clean_approved, "Redline Transport", 1450.0, 1.5, 0.0, 174.0, 1624.0, "APPROVED", "2026-08-15T15:00", [
        {"decided_by": "Priya Nair", "decision": "APPROVED", "note": "Detention hours billed match the dock log — no discrepancy.", "at": "2026-08-16T09:12"},
    ])

    # ------------------------------------------
    # DELIVERED, INVOICE ON_HOLD — overbilled, Elevated Risk carrier
    # ------------------------------------------
    on_hold = make_approved_shipment(shipper_a, "Memphis, TN", "Atlanta, GA", 15500, "Refrigerated produce", "2026-08-20",
                                      "Prairie Express", 1290.0, "DELIVERED", "2026-08-20T07:00", "2026-08-21T09:00")
    add_dock_event(on_hold, "ARRIVAL", "2026-08-21T09:00")
    add_dock_event(on_hold, "DEPARTURE", "2026-08-21T10:05")
    add_invoice(on_hold, "Prairie Express", 1290.0, 4.0, 130.0, 154.8, 1574.8, "ON_HOLD", "2026-08-21T13:30", [
        {"decided_by": "Priya Nair", "decision": "ON_HOLD",
         "note": "Billed 4.0 hrs detention but the dock log shows arrival 09:00 / departure 10:05 — that's 1.08 hrs,"
                 " under the 2-hr free allowance. Please revise the detention charge to $0 and resubmit.",
         "at": "2026-08-22T10:00"},
    ])

    # ------------------------------------------
    # DELIVERED, ON_HOLD -> REVISED -> PENDING_APPROVAL again
    # ------------------------------------------
    revised_pending = make_approved_shipment(shipper_b, "Dallas, TX", "Atlanta, GA", 19000, "Palletized building materials", "2026-08-28",
                                              "Pioneer Haulers", 1680.0, "DELIVERED", "2026-08-28T08:00", "2026-08-29T10:00")
    add_dock_event(revised_pending, "ARRIVAL", "2026-08-29T10:00")
    add_dock_event(revised_pending, "DEPARTURE", "2026-08-29T12:30")
    add_invoice(revised_pending, "Pioneer Haulers", 1680.0, 2.5, 32.5, 201.6, 1914.1, "PENDING_APPROVAL", "2026-08-30T14:20", [
        {"decided_by": "Priya Nair", "decision": "ON_HOLD",
         "note": "Billed 5.0 hrs detention but the dock log shows only 2.5 hrs dwell (arrival 10:00, departure 12:30)."
                 " Please correct the detention hours to match and resubmit.", "at": "2026-08-30T09:00"},
        {"decided_by": "Pioneer Haulers", "decision": "REVISED",
         "note": "Corrected detention hours to match the dock log — apologies, dispatch mis-logged the original wait time.",
         "at": "2026-08-30T14:20"},
    ])

    # ------------------------------------------
    # DELIVERED, full loop: ON_HOLD -> REVISED -> APPROVED
    # ------------------------------------------
    full_loop = make_approved_shipment(shipper_a, "Columbus, OH", "Charlotte, NC", 12800, "Packaged apparel", "2026-08-10",
                                        "Ironhorse Logistics", 760.0, "DELIVERED", "2026-08-10T08:00", "2026-08-11T09:00")
    add_dock_event(full_loop, "ARRIVAL", "2026-08-11T09:00")
    add_dock_event(full_loop, "DEPARTURE", "2026-08-11T10:00")
    add_invoice(full_loop, "Ironhorse Logistics", 760.0, 1.0, 0.0, 91.2, 851.2, "APPROVED", "2026-08-11T14:00", [
        {"decided_by": "Priya Nair", "decision": "ON_HOLD",
         "note": "Billed 3.5 hrs detention but the dock log shows only 1.0 hr dwell (arrival 09:00, departure 10:00)."
                 " Please correct and resubmit.", "at": "2026-08-12T09:30"},
        {"decided_by": "Ironhorse Logistics", "decision": "REVISED",
         "note": "You're right — corrected detention hours to match the dock log.", "at": "2026-08-12T13:00"},
        {"decided_by": "Priya Nair", "decision": "APPROVED",
         "note": "Confirmed — now matches the dock log.", "at": "2026-08-13T10:15"},
    ])

    # ------------------------------------------
    # DELIVERED, PENDING_APPROVAL — no dock events at all (missing-timestamp edge case)
    # ------------------------------------------
    missing_dock = make_approved_shipment(shipper_b, "Denver, CO", "Kansas City, MO", 11000, "Machine parts, crated", "2026-08-30",
                                           "Bluewave Freight", 870.0, "DELIVERED", "2026-08-30T08:00", "2026-08-31T09:00")
    add_invoice(missing_dock, "Bluewave Freight", 870.0, 3.0, 65.0, 104.4, 1039.4, "PENDING_APPROVAL", "2026-08-31T13:00", [])

    print("Seed complete: 12 carriers, 17 users, 15 shipment requests, 10 shipments, 13 dock events, 6 invoices.")


if __name__ == "__main__":
    with engine.begin() as conn:
        seed(conn)
