# 03 — TransCheck: the External Carrier-Safety Feed

**Status:** done

Merges the original build-log 07 (built as a real SOAP feed) and 24 (later simplified) — the full,
honest arc: built accurately, then simplified once the real cost became clear.

## Part 1: Built as a real SOAP/XML service

TransCheck simulates an external carrier-safety registry (the kind real freight brokerages
integrate with — FMCSA-style safety data has historically been served this way) — a system
Northstar doesn't own or control, genuinely separate from its own database.

**What was built:** `legacy_soap_server.py`, a mock XML/SOAP carrier-safety lookup service
exposing one operation, `GetCarrierSafetyProfile`, over a hand-built SOAP-envelope-shaped
request/response (standard library only, no WSDL framework — a student can see the entire wire
format directly). `legacy_soap_client.py` built the request XML and parsed the response,
including a proper SOAP `<Fault>` for an unknown carrier. Data lived in an in-memory dict, not
Postgres.

The mock data reinforced the fraud narrative from the synthetic invoices: the two repeat-offender
carriers (Pioneer Haulers, Prairie Express) show elevated out-of-service violation counts, and
Prairie Express's insurance status is "Expired" — a second, independent signal a real risk memo
would use to escalate a carrier.

**Tested end to end:** two known carriers (including both repeat offenders), a clean carrier, and
an unknown MC number (correctly returned a SOAP fault, not a crash) — all four passed.

## Part 2: Simplified — same lesson, one fewer process to run

The real SOAP/XML mechanics were accurate to how these vendor integrations often look in practice,
but a second process a student has to keep running is a real, unrelated failure mode ("is the SOAP
server up?") that added operational complexity without teaching anything the underlying lesson
needed. The lesson worth keeping: TransCheck's data is genuinely external — it never lives in
Northstar's own database, and checking it is a manual extra step nobody bothers with unless
something's already gone wrong. That doesn't require a real wire protocol, only that the lookup go
through a function, never a direct database join.

**What changed:** `backend/legacy_carrier_safety.py` — the same `CARRIER_SAFETY_DATA` dict, plus a
`get_carrier_safety_profile(mc_number)` function with the exact same contract the SOAP client had.
`legacy_soap_client.py`/`legacy_soap_server.py` retired to `deletes/`. `backend/legacy_web/routes/safety.py`
(the TransCheck screen) needed only a one-line import change — the function signature didn't
change — and lost a now-impossible `except Exception` branch (a plain dict lookup can't fail with
a network error).

## Key decisions

- **Keep the concept, drop the mechanism.** Removing TransCheck entirely would have also removed
  the "why does checking this help" story — it automates a cross-reference a human skips because
  it's extra effort — a much bigger loss than the wire-protocol complexity it would have saved.
- **Don't rewrite history to match the present.** The SOAP build genuinely happened and taught real
  skills (constructing/parsing SOAP-style XML, handling faults); simplifying it later doesn't erase
  that it was real, tested engineering — it's a real, honest decision (build it accurately, then
  simplify once the cost is clear), not a codebase pretending it was always this way.
