# Architecture Diagram Prompts — Northstar Freight FDE Story

Image-generator prompts that tell this project's actual story, in order: the freight brokerage's
existing legacy world → the manual approval pain inside it → the brief handed to the FDE → the AI
solution proposed in the POC → how that solution was grafted onto the legacy system without
touching what already existed. Each diagram is grounded in this repo's real screens and code (not
a generic "AI architecture" filler), so each one teaches a true fact about the system, not just a
pretty box-and-arrow picture.

Shared visual language for every prompt below: **Excalidraw-style hand-drawn diagram, wide
landscape orientation, bold black sketchy outlines, soft pastel fills, white background, icons
doing almost all of the work, text limited to short 1-3 word labels** — image generators render
long text badly, so every real explanation lives in this file's prose, not inside the image
itself. The full style block is repeated in every prompt on purpose — generators do better with a
self-contained prompt than one that references "the same style as before."

---

## 1. Northstar Freight — the company, before any AI

**The real fact behind this diagram:** Northstar Freight is a freight brokerage. Three kinds of
people use its one self-service portal today — shippers who book loads, Northstar's own employees
(dispatch, accounts payable), and the carriers who haul the freight and bill for it. Carriers
submit invoices; employees approve them for payment. No AI exists anywhere in this world yet.

```
Excalidraw-style hand-drawn architecture diagram, wide landscape orientation, whiteboard sketch
aesthetic, bold black hand-drawn outlines, soft pastel fills, slightly wobbly hand-drawn lines,
white background, minimal text — short 1-3 word labels only, icons doing most of the work.

Left side: three simple hand-drawn figures in a vertical stack, each with a one-word label beside
it — a shipping-box icon labeled "Shipper", a delivery-truck icon labeled "Carrier", a person with
a headset icon labeled "Employee". Each connects by its own arrow rightward into one large central
rounded rectangle, light blue fill, containing a simple computer-screen/portal icon, labeled
"Portal".

From the Carrier figure specifically, draw one extra small icon riding along its arrow: a tiny
invoice/receipt icon with a dollar sign, to show carriers specifically submit invoices.

From the Portal box, one arrow continues right into a classic hand-drawn database cylinder icon,
pastel yellow, labeled "Database".

Nowhere in this image: no robot, no brain, no AI icon of any kind — this diagram is the "before
AI" world and should visually read as plain and ordinary, almost old-fashioned, like an ERP screen
from a decade ago. Add one small calendar icon in a corner with no real meaning, just to add a
touch of everyday-office texture.

Overall mood: clean, friendly, whiteboard-sketch, like a founder explaining their current business
on a glass wall — not corporate, not 3D, not photorealistic.
```

---

## 2. The problem — approving an invoice today means checking 5 places by hand

**The real fact behind this diagram:** this is the single clearest pain point in the whole
project. On the real employee invoice-detail screen, a plain on-page notice says it outright:
*"Northstar's systems do not automatically verify detention hours billed against the load's agreed
terms or the real dock timestamps — use the tabs above to compare by hand before deciding."* The
"tabs above" are five separate reference screens (Shipments/TMS, Dock Events/DockTrak, Carrier
Master, TransCheck, Policy Reference) that an Accounts Payable employee must click through
one-by-one, holding the numbers in their head, before pressing one of two buttons: **Approve for
Payment** or **Hold Payment (Dispute)**. Nothing cross-checks these five systems against each
other automatically — that gap is the whole reason the FDE engagement exists.

```
Excalidraw-style hand-drawn architecture diagram, wide landscape orientation, whiteboard sketch
aesthetic, bold black hand-drawn outlines, soft pastel fills, slightly wobbly hand-drawn lines,
white background, minimal text — short 1-3 word labels only, icons doing most of the work.

Center: one tired-looking hand-drawn stick figure at a desk, wearing a small tie, with a thought-
bubble above its head containing a single big question mark.

Arranged around the figure in a fan/arc, five separate small rounded rectangles, each a different
pastel color, each with its own simple icon and short label, each connected to the stick figure by
its own thin hand-drawn arrow pointing INTO the figure's head (showing the person must gather all
five by hand): a truck icon labeled "Shipments", a clock icon labeled "Dock Events", a folder icon
labeled "Carriers", a shield icon labeled "TransCheck", a document icon labeled "Policy".

Below the figure, one invoice/receipt icon with a dollar sign sits on the desk, with a dotted line
connecting it up to the thought bubble, to show this is the invoice being decided on.

To the right of the figure, two small buttons drawn as simple hand-drawn pill shapes: a green
checkmark icon labeled "Approve" and a red stop-hand icon labeled "Hold" — both drawn slightly
faded/pale, with a small "?" hovering between them, to show the decision is uncertain and manual.

Add a few small red zig-zag "error" or spark icons scattered faintly in the background, to suggest
mistakes slip through unnoticed.

Overall mood: clean, friendly, whiteboard-sketch, but with a slightly stressed, overwhelmed feeling
— like a founder sketching their own team's daily headache on a glass wall. Not corporate, not 3D,
not photorealistic.
```

