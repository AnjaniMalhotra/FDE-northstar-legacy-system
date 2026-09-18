# 04 — Legacy Web Simulation

**Status:** done — built, iterated through four passes, and one bug found and fixed in it

Merges the original build-log 18 (the simulation itself, including its own three follow-up
passes) and 25 (a mislabeling bug found while touching related code later) — the bug belongs with
the feature it was found in, not filed separately.

## Part 1: The five-system simulation

The original single-app Streamlit "before FDE" demo taught the right *idea* (five disconnected
lookup screens, nothing cross-checked) but visually read as one app, not as the pile of separate,
real, unrelated systems a Northstar employee actually has to open. Replaced with
`backend/legacy_web/` — a FastAPI + server-rendered HTML app, same underlying queries and pain
points, presented as five genuinely different-branded systems:

- **Northstar Intranet** (`/`) — a plain links directory, the employee's actual starting point
- **Northstar AP — Invoice Processing** (`/ap`) — invoice lookup plus a real Approve/Hold decision
- **Northstar TMS — Load Booking** (`/tms`) — agreed rate/detention terms for a load
- **DockTrak Terminal** (`/dock`) — raw arrival/departure events
- **Carrier Master File** (`/carriers`) — carrier lookup, no dispute history
- **TransCheck** (`/safety`) — the external carrier safety lookup, styled as a genuinely separate
  third-party vendor site

No AI, no reconciliation math, no cross-checking anywhere — that's the entire point of the
"before" state. One new legacy-style table, `dbo.tbl_ap_invc_dcsn_raw`, records the one real write
(the Approve/Hold decision).

**Structure:** one shared `base.html` layout (blocks for title/CSS/header/content), one router per
system, six fully independent stylesheets (no shared base CSS) so each system reads as a genuinely
different product built by a different team in a different decade — a deliberate trade of a little
CSS duplication for a much stronger visual impression.

**Verified, not assumed:** exercised every route with `curl` against real seeded data — all five
systems' search/detail pages, the POST decision endpoint (confirmed the row round-trips), the
"not found" paths, all CSS files serving 200s. No errors in the server log.

## Part 2: Three realism passes

1. **Landing page + queue widgets** — a card layout grouped by department, a live Invoice Review
   Queue (real pending invoices, no row yet in the decisions table), status badges derived from
   the latest decision row (not a stored status column), and a real two-step Approve/Hold
   confirm-then-submit flow.
2. **Systems-are-competent, workflow-is-the-problem rework** — reframed the premise: the realistic
   enterprise failure mode isn't "five badly-built websites," it's "five individually solid
   systems that were never integrated." Each system got real professional styling and real depth
   (AP's sidebar of modules, Carrier Management's live performance aggregates, TMS's disabled
   "Events" tab as a deliberate detail — that integration was never built, which is the point) —
   while keeping the two hard constraints throughout: no AI/reconciliation logic, no schema
   rebuild. Deliberately **not** added: severity flags on the invoice queue (that judgment belongs
   to the AI copilot, not this "before" state), fabricated performance numbers with no backing
   schema field, fabricated dock-event types beyond the two real ones.
3. **High-production visual overhaul** — Google Fonts, SVG brand icons, live status badges, and a
   distinct professional aesthetic per system (AP's stepper, DockTrak's dark IoT terminal theme,
   TransCheck's violet compliance-SaaS branding), verified with a full pytest/TestClient sweep
   across all 11 endpoints — all `200 OK`.

**Key decisions across all passes:** one FastAPI app, not five separate servers (the illusion of
separation comes from routing + branding, not five real processes); no links between systems (the
friction of manually carrying an ID from one screen to another *is* the pain point this whole
exercise exists to demonstrate).

## Part 3: A mislabeling bug found later, and fixed

While simplifying TransCheck's SOAP mechanics (build-log 03), found that `northstar_web`'s own
employee-portal TransCheck tab carried the same "EXTERNAL" badge and a banner claiming it's "a
third-party registry Northstar doesn't own" — but unlike `legacy_web`'s version, this page reads
carrier safety data straight out of `northstar_web`'s own `carriers` table, the exact same row
Carrier Master already uses. There was no separate system there at all; the "external" framing was
cosmetic, copied from the legacy simulation without the underlying separation to back it up.

**Fix:** removed the `EXTERNAL` badge from the TransCheck nav link across all 10 employee-portal
pages that repeated it, replaced the misleading banner with an accurate one, and fixed a matching
false claim on `carriers.html`. Removed the now-fully-unused `.ext-tag` CSS rule.

**Key decision:** don't manufacture real separation just to justify a label. The tempting
"consistent" fix would have wired this page to actually call the legacy safety module, reintroducing
cross-app plumbing for a page whose only real problem was a mislabeled banner. Fixing the label was
the actual fix — `northstar_web`'s design choice (safety data living on the carrier record) isn't
wrong, it's just a different, equally valid choice from `legacy_web`'s genuinely-separate one.
