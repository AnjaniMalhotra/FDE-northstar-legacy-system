# Northstar Freight — Linehaul Rate Verification Policy
**Version:** 1.0 | **Effective Date:** Jan 2026 | **Owner:** Finance & Compliance

## 1. Purpose
This policy defines when a carrier invoice's linehaul charge counts as a discrepancy worth flagging. The agreed linehaul rate for each load is set at booking time and lives in the TMS — this policy governs how we *check* an invoice against that agreed rate, not what the rate is. Linehaul is not an accessorial charge (see the separate Accessorial Charge Audit & Dispute Policy for detention) — it's the base transportation rate itself, so its verification rule is simpler: there's no time dimension, only a dollar comparison.

## 2. Linehaul Rate Verification
A linehaul charge is considered a **verified discrepancy** when:
- The billed linehaul amount exceeds the rate agreed at booking (in the TMS) by more than **$25**.

As with detention, only overcharges create a dispute flag — a carrier billing *less* than the agreed rate is a data-quality note, never a dispute flag.

## 3. Escalation Tiers and Repeat Pattern Rule
Once a linehaul charge is a verified discrepancy, it follows the exact same Escalation Tiers (Section 3) and Repeat Pattern Rule (Section 4) defined in the Accessorial Charge Audit & Dispute Policy — those rules are already charge-agnostic (they key off the dollar amount and the carrier's overall flag history, not the charge type). A carrier's Tier 2 triggers count linehaul and detention flags together, not separately: a pattern of billing problems is a pattern regardless of which line item it shows up on.

## 4. What the System May and May Not Do Automatically
Identical to Section 5 of the Accessorial Charge Audit & Dispute Policy: the system may read TMS and invoice data, calculate agreed-vs-billed linehaul, and log a Tier 1 flag with its reasoning — never dispute a charge, hold or release payment, or place a carrier on the Elevated Risk list without a human.
