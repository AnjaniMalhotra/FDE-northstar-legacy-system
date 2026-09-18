# Northstar Freight — Company Profile

### What the company is, who it works with, and what its people do

This doc is the "who are these people and what do they actually do all day" companion to
[the sibling project's docs/02-ai-copilot-solution.md](../../Northstar-Copilot-POC/docs/02-ai-copilot-solution.md) (the business problem and
the plan). Everything here is grounded in what the synthetic data and code actually contain, not invented on top of
it. This version covers Northstar's legacy world only — the AI copilot built on top of it lives in a separate
project and has its own company-profile doc covering its roles and workflow.

---

## 1. What Northstar Freight is

Northstar Freight is a fictional **freight brokerage**. The one thing that matters most about that word: **Northstar
doesn't own a single truck.** Its entire business is matching two other parties —

- **Shippers** — companies that have freight that needs to move from A to B, and
- **Carriers** — trucking companies that own the trucks and actually drive the freight —

and getting paid the difference between what it charges the shipper and what it pays the carrier to move the same
load. That difference is the **margin** (also called the **spread**), and industry-wide it's thin — often under 15%
— which is why small, unnoticed billing errors are a real threat to the business, not a rounding error.

Every load Northstar books goes through the same basic shape:

1. A shipper needs a truckload moved → Northstar books the load and agrees a price with a carrier (the **rate
   confirmation**).
2. The carrier picks up, hauls, and delivers the freight.
3. The carrier submits an **invoice** asking to be paid — the agreed linehaul rate, plus any **accessorial charges**
   (detention, extra stops, fuel surcharge) it believes it's owed.
4. Northstar's Finance team checks the invoice against what was agreed and what actually happened, and pays it.

Step 4 is manual and error-prone today — that gap is the whole reason this project exists.

---

## 2. Clients and carriers — who Northstar actually works with

### 2.1 Shippers (Northstar's clients)

Shippers are the customers who pay Northstar to get their freight moved. **This project deliberately does not model
shippers as named companies or as system users** — Northstar's side of the business is the carrier relationship. A
shipper shows up in the data only indirectly, as the reason a load exists (an origin city, a destination city, an
agreed rate) — never as a login, a record, or a party anyone in this system talks to directly. The whole system is
built from Northstar's side of the desk, looking outward at its carrier network — not from a shipper's point of
view.

### 2.2 Carriers (Northstar's vendors)

Carriers are the trucking companies in Northstar's network — the vendors it pays to actually move freight. The
synthetic dataset models **12 carriers**, each with a name, an **MC number** (their federal operating license
number — e.g. `MC-100002`), and a **safety rating** pulled from the external TransCheck registry (see §4.5). A few,
by name: Redline Transport, Bluewave Freight, Pioneer Haulers, Summit Trucking, and eight others. Two of the twelve
are deliberately seeded as repeat offenders on detention billing (54% and 38% of their invoices flagged, versus
0–28% for everyone else) — a pattern the AI copilot's reconciliation logic is built to catch, though that logic
itself lives in the separate copilot project.

Against those 12 carriers, the dataset has **150 loads** and **150 matching invoices**, moving freight across 10
lanes between 10 Midwest/South hub cities (Chicago, Indianapolis, Kansas City, Dallas, Atlanta, Memphis, Columbus,
Charlotte, Denver, Phoenix).

---

## 3. How shippers and carriers actually interact with Northstar

Neither shippers nor carriers have a self-service login or portal anywhere in this project — there's no "carrier
portal" or "shipper portal" to point to. That's a deliberate scope choice (see §2.1), and it's also realistic for a
mid-size brokerage running on older systems: everything routes through a Northstar employee.

- **A shipper's involvement ends at booking.** They call or email Northstar with a load; Ops books it into the TMS
  and tenders it to a carrier at an agreed rate. The shipper doesn't see or touch anything after that — no visible
  representation of them exists in this project once the load exists.
- **A carrier's involvement is: haul the load, then get paid.** A carrier is *offered* a load (a tender), *hauls*
  it, and *submits an invoice* after delivery — asking to be paid the agreed rate plus whatever accessorials it
  believes it earned. Every one of those interactions happens through a Northstar employee re-keying or reviewing
  something in an internal system (TMS for the tender, AP for the invoice) — the carrier itself never logs into
  Northstar's systems in this project. The one exception is indirect: TransCheck (§4.5) is an *external* registry
  Northstar queries about a carrier, not a system a carrier logs into.

So "the portal" a carrier or shipper experiences, in the real world this project is modeling, is really just **a
phone call and a PDF** — a tendered rate confirmation going out, and an invoice PDF coming back in. Everything after
that is entirely internal to Northstar, which is exactly why this project's five internal systems (§4) and the human
roles that run them (§5) are where all the actual work — and all the actual risk — lives.

---

## 4. The five legacy systems

