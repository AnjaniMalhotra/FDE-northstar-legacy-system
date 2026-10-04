# Northstar Freight — Accessorial Charge Audit & Dispute Policy
**Version:** 1.0 | **Effective Date:** Jan 2026 | **Owner:** Finance & Compliance

## 1. Purpose
This policy defines when a carrier invoice's accessorial charges (primarily detention) count as a discrepancy worth flagging, and what level of approval is required before acting on one. Agreed rates, free-time allowances, and per-hour detention rates for each load are set at booking time and live in the TMS — this policy governs how we *check* an invoice against those terms, not what the terms are.

## 2. Detention Charge Verification
A detention charge is considered a **verified discrepancy** when both of the following are true:
- The billed detention time differs from the actual dock dwell time (arrival to departure) by more than **15 minutes**, and
- The resulting difference in billed amount is more than **$25**.

For a carrier **dispute flag**, the difference must be an overcharge (the
billed amount exceeds the actual amount). Undercharges can be reported as a
data-quality issue, but must not create a carrier dispute flag.

Differences smaller than this are within normal timestamp/rounding tolerance and should not be flagged — flagging routine noise trains people to ignore the system.

## 3. Escalation Tiers
This section defines exactly when manager-level approval is required instead of analyst-level handling — the dividing line between what an analyst may resolve alone and what must go to a manager.
- **Tier 1 (Analyst-level):** Any single invoice with a verified discrepancy **under $250** may be logged and flagged for carrier follow-up without manager sign-off. This is a *flag*, not a payment action — see Section 5.
- **Tier 2 (Manager-level):** Required whenever the verified discrepancy on a single invoice is **$250 or more** (see also the Repeat Pattern Rule, Section 4).

## 4. Repeat Pattern Rule
If a carrier has **3 or more flagged invoices within a rolling 90-day window**, that carrier relationship requires a mandatory Tier 2 review — regardless of whether any individual invoice met the dollar threshold in Section 3. A pattern of small discrepancies is itself a signal, even when no single invoice is large.

## 5. What the System May and May Not Do Automatically
- **May do without approval:** read invoice, load, and dock-event data; calculate actual vs. billed detention; log a Tier 1 flag with its reasoning.
- **Always requires human approval, regardless of tier:** disputing a charge with a carrier, or holding or releasing a payment.
