"""
Authors data/policy/carrier_risk_memo.pdf — a short internal memo on carrier
risk indicators. This exists as a PDF (not markdown) on purpose: it simulates
a document type that actually shows up in a real company (a distributed memo
attachment), giving the RAG ingestion pipeline a second file format to parse,
alongside the markdown policy doc.

This is a one-time authoring script, not part of the regular data pipeline —
run it again only if the memo's wording needs to change.
"""
# ------------------------------------------
# IMPORTS — PDF generation library and path handling
# ------------------------------------------
from pathlib import Path
from fpdf import FPDF

# ------------------------------------------
# OUTPUT PATH — where the generated memo PDF is written
# ------------------------------------------
OUT_PATH = Path(__file__).resolve().parents[2] / "data" / "policy" / "carrier_risk_memo.pdf"

# ------------------------------------------
# TITLE AND SUBTITLE — the memo's header text
# ------------------------------------------
TITLE = "Internal Memo -- Carrier Risk Indicators"
SUBTITLE = "Confidential -- Operations & Compliance | v1.0 | Jan 2026"

# ------------------------------------------
# BODY — the memo's full text content, split into paragraphs when written
# ------------------------------------------
BODY = """Purpose

This memo helps Operations and Compliance distinguish an honest billing mistake from a
pattern worth escalating. It complements the Accessorial Charge Audit & Dispute Policy --
that policy defines the dollar/time thresholds for a single invoice; this memo defines
when a carrier's behavior across multiple invoices should be treated as a risk signal.

Indicators of Elevated Carrier Risk

1. Repeated detention overbilling above the policy tolerance within a rolling 90-day
   window (see the Repeat Pattern Rule in the Dispute Policy).

2. A load tendered to one carrier, then re-confirmed for pickup under a different MC
   number shortly before the scheduled pickup time -- a classic double-brokering signal.

3. Invoice remittance (bank/payment) details changing between submissions without any
   prior notice from the carrier.

4. A carrier's safety rating dropping to "Conditional" at the same time as any open
   billing dispute.

Recommended Action

A carrier meeting two or more of the above indicators should be placed on the Elevated
Risk list. Per the Dispute Policy, any carrier on the Elevated Risk list requires Tier 2
(manager-level) review for all future invoices, not only the ones that are individually
flagged. Placing a carrier on this list always requires human approval -- it is never an
automatic action.
"""


# ------------------------------------------
# BUILD PDF — lay out title, subtitle, and body paragraphs, then write the file
# ------------------------------------------
def build_pdf() -> None:
    pdf = FPDF()
    pdf.add_page()

    def write_block(text: str, size: int, style: str, line_h: int, gap_after: int):
        pdf.set_x(pdf.l_margin)  # fpdf2's cursor doesn't always reset itself between blocks
        pdf.set_font("Helvetica", style, size)
        pdf.multi_cell(pdf.epw, line_h, text)
        pdf.ln(gap_after)

    write_block(TITLE, 16, "B", 10, 2)
    write_block(SUBTITLE, 10, "I", 8, 4)
    for paragraph in BODY.strip().split("\n\n"):
        write_block(paragraph.strip(), 11, "", 6, 4)
    pdf.output(str(OUT_PATH))
    print(f"Wrote {OUT_PATH}")


# ------------------------------------------
# RUN — generate the memo PDF when run directly
# ------------------------------------------
if __name__ == "__main__":
    build_pdf()
