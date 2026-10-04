# Northstar Freight — Legacy System

Northstar Freight is a fictional freight brokerage — a company that doesn't own trucks, but matches
shippers who need freight moved with carriers who move it. This is Northstar's self-service portal:
shippers book shipments, employees approve them and review invoices, and carriers haul the freight
and bill for it — all without any AI involved. It's the "before" system: the world an AI copilot
(built separately, in the sibling `Northstar-Copilot-POC` project) gets added on top of later,
without changing anything in here. See [`project-overview/README.md`](project-overview/README.md)
for the full three-part capstone this project is one part of.

## Try it

**Option A — Docker, no account needed.** Runs the portal and its own throwaway database on your
machine:
```bash
docker compose up --build
```
Then open **http://localhost:8080/**. First start takes a little longer while the database sets
itself up with sample data; every start after that is quick.

**Option B — deploy it to your own Google Cloud project.** Creates a real, hosted copy — a managed
Postgres database (Cloud SQL) and a public URL (Cloud Run):
```bash
bash deploy/setup_gcp.sh <your-gcp-project-id>
```
Requires the `gcloud` and `terraform` CLIs, already logged in (`gcloud auth login`) and billing
enabled on the project. Takes a few minutes; prints the live URL when it's done.

## Log in and look around

| Portal | Demo login | Password |
|---|---|---|
| Shipper | `shipper@acmemfg.com` | `demo123` |
| Employee — Operations | `ops@northstarfreight.com` | `demo123` |
| Employee — Accounts Payable | `ap@northstarfreight.com` | `demo123` |
| Employee — Admin | `admin@northstarfreight.com` | `demo123` |
| Carrier — Pioneer Haulers | `dispatch@pioneerhaulers.com` | `demo123` |
| Carrier — Redline Transport | `dispatch@redlinetransport.com` | `demo123` |

(Every carrier in the network has its own login — the pattern is `dispatch@` + the carrier's name,
lowercased with spaces removed.)

## What you can do in each portal

- **Shipper** — request a shipment (route, weight, goods, a carrier you'd like), then track it.
- **Employee** — review and approve booking requests, review submitted invoices against what was
  agreed and what actually happened at the dock, manage the carrier network, and look up a
  carrier's safety rating.
- **Carrier** — see the shipments assigned to you, submit an invoice once delivered, and see any
  disputes raised against an invoice you've submitted.

A shipment's life, start to finish: a shipper requests it → an employee approves it and it becomes
a real booking → the carrier hauls it (arrival/departure at the dock are captured automatically,
like a real telematics feed) → the carrier submits an invoice → an employee reviews it and approves
or holds it, with a note if held → a held invoice can be revised and resubmitted. Every invoice can
be downloaded as a PDF from the browser's own print dialog.

## Learn more

[docs/PROJECT_SUMMARY.md](docs/PROJECT_SUMMARY.md) is the starting point for understanding
Northstar Freight as a business, the freight/logistics terms used throughout, how the portal itself
is put together, and how access and security are enforced.

---

### For developers

This project is built to be read, not just run — see [CLAUDE.md](CLAUDE.md) for the code
philosophy, [docs/03-portal-architecture.md](docs/03-portal-architecture.md) for how the backend
and database fit together, and [docs/04-security-and-access-model.md](docs/04-security-and-access-model.md)
for how login and data access are enforced by Postgres itself. `deploy/terraform/` holds the
infrastructure-as-code behind Option B above, and `Dockerfile`/`docker-compose.yml` behind Option A.