---

## 3. The brief — what Northstar asked the FDE to solve

**The real fact behind this diagram:** Northstar's ask to the FDE, in plain terms, was: catch
billing errors and fraud risk in carrier invoices *before* they get paid — without taking the
final approval decision away from a human. The deliverable had to respect that constraint from
day one.

```
Excalidraw-style hand-drawn architecture diagram, wide landscape orientation, whiteboard sketch
aesthetic, bold black hand-drawn outlines, soft pastel fills, slightly wobbly hand-drawn lines,
white background, minimal text — short 1-3 word labels only, icons doing most of the work.

Left: the same five-tab overload scene as before, drawn smaller and faded/pale this time (a tired
stick figure with five small faded icons fanned around it) inside a rounded rectangle labeled
"Today".

A single thick hand-drawn arrow points right from this box into a simple hand-drawn briefcase
icon in the center, with a small magnifying-glass badge on it, labeled "The Ask".

From the briefcase, three short arrows fan out rightward into three small icon badges stacked
vertically: a bug/error icon labeled "Billing Errors", a mask or warning-triangle icon labeled
"Fraud Risk", and a raised-hand icon labeled "Human Decides" — this third one drawn slightly
bigger and bolder than the other two, with a small padlock on it, to visually emphasize it is the
non-negotiable constraint.

Far right: a small hand-drawn figure wearing a hard-hat or an engineer's cap, labeled "FDE",
receiving all three arrows into a single thought bubble above its head.

Overall mood: clean, friendly, whiteboard-sketch, like a founder handing a brief to an engineer on
a glass wall — not corporate, not 3D, not photorealistic.
```

---

## 4. The proposed solution (POC) — the full reconciliation pipeline

**The real fact behind this diagram:** this is the actual decision pipeline built in
`Northstar-Copilot-POC/copilot/guardrails.py`, deliberately deterministic rather than left to the
AI's own judgment. Two reconciliation engines feed it — one for **detention** (checks both a time
variance AND a dollar variance, since dwell-time billing has a real clock dimension) and one for
**linehaul** (a flat agreed-rate-vs-billed-rate check, dollar only, no time dimension). Either
engine's result passes through the same two-stage policy: first an **eligibility check** (is the
overcharge even real and above the minimum threshold — if not, nothing is logged at all), then,
only for eligible cases, a **tier decision** between exactly two documented triggers: the dollar
amount clears a hard Tier-2 threshold, OR this carrier has hit a repeat-flag-count inside a time
window (a pattern signal, counted regardless of how past flags were resolved). Tier 1 can be
logged automatically as a flag; Tier 2 cannot — and *neither* tier ever approves, holds, or pays
anything by itself. The agent that uses this pipeline is a LangGraph "reasoner ↔ tools" loop,
grounded by a RAG search over Northstar's own policy documents, with one tool
(`log_dispute_flag`) as its only write capability.

