# Security and Access Model

The core lesson this project teaches: **enforce access with the database itself, not with
application code that could be forgotten or bypassed.**

## Login: the database checks the password, not the app

When someone logs in, the backend never reads a stored password into Python and compares it itself.
Instead, it asks Postgres to do the comparison, using the `pgcrypto` extension:

```sql
SELECT id, portal, role, email, name, company_name, carrier_id FROM users
WHERE portal = :portal AND email = :email AND password_hash = crypt(:password, password_hash)
```

`crypt(:password, password_hash)` re-hashes the submitted password with the same salt already
stored in `password_hash`, and Postgres compares the two hashes directly in the query. If they
match, the row comes back; if not, the query returns nothing. The application code never holds a
raw password longer than the length of one request, and never implements its own hashing or
comparison logic — a common source of authentication bugs.

On success, the backend issues a random session token (`secrets.token_urlsafe(32)`), stores it in a
`sessions` table with an expiry, and sets it as an `HttpOnly` cookie. Every other route requires
that cookie to resolve to a real, unexpired session row — there's no endpoint that trusts a
client-supplied user ID or role.

## Role separation: one users table, three portals, no shared password

Shippers, employees, and carriers are all rows in the same `users` table, distinguished by a
`portal` column (`shipper` / `employee` / `carrier`) and a `role` column for finer-grained
permissions within the employee portal. Logging in always specifies which portal you're logging
into, so the same email can't accidentally authenticate against the wrong portal's data. What a
logged-in user can see and do is decided by their `portal`/`role`, read from their own session row
— never from anything the client sends.

## Database-level access: two Postgres roles, not one shared login

The database itself enforces a second layer, independent of anything the application code does:

| Role | Who uses it | What it can do |
|---|---|---|
| `northstar_web_app` | The FastAPI backend's own database connection | Full read/write on every table — this is the one login the running application uses |
| `northstar_web_fde_ro` | A human FDE (or, in the sibling AI project, the AI's own read-only connection) connecting directly to the database, bypassing the API entirely | `SELECT` only — no `INSERT`/`UPDATE`/`DELETE` grant exists for this role at all |

The read-only role has no write permission **at the database level** — not because the application
chooses not to call a write query with it, but because Postgres itself would reject any write
attempt regardless of what code tried to run it. That's the difference between "the app is
currently written not to do X" and "X is actually impossible" — the second one survives a bug, a
new script, or a future contributor who didn't read the application code first.

**One more restriction, at the column level, not just the table level:** even the read-only role
cannot bulk-read the `password_hash` column:

```sql
REVOKE SELECT ON users FROM northstar_web_fde_ro;
GRANT SELECT (id, portal, role, email, name, company_name, carrier_id) ON users TO northstar_web_fde_ro;
```

An FDE (or the AI) can legitimately need to read user records — to look up who submitted a request,
for example — without ever being able to read password hashes in bulk, even though they're stored
in the same table.

## Why this matters more than it looks like it should

A permission check written as an `if` inside application code has to be present, correct, and
actually reached on every single code path that touches sensitive data or a write — miss one route,
one script, one future feature, and the check silently doesn't apply. A permission enforced by the
database's own role system applies to *every* connection using that role, automatically, including
ones nobody has written yet. That's the whole idea behind "database-enforced access control," and
it's why this project's `CLAUDE.md` treats a hardcoded `if` check as the wrong pattern for anything
touching real access control, in favor of something the database — not the application — is
responsible for holding true.
