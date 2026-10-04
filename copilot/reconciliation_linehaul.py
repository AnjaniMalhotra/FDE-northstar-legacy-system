"""Database-derived linehaul facts — the agreed rate vs. what the carrier
actually billed. Simpler than reconciliation_detention.py: no time
dimension, just a flat rate comparison."""
# ------------------------------------------
# IMPORTS
# ------------------------------------------
from dataclasses import dataclass
from decimal import Decimal

from sqlalchemy import text
from sqlalchemy.engine import Engine


# ------------------------------------------
# LINEHAUL RECONCILIATION RESULT — billed vs. agreed linehaul rate and its variance
# ------------------------------------------
@dataclass(frozen=True)
class LinehaulReconciliation:
    shipment_id: int
    invoice_id: int
    carrier_id: int
    agreed_rate: Decimal
    billed_amount: Decimal

    @property
    def amount_variance(self) -> Decimal:
        return self.billed_amount - self.agreed_rate


# ------------------------------------------
# GET LINEHAUL RECONCILIATION — pull the agreed rate and billed linehaul for one shipment
# ------------------------------------------
def get_linehaul_reconciliation(engine: Engine, shipment_id: int) -> LinehaulReconciliation | None:
    """Calculate billed-versus-agreed linehaul from northstar_web's own
    tables only. Simpler than detention — no time dimension, just what was
    agreed when the shipment was booked versus what the carrier actually
    billed."""
    query = text("""
        SELECT i.id AS invoice_id, s.carrier_id, s.agreed_rate, i.linehaul_amount
        FROM shipments s
        JOIN invoices i ON i.shipment_id = s.id
        WHERE s.id = :shipment_id
    """)
    with engine.connect() as conn:
        row = conn.execute(query, {"shipment_id": shipment_id}).fetchone()
    if not row:
        return None
    return LinehaulReconciliation(
        shipment_id=shipment_id, invoice_id=row.invoice_id, carrier_id=row.carrier_id,
        agreed_rate=Decimal(str(row.agreed_rate)), billed_amount=Decimal(str(row.linehaul_amount)),
    )


# ------------------------------------------
# FORMAT LINEHAUL RECONCILIATION — render facts as text for the LLM to read
# ------------------------------------------
def format_linehaul_reconciliation(result: LinehaulReconciliation) -> str:
    """Render facts for the LLM; policy decisions happen elsewhere."""
    return (
        f"Shipment {result.shipment_id}:\n"
        f"AGREED linehaul rate: ${result.agreed_rate:.2f}\n"
        f"BILLED linehaul: ${result.billed_amount:.2f}\n"
        f"Difference: ${result.amount_variance:+.2f}"
    )


# ------------------------------------------
# PLAIN LANGUAGE LINEHAUL FACTS — the same reconciliation, spelled out for a non-technical reader
# ------------------------------------------
def plain_language_linehaul_facts(result: LinehaulReconciliation) -> list[dict]:
    return [
        {"label": "Agreed rate", "value": f"${result.agreed_rate:.2f}"},
        {"label": "Billed linehaul", "value": f"${result.billed_amount:.2f}"},
        {
            "label": "Difference",
            "value": (
                f"${result.amount_variance:.2f} too much" if result.amount_variance > 0
                else f"${-result.amount_variance:.2f} too little" if result.amount_variance < 0
                else "None — billed correctly"
            ),
        },
    ]
