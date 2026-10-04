# How the AI Integration Works

## What this is

`Northstar-Legacy-With-AI` is the self-service freight portal — shipper booking, employee
operations, carrier invoicing — with an AI copilot woven directly into the employee side. The AI's
own logic (the reconciliation math, the reasoning agent, its guardrails, RAG policy search) runs
**inside this project's own backend** — `copilot/` and `backend/copilot_api/`, ported in from the
standalone `Northstar-Copilot-POC` project, which stays separate and unmodified as a
stakeholder-facing demo. Nothing about the portal's own booking → approval → delivery → invoice
flow changed to make room for it — every addition here is new surface area, not a rewrite of what
was already there.

## How it works

**One process, one port.** `backend/northstar_web_api/main.py` is the only app that runs. It mounts
the portal's own routes and the AI's own routes (`backend/copilot_api/`) side by side — the AI's
routes all live under `/api/ai/...`, specifically so they can never collide with the portal's own
generic `/api/{collection}` routes.

**The chat widget.** Every employee page carries a floating "Ask the AI copilot" bubble
(`shared/js/ai_widget.js`). It calls `/api/ai/...` on this same app — no separate service, no
cross-origin request, and no login of its own: it reads the exact same `northstar_web_session`
cookie the employee already has from logging into the portal.

**AI Review, on the invoice page.** Opening any invoice shows an AI Review card, positioned above
the human Decision so it reads as the first thing to check, not an afterthought. It runs the same
reconciliation the widget can — comparing billed detention and linehaul charges against real dock
timestamps and the agreed rate — and shows its reasoning plainly. It never approves or holds a
payment itself; that stays a human decision, made in the Decision card immediately below it.

**Pending Approvals and Audit Log.** Two more tabs in the employee sidebar, each a full page backed
by the AI's own data: flags waiting on a human decision, and the complete record of what the AI has
done and why. Access to each follows the AI's own role model — an Analyst won't see Pending
Approvals, since that requires Manager- or Admin-level review.

**A larger dataset.** The starter seed (12 carriers, 2 shippers, a handful of invoices) is enough to
show the golden path but not enough to explore the AI at any real volume. `generate_more_data.py`
adds on top of it — never replacing it — to reach roughly 25 carriers, 50 shippers, and 100
invoices, with a realistic mix of clean invoices, harmless rounding noise, and genuine billing
discrepancies for the AI to actually find.

**The Policies page.** Promoted to the main sidebar and rewritten with real depth: all four of the
documents Finance & Compliance actually work from (detention policy, linehaul policy, the dispute
workflow, and the carrier risk memo), with worked examples showing exactly where a threshold falls.

## Design decisions

**One login, not two.** The AI has no session or login of its own. `backend/copilot_api/auth.py`'s
`get_ai_user` depends directly on the portal's own `require_session` (same
`northstar_web_session` cookie, same DB-backed `sessions` table) and translates the already
-authenticated employee's portal role into an AI role via `copilot/identity.py`'s
`PORTAL_ROLE_MAP` — no second credential check, no second cookie, nothing to log into separately.
An earlier version of this integration kept two independent session models (a `copilot_session`
cookie the widget logged into silently, right after the portal login) — it worked, but it was two
systems pretending to be one: a server restart wiped the AI's in-memory session while the portal's
own DB-backed one survived, and a non-awaited silent-login call could lose a race against the
page navigation that followed it, leaving a stale role's session behind indefinitely. Deriving the
AI's identity from the portal's session on every request, instead of caching a second one,
removes both failure modes at the source rather than patching around them.

**Native pages, not an embedded console.** Pending Approvals and Audit Log render as ordinary
portal pages — styled with the portal's own cards, buttons, and tables — that call the AI's routes
directly, rather than embedding a separate console in an iframe. A cross-origin iframe's own login
doesn't reliably keep its session in modern browsers (Safari's tracking protections in particular
treat a third-party iframe's cookies very differently from a page's own direct requests), and an
embedded console never feels like part of the system it's embedded in anyway.

**The brain moved in, the frontend didn't need to change.** Earlier, these same pages called a
separately-running `Northstar-Copilot-POC` service over HTTP (`localhost:8030`). The frontend was
already styled to match the portal and already called through one shared helper
(`aiApiRequest()`), so folding the actual logic into this project's own backend only required
changing that helper's base URL from an absolute cross-origin address to a relative, same-origin
one (`/api/ai`) — nothing about how any page looks or behaves changed.

**The static site moved in too, for the same reason.** For a while after the brain moved in, the
site itself was still served separately (`python3 -m http.server`, its own port) from the API —
meaning `ai_widget.js`'s relative URL was actually resolving against the *site's* origin, not the
API's, and silently 404ing. `backend/northstar_web_api/main.py` now mounts the static site itself
(`StaticFiles`, after every API route) so there's truly one process, one port, one origin — the
same fix already applied to `Northstar-Legacy-System`.

**The AI never touches Northstar's own approval record.** The portal's own `invoice_decisions` table
— who actually approved an invoice for payment — is untouched by any of this. The AI's own review
is a separate record, shown alongside it, answering a narrower question: did the AI look at this
invoice, and what did it find. The two can be read together without either one silently overwriting
the other.

**One dataset, shared.** This portal and the AI both read and write the same database. The AI's own
tables (its flags, audit trail, and review records) are additions on top of the portal's schema, not
a parallel copy of it — an invoice here is the same invoice the AI sees.
