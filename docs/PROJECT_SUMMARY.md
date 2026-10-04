# Project Summary

## What this project is

Northstar Freight's self-service portal: a shipper, employee, and carrier each get their own login
and can book, approve, track, and invoice a shipment end to end — no AI anywhere in this project.
This is the "before FDE" world: the client's existing system, as it was before any AI was added.
`Northstar-Copilot-POC` (a separate, standalone project) is the AI copilot built to read and write
this same database; `Northstar-Legacy-With-AI` is a copy of this portal with that AI woven directly
into the employee pages.

## Where to start

- [01-company-profile.md](01-company-profile.md) — what Northstar Freight is, who it works with,
  and how a load moves from booking to invoice.
- [02-glossary.md](02-glossary.md) — every freight/logistics term and every term specific to how
  this portal itself is built, in one place.
- [03-portal-architecture.md](03-portal-architecture.md) — how the three portals, one backend, and
  one database fit together.
- [04-security-and-access-model.md](04-security-and-access-model.md) — how login and database
  access are enforced by Postgres itself, not by application code.

## How the code itself is written

Because this is a teaching project, code quality here means something specific: **the minimum code
needed to teach each concept**, not the most complete or clever solution. See
[CLAUDE.md](../CLAUDE.md) for the exact rules.
