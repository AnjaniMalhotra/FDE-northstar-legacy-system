"""
One generic REST surface over the collections frontend/northstar_web/'s JS
already knows how to talk to (all, find, query, insert, update — see
shared/js/db.js) — GET/POST /api/{collection}, GET/PATCH /api/{collection}/{id}.
Every route requires a valid session (auth.require_session). The
`invoices` collection is the one special case: its `decisions` field is a
normalized child table (invoice_decisions), joined in on read and
replaced wholesale on write, so no page-level JS has to change shape.
"""
# ------------------------------------------
# IMPORTS
# ------------------------------------------
from fastapi import APIRouter, Depends, HTTPException
from sqlalchemy import text
from sqlalchemy.engine import Connection

from backend.northstar_web_api.auth import require_session
from backend.northstar_web_api.db import get_conn, metadata
from backend.northstar_web_api.naming import payload_to_snake, row_to_camel

router = APIRouter(prefix="/api", dependencies=[Depends(require_session)])

# ------------------------------------------
# COLLECTION -> TABLE NAME — the only place this mapping is defined
# ------------------------------------------
COLLECTION_TABLE = {
    "carriers": "carriers",
    "users": "users",
    "shipmentRequests": "shipment_requests",
    "shipments": "shipments",
    "dockEvents": "dock_events",
    "invoices": "invoices",
}


def table_for(collection: str):
    table_name = COLLECTION_TABLE.get(collection)
    if table_name is None:
        raise HTTPException(status_code=404, detail=f"Unknown collection: {collection}")
    return metadata.tables[table_name]


def serialize(row: dict) -> dict:
    row = dict(row)
    row.pop("password_hash", None)  # never leaves the server, for any table
    return row_to_camel(row)


# ------------------------------------------
# DECISIONS — attach each invoice's decision history, in JS's expected
# shape. One query for the whole batch (IN (...) on every invoice id),
# not one query per invoice — the earlier per-row version was a real N+1
# bug invisible at a few dozen invoices and a multi-minute hang at 5,000,
# confirmed by testing against the actual scaled-up dataset, not a guess.
# ------------------------------------------
def attach_decisions(conn: Connection, invoice_rows: list[dict]) -> list[dict]:
    if not invoice_rows:
        return invoice_rows
    ids = [row["id"] for row in invoice_rows]
    all_decisions = conn.execute(
        text("SELECT invoice_id, decided_by, decision, note, at FROM invoice_decisions"
             " WHERE invoice_id = ANY(:ids) ORDER BY at"),
        {"ids": ids},
    ).mappings().all()
    by_invoice: dict[int, list[dict]] = {}
    for d in all_decisions:
        d = dict(d)
        invoice_id = d.pop("invoice_id")
        by_invoice.setdefault(invoice_id, []).append(row_to_camel(d))
    for row in invoice_rows:
        row["decisions"] = by_invoice.get(row["id"], [])
    return invoice_rows


def replace_decisions(conn: Connection, invoice_id: int, decisions: list[dict]) -> None:
    conn.execute(text("DELETE FROM invoice_decisions WHERE invoice_id = :id"), {"id": invoice_id})
    for d in decisions:
        conn.execute(
            text("INSERT INTO invoice_decisions (invoice_id, decided_by, decision, note, at) VALUES (:iid, :decided_by, :decision, :note, :at)"),
            {"iid": invoice_id, "decided_by": d.get("decidedBy"), "decision": d.get("decision"),
             "note": d.get("note"), "at": d.get("at")},
        )


# ------------------------------------------
# DASHBOARD SUMMARY — GET /api/dashboard-summary. Registered before the
# generic /{collection} route below (Starlette matches in registration
# order; after it, "dashboard-summary" would just be swallowed as a
# collection name). Counts and sums computed in SQL, not by downloading
# every row and filtering client-side — the whole reason this exists:
# dashboard.html used to fetch every invoice and every shipment request in
# full just to show 4 numbers, which was fine at a few dozen rows and a
# multi-minute hang at the full demo dataset's scale.
# ------------------------------------------
@router.get("/dashboard-summary")
def dashboard_summary(conn: Connection = Depends(get_conn)):
    bookings_pending = conn.execute(
        text("SELECT count(*) FROM shipment_requests WHERE status = 'PENDING_REVIEW'")
    ).scalar_one()
    invoice_counts = dict(conn.execute(
        text("SELECT status, count(*) FROM invoices GROUP BY status")
    ).all())
    approved_amount = conn.execute(
        text("SELECT coalesce(sum(total_amount), 0) FROM invoices WHERE status = 'APPROVED'")
    ).scalar_one()
    return {
        "bookingsPending": bookings_pending,
        "invoicesPending": invoice_counts.get("PENDING_APPROVAL", 0),
        "invoicesOnHold": invoice_counts.get("ON_HOLD", 0),
        "approvedAmount": float(approved_amount),
    }


# ------------------------------------------
# LIST — GET /api/{collection}
# ------------------------------------------
@router.get("/{collection}")
def list_collection(collection: str, conn: Connection = Depends(get_conn)):
    table = table_for(collection)
    rows = [dict(r) for r in conn.execute(table.select()).mappings().all()]
    if collection == "invoices":
        rows = attach_decisions(conn, rows)
    return [serialize(r) for r in rows]


# ------------------------------------------
# GET ONE — GET /api/{collection}/{id}
# ------------------------------------------
@router.get("/{collection}/{item_id}")
def get_one(collection: str, item_id: int, conn: Connection = Depends(get_conn)):
    table = table_for(collection)
    row = conn.execute(table.select().where(table.c.id == item_id)).mappings().first()
    if row is None:
        raise HTTPException(status_code=404, detail="Not found.")
    row = dict(row)
    if collection == "invoices":
        attach_decisions(conn, [row])
    return serialize(row)


# ------------------------------------------
# INSERT — POST /api/{collection}
# ------------------------------------------
@router.post("/{collection}")
def insert_row(collection: str, payload: dict, conn: Connection = Depends(get_conn)):
    table = table_for(collection)
    decisions = payload.pop("decisions", None)
    values = payload_to_snake(payload)
    values.pop("id", None)
    values.pop("password_hash", None)
    valid_columns = set(table.c.keys())
    values = {k: v for k, v in values.items() if k in valid_columns}

    result = conn.execute(table.insert().values(**values))
    new_id = result.inserted_primary_key[0]

    if collection == "invoices" and decisions:
        replace_decisions(conn, new_id, decisions)

    row = dict(conn.execute(table.select().where(table.c.id == new_id)).mappings().first())
    if collection == "invoices":
        attach_decisions(conn, [row])
    return serialize(row)


# ------------------------------------------
# UPDATE — PATCH /api/{collection}/{id}
# ------------------------------------------
@router.patch("/{collection}/{item_id}")
def update_row(collection: str, item_id: int, payload: dict, conn: Connection = Depends(get_conn)):
    table = table_for(collection)
    decisions = payload.pop("decisions", None)
    values = payload_to_snake(payload)
    values.pop("id", None)
    values.pop("password_hash", None)
    valid_columns = set(table.c.keys())
    values = {k: v for k, v in values.items() if k in valid_columns}

    if values:
        conn.execute(table.update().where(table.c.id == item_id).values(**values))
    if collection == "invoices" and decisions is not None:
        replace_decisions(conn, item_id, decisions)

    row = conn.execute(table.select().where(table.c.id == item_id)).mappings().first()
    if row is None:
        raise HTTPException(status_code=404, detail="Not found.")
    row = dict(row)
    if collection == "invoices":
        attach_decisions(conn, [row])
    return serialize(row)
