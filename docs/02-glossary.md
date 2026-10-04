# Glossary

Every term used in this project, in one place — freight/logistics terms first, then the terms
specific to how this portal itself is built.

## Freight & logistics terms

| Term | What it means here |
|---|---|
| **Carrier** | A trucking company that actually moves the freight (e.g., "Pioneer Haulers"). Northstar doesn't own trucks — carriers do the driving. |
| **Shipper** | The company that needs freight moved — Northstar's paying customer. |
| **Broker** | What Northstar Freight is: the middleman who finds a carrier for a shipper's load and pockets the difference between what the shipper pays and what the carrier is paid. |
| **Load / Shipment** | One truckload going from an origin city to a destination city on a specific date. |
| **Rate confirmation** | The agreed price and terms for a shipment, set at booking time (`shipments.agreed_rate`) — what the invoice should later match. |
| **Detention** | A fee a carrier charges when their truck has to wait too long at the dock before loading/unloading, beyond a free-time allowance (`detention_free_hours`). |
| **Accessorial (charge)** | Any extra fee beyond the base linehaul rate — detention is one example; fuel surcharge is another. |
| **Linehaul** | The base rate for actually moving the freight from A to B, not counting extra fees. |
| **Fuel surcharge** | An extra charge tied to fuel price changes. |
| **Dock event** | A timestamped record (`dock_events`) of a truck arriving at or departing a dock — the real-world fact detention is measured against. |
| **MC number** | A trucking company's federal operating license number (e.g., `MC-100002`) — a stable ID for looking a carrier up. |
| **Margin / Spread** | The difference between what Northstar charges the shipper and pays the carrier for the same load. |
| **Safety rating** | A carrier's standing (e.g., Satisfactory, Conditional) tracked on the carrier record — reviewed on the employee "TransCheck" page before booking with a new or flagged carrier. |
| **Elevated risk** | A flag on a carrier's own record (`carriers.elevated_risk`) marking it for closer scrutiny — set manually by an employee. |

## This project's own terms

| Term | What it means here |
|---|---|
| **Portal** | One of the three self-service sites this project serves — shipper, employee, or carrier — each its own login and set of pages, all calling the same backend. |
| **Session cookie** | An opaque, server-issued token (`northstar_web_session`) stored as an `HttpOnly` cookie after login — every other API request is checked against it; nothing relies on client-side JavaScript to enforce who's logged in. |
| **pgcrypto** | A Postgres extension used to check a password's hash directly inside the database (`password_hash = crypt(:password, password_hash)`) — the application code never reads or compares a raw password itself. |
| **FastAPI** | The Python web framework the backend (`backend/northstar_web_api/`) is built with — it turns HTTP requests into typed Python function calls. |
| **Postgres role** | A database-level login with its own explicit permissions — this project uses two: a read/write role for the API's own connection, and a strictly read-only role for an FDE (or, in the sibling project, the AI) to connect with directly. See [04-security-and-access-model.md](04-security-and-access-model.md). |
| **RBAC (Role-Based Access Control)** | Giving different logins different permissions based on their role (shipper/employee/carrier, or a specific employee role) instead of one shared login for everyone. |
| **Northstar-Copilot-POC** | The sibling project: a standalone AI system that reads and writes this project's own `northstar_web` database directly, adding its own tables and roles on top — nothing in this project changes to support it. |
| **Northstar-Legacy-With-AI** | A second sibling project: a copy of this portal with the AI copilot woven directly into the employee pages — the "after" version of this "before" system. |