Five separate, unbranded-together internal systems, each with its own look and its own login persona — deliberately
built to feel like they were bought or built at different times, because that's what a real 20-year-old brokerage's
tech stack looks like:

| System | What it's for | Who uses it |
|---|---|---|
| **Northstar AP** (`/ap`) | Invoice review queue — see what's pending, on hold, or approved, and open one invoice at a time to review it against the load | Priya Nair, Accounts Payable (Finance) |
| **Northstar TMS** (`/tms`) | Transportation Management — where loads are booked and tendered to carriers, and where the agreed rate lives | Transportation / Ops |
| **DockTrak** (`/dock`) | Terminal Operations, Dallas DC — the real timestamped record of when a truck actually arrived and left a dock | Terminal/dock staff |
| **Carrier Management** (`/carriers`) | Vendor records — Northstar's own file on each carrier it works with | Carrier Management |
| **TransCheck** (`/safety`) | *External* — a carrier compliance/safety registry Northstar doesn't own (`backend/legacy_carrier_safety.py`) | Compliance, and looked up on demand by anyone checking a carrier's safety rating |

The landing page ties them together as one "Operations Portal," but under the hood they're five independent apps
sharing nothing but a login banner — including, critically, **no cross-checking between them**. Nothing in Northstar
AP automatically looks at DockTrak's real timestamps before approving a detention charge. That gap — the data that
would catch a bad invoice existing, just in a different system nobody has time to cross-reference — is the entire
reason this project exists (see the sibling project's [docs/02-ai-copilot-solution.md §2.2](../../Northstar-Copilot-POC/docs/02-ai-copilot-solution.md)).

Underneath all five, there's one Postgres database with deliberately cryptic legacy table names (`dbo.tbl_carr_mstr`,
`dbo.tbl_load_bkg_raw`, `dbo.tbl_dock_evt_raw`, `dbo.tbl_carr_invc_raw`) — the "ugly legacy schema" every one of
these apps reads and writes directly, with one shared admin login and no row-level restriction. That's deliberate:
it's what a real 20-year-old system with no governance actually looks like.

### TransCheck — the one external system

TransCheck is the one system in this project Northstar doesn't own — a stand-in for a real external carrier-safety
registry a brokerage would subscribe to. An earlier version simulated it as a real SOAP/XML service on its own
port, matching how these vendor integrations often still look in practice — accurate, but a second process to keep
running added real operational overhead without teaching anything the current version doesn't: `backend/legacy_carrier_safety.py`
is now a plain function returning the same data, kept looking like an external lookup (never a direct database
join) without the extra moving part.

---

## 5. Northstar's employees — roles and day-to-day work

- **Priya Nair, Accounts Payable (Finance)** — works the invoice review queue in Northstar AP: opens each invoice,
  checks it against the load and whatever she can see in other systems, and records an Approve/Hold decision.
- **Transportation / Ops** — books and tenders loads in Northstar TMS; the agreed rate a carrier will later invoice
  against comes from here.
- **Terminal / dock staff** — log real arrival and departure timestamps in DockTrak as trucks are loaded or
  unloaded. This is the one system with an honest, timestamped record of what actually happened at the dock — and
  today, nobody downstream automatically checks it.
- **Carrier Management** — maintains Northstar's own vendor file on each carrier it works with (Carrier Master).
- **Compliance** — looks up a carrier's safety rating via TransCheck when needed.

None of these roles cross-reference each other's systems as part of their normal workflow — that's the whole
premise this project's later work (in the separate AI copilot project) is built to fix.

---

## 6. A load's life, start to finish (through invoicing)

1. **A shipper calls Northstar with a load.** Ops books it in Northstar TMS, tenders it to a carrier at an agreed rate
   (say, $1,200) — this is the rate confirmation.
2. **The carrier hauls the load.** Terminal staff at the dock log real arrival/departure timestamps in DockTrak as
   the truck is loaded or unloaded.
3. **The carrier submits an invoice** — the agreed linehaul rate, plus whatever accessorials it believes it earned
   (say, a $400 detention charge for a long wait at the dock).
4. **Northstar AP reviews and decides** — today, without an easy way to cross-check the invoiced detention against
   DockTrak's real timestamps, because that means manually opening a second system.

What happens after that — automated reconciliation against real dock data, a dispute flag, tiered human approval —
is where the separate AI copilot project picks up. This doc only covers Northstar's legacy world (steps 1–4 above).

---

## 7. Quick numbers (from the synthetic dataset)

| Fact | Value |
|---|---|
| Carriers in the network | 12 |
| Loads / invoices modeled | 150 each |
| Lanes (hub cities) | 10 (Chicago, Indianapolis, Kansas City, Dallas, Atlanta, Memphis, Columbus, Charlotte, Denver, Phoenix) |
| Carriers seeded as repeat offenders | 2 of 12 (54% and 38% flag rates) |
| Everyone else's flag rate | 0–28% |
