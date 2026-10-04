# Northstar Freight — Detention Dispute Workflow (SOP)
**Version:** 1.0 | **Effective Date:** Jan 2026 | **Owner:** Finance & Compliance Operations

## 1. Purpose
This SOP (Standard Operating Procedure) describes the step-by-step process an analyst, and then a manager, follows once the reconciliation system flags a detention-charge discrepancy. It complements the Accessorial Dispute Policy: that document defines *the rule* (what counts as a discrepancy, what tier applies); this document defines *the steps* (what a person actually does about it).

## 2. Reviewing a Flagged Discrepancy (Analyst)
1. Open the flagged invoice and read the system's reconciliation facts (actual vs. billed detention).
2. Confirm the figures make sense — do not approve or dismiss a flag based on its tier label alone.
3. If the discrepancy looks like a data problem rather than a billing problem, follow Section 5 instead of treating it as a carrier dispute.
4. A Tier 1 flag needs no further action — the system has already recorded it automatically.
5. A Tier 2 flag must be escalated to a manager. An analyst never resolves a Tier 2 flag directly.

## 3. When a Flag Becomes Tier 2
A flag is escalated to Tier 2 automatically, the moment it is logged, when any one of the following is true:
- The discrepancy is $250 or more.
- The carrier already has 2 or more **upheld** disputes in the trailing 90 days.
- The carrier is on the **Elevated Risk** list.
- The carrier has 3 or more flags of *any* kind in the trailing 90 days (the repeat-pattern rule).

No one decides this by hand — the system determines the tier from the database every time a flag is logged, independent of who raised it.

## 4. Manager Review — Approving or Rejecting a Pending Flag
1. Review the flagged invoice, the reconciliation facts, and the carrier's full flag history.
2. **Approve** the flag if the discrepancy is confirmed and worth raising with the carrier. Approving does not itself dispute the charge — it records that Northstar intends to.
3. **Reject** the flag if it turns out to be a data issue or a legitimate charge, and note why.
4. After Northstar's dispute conversation with the carrier concludes, record the outcome: **Upheld** if the carrier agreed the charge was wrong, or **Denied** if the carrier gave a legitimate explanation.
5. Only an approved flag can later have a dispute outcome recorded. A rejected or still-pending flag has none.

## 5. Missing or Incomplete Dock Timestamps
If a load's arrival or departure timestamp is missing, the system cannot compute an actual detention time and cannot flag or clear that invoice automatically.
1. Do not assume a charge is legitimate just because it couldn't be automatically checked — a missing timestamp is not evidence the charge is fine.
2. Check with dispatch or the carrier for the missing timestamp before approving payment.
3. If the timestamp truly cannot be recovered, escalate to a manager rather than approving the invoice at face value.

## 6. Handling a Carrier on the Elevated Risk List
1. Every invoice from a carrier on the Elevated Risk list is automatically treated as Tier 2, regardless of the dollar amount.
2. A manager must personally review every such invoice — none can be auto-approved.
3. Removing a carrier from the Elevated Risk list is a manager-level decision, made only after a sustained period without new upheld disputes, and must be recorded with a reason.