```
Excalidraw-style hand-drawn architecture diagram, wide landscape orientation, whiteboard sketch
aesthetic, bold black hand-drawn outlines, soft pastel fills, slightly wobbly hand-drawn lines,
white background, minimal text — short 1-3 word labels only, icons doing most of the work.

Top-left: two small input icons stacked, each feeding one arrow rightward into the pipeline — a
clock-with-dollar-sign icon labeled "Detention" and a flat-ruler/rate-tag icon labeled "Linehaul".
Both arrows merge into one single arrow (drawn as a simple "Y" merge) flowing into the first
pipeline stage.

A horizontal pipeline of four hand-drawn shapes left to right, connected by arrows:

1. (rounded rectangle, light blue) a magnifying-glass-over-dollar-sign icon, labeled "Eligible?".
   One arrow exits its bottom toward a small trash-can icon (meaning: stop, nothing logged) for
   "no"; one arrow continues right for "yes".
2. (diamond shape, light yellow) two small icon badges side by side inside it: a dollar-sign-in-
   circle icon and a repeating-arrows/cycle icon, labeled "Tier?" — showing the two real triggers
   checked here.
3. Two small rounded rectangles branching from the diamond: one light green labeled "Tier 1" with
   a small pencil/log icon (auto-logged), one light red labeled "Tier 2" with a small siren/alert
   icon (escalated, never auto-logged).
4. (large rounded rectangle, far right, light red fill, bigger than the others) a raised-hand or
   stop-hand icon, labeled "Human" — both Tier 1 and Tier 2 arrows converge into this one box.

Below the whole pipeline, draw a separate small loop of two circles connected by two curved
arrows (a mini version of a reasoning loop): a brain icon labeled "Reasoner" and a toolbox icon
labeled "Tools", with one small thin arrow rising up from the Tools circle into the pipeline above
it, and one small document-stack icon with a magnifying glass labeled "Policy" feeding into the
Tools circle from below.

Overall mood: clean, friendly, whiteboard-sketch, like a founder explaining a well-thought-out
system on a glass wall — not corporate, not 3D, not photorealistic.
```

---

## 5. Integration — the AI layer added beside the legacy system, nothing removed

**The real fact behind this diagram:** the integration project (`Northstar-Legacy-With-AI`) is a
full copy of the legacy portal with the AI layer woven in *additively* — same HTML/CSS, same
database, same existing routes, all untouched. What's new sits beside it: a chat widget and an "AI
Review" panel bolted onto the existing invoice page, a new `/api/ai/...` route prefix living next
to the portal's own existing `/api/...` routes in the very same process, and new database tables
(`dispute_flags`, `ai_invoice_reviews`, `agent_audit_log`) added on top of
the existing tables in the one shared database — never replacing or editing them. The two features
even keep two independent login sessions (the portal's own, and the AI's own), quietly chained
together so the user only ever sees one login prompt.

```
Excalidraw-style hand-drawn architecture diagram, wide landscape orientation, whiteboard sketch
aesthetic, bold black hand-drawn outlines, soft pastel fills, slightly wobbly hand-drawn lines,
white background, minimal text — short 1-3 word labels only, icons doing most of the work.

Center: one large rounded rectangle, drawn with a solid confident outline, light gray fill,
labeled "One App" underneath. Inside it, on the left, a smaller box with a dashed (not solid)
outline, pale and slightly faded, containing a simple house/portal-door icon labeled "Legacy" —
the dashed outline signals "existing, untouched". On the right inside the same big box, a smaller
box with a solid bold outline, brighter color, containing a robot-head icon labeled "AI Layer" —
the solid outline signals "newly added".

From the Legacy box, a short label-only arrow pointing at its own dashed outline with a small
"unchanged" padlock icon. From the AI Layer box, a short arrow pointing at a small "+" plus-sign
icon, to show it is purely additive.

On top of the Legacy box, draw two small new icon badges sitting ON TOP of it like stickers (not
replacing anything underneath): a small chat-bubble-with-robot icon and a small clipboard-with-
checkmark icon — these represent the chat widget and the AI review panel bolted onto the existing
invoice screen.

Below the big outer box, one single database cylinder icon, pastel yellow, labeled "Database".
Draw it with two layers visible inside it like sediment: a thicker bottom layer labeled "existing"
and a thin new top layer added on top labeled "new tables" — both layers inside the one same
cylinder, never two separate cylinders.

Two small key icons above the big box, one gold one silver, each with a short arrow down into the
Legacy box and the AI Layer box respectively — showing two separate logins quietly chained
together, drawn with a small curved connecting arrow between the two keys themselves.

Overall mood: clean, friendly, whiteboard-sketch, like a founder proudly explaining how they
upgraded a system without breaking it, on a glass wall — not corporate, not 3D, not
photorealistic.
```

---

## 6. Database & security — new roles added beside the old ones

**The real fact behind this diagram:** nothing about the legacy database's own access model
changed. It already had two roles — a read/write app role, and a strictly read-only FDE role.
The AI layer adds its own roles on top, purely additively: one role for the AI agent itself
(allowed to read broadly but write only dispute flags), and three human roles matching the AI
console's own permission levels (Analyst, Manager, Admin) — all enforced by real Postgres
GRANTs, never by an `if` statement buried in application code.

