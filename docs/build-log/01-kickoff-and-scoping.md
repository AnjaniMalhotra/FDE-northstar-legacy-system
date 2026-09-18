# 01 — Kickoff and Scoping

**Status:** done (documentation steps, no code)

Merges the original build-log 01 (The Brief) and 02 (Scoping Workshop) — the same kickoff
conversation and the scope decision that came directly out of it.

## Part 1: The Brief

**Client:** Northstar Freight, a non-asset freight brokerage (books loads for shippers, tenders
them to a network of trucking carriers, earns the spread between the two rates).

**The pain:** Carrier invoices routinely include padded or incorrect accessorial charges (mainly
detention), and there's no fast way to check a submitted invoice against what actually happened at
the dock. Errors get paid because nobody has time to check every line item by hand.

**The KPI that matters:** **% of carrier spend recovered per month** by catching incorrect charges
before payment — the number every later phase should be able to point back to.

**What "done" looks like for the whole project:** a system that can look at an incoming invoice,
compare it against the agreed contract terms and the real dock timestamps, and tell a human — in
plain language — whether it adds up, and if not, why.

**Key decision:** deliberately scoping the first version around **one specific, well-documented
pain point (detention overbilling)** rather than "all possible invoice errors." Detention is the
highest-value target because it's the single highest-error accessorial category industry-wide, and
because it's checkable against an objective fact (dock arrival/departure timestamps) rather than a
judgment call.

## Part 2: The Scoping Workshop

A short scope document settling two questions before any code got written: what counts as an
"anomaly" worth flagging, and what the system is/isn't allowed to do on its own. Skipping this is
how these projects end up solving the wrong problem — or building an agent that quietly does
something it shouldn't.

**The conflicting stakeholder positions (simulated):**
- **Ops** wants payments to go out fast, so carriers keep taking Northstar's loads.
- **Finance** wants zero leakage — every incorrect charge caught before payment.
- **Compliance** is worried about false accusations damaging carrier relationships, and about
  fraud liability if something slips through.

**What we decided — the actual scope rules:**

An invoice line item counts as an "anomaly" when the billed detention hours don't match the actual
dock dwell time by more than **15 minutes** (allowing for normal timestamp imprecision), **and**
the mismatch changes the billed amount by more than **$25** (small rounding differences aren't
worth flagging).

What the system may do on its own (no human needed): read invoices, loads, and dock event data;
calculate actual detention time and compare it to what was billed; flag a mismatched line item and
show the reasoning.

What always requires a human: disputing a charge with a carrier; holding or releasing a payment;
flagging a carrier as high-risk/repeat offender. This list is the seed of every guardrail rule the
AI copilot project later builds — written here first, in plain language, before any code exists.

**Key decision:** picked **15 minutes / $25** as the flagging threshold rather than flagging every
tiny discrepancy. A system that cries wolf on rounding noise gets ignored; the goal is a small
number of high-confidence flags a human can actually act on, not a wall of alerts.
