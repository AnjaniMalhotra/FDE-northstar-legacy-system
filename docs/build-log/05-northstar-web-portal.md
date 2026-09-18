# 05 — Northstar Web Portal Visual Enhancements

**Status:** done

## What we built (the plan)

Elevated `frontend/northstar_web/` (the shipper/employee/carrier self-service portal) from plain
boxed content to a high-production corporate freight website aesthetic (matching tools like
Flexport, Samsara, and C.H. Robinson).

## Implementation details

- **Brand & asset generation:** regenerated photographic assets with explicit Northstar Freight
  branding on facilities and dock scenes, and vetted partner carrier names (Redline Transport,
  Pioneer Haulers, Bluewave Freight) on truck trailers across hero imagery. Replaced the legacy
  logo badge with a custom compass-star emblem.
- **Design system:** Google Fonts (`Plus Jakarta Sans`, `Inter`, `JetBrains Mono`), glassmorphism
  overlays, warm neutral elevations in `tokens.css`; topbar glass blur, photo hero overlay scrim,
  elevated overlap cards, stat-counter strip, and a multi-column enterprise footer in `base.css`.
- **Homepage overhaul:** bold all-caps hero card, a "Why Choose Us" dark image-card grid, a
  trusted-by-clients logo strip, an end-to-end capabilities grid with real photographic headers,
  and an interactive Shipment Tracking & Account Portal widget replacing the old plain portal-card
  directory.
- **Secondary marketing pages** (services, about, industries, contact) each got matching hero
  banners and photographic capability/industry cards.
- **Role-based login portals** (shipper/employee/carrier) gained auto-fill demo-credential buttons.
- **Layout & contrast refinements:** dark glass backdrop cards behind hero text, natural grid flow
  for overlap cards, compacted card padding, and full portal app-shell CSS (sidebar, topbar,
  KPI row, filter bar) re-integrated so all three portal dashboards stay fully styled.

## Verification

Stood up the static server (port 8010) and the FastAPI backend (port 8020). Ran an automated sweep
across all 30 public and internal portal pages — all returned clean `200 OK` with zero layout
overlap or contrast issues.