```
Excalidraw-style hand-drawn architecture diagram, wide landscape orientation, whiteboard sketch
aesthetic, bold black hand-drawn outlines, soft pastel fills, slightly wobbly hand-drawn lines,
white background, minimal text — short 1-3 word labels only, icons doing most of the work.

Center: one large hand-drawn database cylinder icon, pastel yellow fill, labeled "Postgres",
drawn big in the middle of the canvas.

Two small badges connected to the database by solid black arrows, drawn first and positioned on
the LEFT side of the cylinder (the "already existed" side), each inside a rounded rectangle with a
faded, slightly pale fill: a gear icon labeled "App" (thick arrow, full access) and a person-with-
badge icon labeled "FDE" (dashed arrow, with a small padlock drawn on the arrow, read-only).

Four more small badges on the RIGHT side of the cylinder (the "newly added" side), each drawn with
a bolder, brighter fill and a small "+" plus-sign in the corner of its rounded rectangle to mark
them as new: a robot-head icon labeled "Agent" (thin arrow with a small padlock, narrow access), and
three identical person-silhouette icons grouped in one badge labeled "Analyst / Manager / Admin"
(three thin arrows fanning into the database).

Draw a faint vertical dashed line down the middle of the whole canvas, directly through the
database cylinder, separating the pale "existing" left badges from the bright "+" new right
badges — the line passes through the cylinder itself to show it's the one same database serving
both sides, not two databases.

Overall mood: clean, friendly, whiteboard-sketch, like a founder explaining who's allowed to touch
what, on a glass wall — not corporate, not 3D, not photorealistic.
```

---

## 7. Before vs. after — the human still has the final word

**The real fact behind this diagram:** the single most important thing this whole project does
*not* change: the Accounts Payable employee still presses the same two buttons,
**Approve for Payment** or **Hold Payment**, and still has the final word. What changes is what
they see right before pressing one: instead of manually checking five separate tabs from memory,
they now see one AI Review panel stating the tier and the reasoning, computed by the deterministic
pipeline in diagram 4 — never an auto-approval, never an auto-hold, only a better-informed human
decision.

```
Excalidraw-style hand-drawn architecture diagram, wide landscape orientation, whiteboard sketch
aesthetic, bold black hand-drawn outlines, soft pastel fills, slightly wobbly hand-drawn lines,
white background, minimal text — short 1-3 word labels only, icons doing most of the work.

Split the canvas into two equal halves side by side, separated by a tall dashed vertical line,
labeled "Before" on the left half and "After" on the right half at the very top.

Left half: the same tired stick figure from diagram 2, with five small faded icons fanned around
its head (truck, clock, folder, shield, document), all connecting into its thought bubble. Below
the figure, the same two pale pill-shaped buttons: green checkmark "Approve" and red stop-hand
"Hold", both still drawn slightly faded/uncertain with a small "?" between them.

Right half: the same stick figure, same pose, but calmer — its five small fanned icons are now
replaced by a single small rounded rectangle floating beside its head, bright and clear, containing
a small robot-head icon next to a small clipboard-checkmark icon, labeled "AI Review". One short
arrow flows from this one box into the figure's thought bubble (replacing the five scattered
arrows from the left half). Below the figure, the exact same two pill-shaped buttons as the left
half — green checkmark "Approve" and red stop-hand "Hold" — but drawn bold, solid, and confident
this time, with no "?" between them, and a small hand icon resting near the buttons to emphasize
the human's hand is still the one pressing them.

Overall mood: clean, friendly, whiteboard-sketch, like a founder proudly showing a before-and-after
on a glass wall — not corporate, not 3D, not photorealistic.
```

---

## Tips for using these prompts

- **Follow the order 1 → 7** when presenting these — they tell one continuous story (legacy world
  → the pain → the brief → the proposed fix → how it was integrated → who can touch what → the
  human-decision outcome), and work best shown in sequence rather than as unrelated slides.
- **Generate 2-4 variations per prompt** and pick the cleanest — image generators are inconsistent
  with diagram logic, so the first result isn't always the best one.
- **If icons come out wrong or arrows point the wrong way**, that's a known limitation of current
  image generators with precise diagrams — regenerate rather than trying to prompt-engineer your
  way to perfection; these tools are better at style than at exact logic.
- **If any generated text is garbled** (a common failure mode), that's expected — these prompts
  already ask for minimal text for exactly this reason. Add labels afterward in any image editor
  if needed, rather than fighting the generator for perfect text.
- Diagram 4 (the pipeline) and diagram 6 (the roles) are the two most detail-dense prompts — if a
  generator struggles to fit everything in cleanly, it's fine to split either one into two separate
  images (e.g., split 4 into "reconciliation + eligibility" and "tiering + human gate").
