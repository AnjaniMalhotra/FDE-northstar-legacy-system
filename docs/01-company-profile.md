# Northstar Freight — Company Profile

What the company is, who it works with, and what its people do — grounded in what the data and
code actually contain.

## 1. What Northstar Freight is

Northstar Freight is a fictional **freight brokerage**. The one thing that matters most about that
word: **Northstar doesn't own a single truck.** Its entire business is matching two other parties —

- **Shippers** — companies that have freight that needs to move from A to B, and
- **Carriers** — trucking companies that own the trucks and actually drive the freight —

and getting paid the difference between what it charges the shipper and what it pays the carrier to
move the same load. That difference is the **margin** (also called the **spread**), and
industry-wide it's thin — often under 15% — which is why small, unnoticed billing errors are a real
threat to the business, not a rounding error.

Every load Northstar books goes through the same basic shape:

1. A shipper needs a truckload moved → an employee books it and agrees a price with a carrier (the
   **rate confirmation**).
2. The carrier picks up, hauls, and delivers the freight.
3. The carrier submits an **invoice** asking to be paid — the agreed linehaul rate, plus any
   **accessorial charges** (detention, fuel surcharge) it believes it's owed.
4. Northstar's Finance team checks the invoice against what was agreed and what actually happened,
   and approves or holds it.

Step 4 is where billing errors either get caught or slip through — the reason a system that can
cross-check an invoice against real data (rather than a person's memory of two other screens)
matters.

## 2. Who Northstar works with

### Shippers (Northstar's clients)

Shippers are the customers who pay Northstar to get their freight moved. In this system, a shipper
has their own login and portal (`frontend/northstar_web/shipper/`) — they submit a shipment
request (origin, destination, weight, goods, pickup date, and a carrier they'd like used), and can
track it once it's approved and moving.

### Carriers (Northstar's vendors)

Carriers are the trucking companies in Northstar's network — the vendors it pays to actually move
freight. Each carrier record (`carriers` table) has a name, an **MC number** (their federal
operating license number, e.g. `MC-100002`), a **safety rating**, and a count of out-of-service
violations. Carriers also have their own login and portal
(`frontend/northstar_web/carrier/`) — they see shipments assigned to them, submit invoices, and can
view disputes raised against a submitted invoice.

## 3. The three portals

Unlike an older system where every interaction routes through a phone call or an employee re-keying
something, this system gives each party its own direct, self-service login:

| Portal | Who logs in | What they do |
|---|---|---|
| **Shipper** | The customer booking freight | Submit a shipment request, track its status |
| **Employee** | Northstar staff (Operations, Finance, Carrier Management) | Approve/reject booking requests, review invoices, manage the carrier network, look up safety ratings |
| **Carrier** | The trucking company hauling the freight | View assigned shipments, submit invoices, see any disputes raised |

All three share one login table and one database (`northstar_web`) — see
[03-portal-architecture.md](03-portal-architecture.md) for how the three fit together and
[04-security-and-access-model.md](04-security-and-access-model.md) for how access is kept separate
between them.

## 4. A load's life, start to finish

1. **A shipper submits a request.** Origin, destination, weight, goods, a pickup date, and the
   carrier they'd like — this becomes a row in `shipment_requests` with status `PENDING_REVIEW`.
2. **An employee reviews and decides.** Approving it creates a real `shipments` row with an agreed
   rate and the carrier's detention terms (free hours, rate per hour) copied in at booking time —
   this is the rate confirmation the later invoice gets checked against.
3. **The carrier hauls the load.** Arrival and departure are captured as `dock_events` rows tied to
   the shipment — a real, timestamped record of what actually happened, independent of whatever the
   carrier later bills for.
4. **The carrier submits an invoice.** The agreed linehaul rate, plus whatever detention/fuel
   surcharge it believes it earned — a new `invoices` row, status `PENDING_APPROVAL`.
5. **An employee (Finance) reviews and decides.** Approve, put `ON_HOLD`, or ask for a revision —
   recorded as an `invoice_decisions` row, so every invoice keeps a full decision history, not just
   a final status.

Whether the billed detention hours actually match the real gap between the two `dock_events`
timestamps is exactly the kind of cross-check that's easy to describe and tedious to do by hand
across two different screens — which is the whole reason `Northstar-Legacy-With-AI` exists as a
sibling project.

## 5. Quick numbers (from the seeded dataset)

| Fact | Value |
|---|---|
| Carriers in the network | 25 |
| Shippers | 50 |
| Invoices | 100 |
| Invoice status mix | ~7% on hold, ~52% approved, ~41% pending approval |

These numbers come from the shared `northstar_web` database — the same database
`Northstar-Legacy-With-AI` reads from, so both projects always show the same real data.
