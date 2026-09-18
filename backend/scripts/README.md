# Scripts Index

Setup scripts for this project's one database — not the application itself (that's
`backend/northstar_web_api/`). `bootstrap.sh` runs all of these in order automatically; see it for
the exact sequence if setting up by hand instead.

## `northstar_web` database (the self-service portal)

- `northstar_web_schema.sql` — the schema (carriers, users, shipments, invoices, ...)
- `northstar_web_security.sql` — the read/write app role + the read-only FDE role
- `northstar_web_migrate_contact.sql` — the public contact-form inquiries table
- `seed_northstar_web_data.py` — seeds realistic mock data across the full booking→invoice flow

## Bootstrap

- `bootstrap.sh` — runs everything above in order, idempotently

`legacy_web` and its supporting `northstar_freight` scripts (`legacy_schema.sql`,
`generate_synthetic_data.py`, `load_legacy_data.py`, `migrate_ap_decisions.sql`) have been retired
— moved to `deletes/`, not removed outright. See
[docs/build-log/06-retire-legacy-web-and-northstar-freight.md](../../docs/build-log/06-retire-legacy-web-and-northstar-freight.md).
