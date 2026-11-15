# Frontend progress

Branch `frontend/p0` · worktree `../DigiEarth-frontend` · contract v0.2.0

## Packages
| # | Status | Notes |
|---|---|---|
| FE-01 | done | Vite 8, React 19, TS strict, ESLint, Vitest, tokens, shell, /api proxy |
| FE-02 | done | Cesium + NASA GIBS BlueMarble_ShadedRelief_Bathymetry (layer, matrix set `500m`, levels 0-7 checked against GetCapabilities; tile fetched OK). Outline, fly-to, click -> [lon, lat], viewer destroyed on unmount |
| FE-03 | done | Types generated with openapi-typescript; openapi-fetch client; fixture `fetch` serves every endpoint (health, variables, regions, region, analyze, trend-maps + image, guide, sessions CRUD); permanent SAMPLE banner in fixture mode |
| FE-04 | done | Top-bar region search (client-side filter), variable select, region and variable cards with definitions, "Suggested for this region", unavailable variables disabled with reason |
| FE-05 | done | Result panel: verdict, text significance badge, annual/monthly/anomaly chart with Sen and OLS lines, explainer, details, source, caveats. Nulls are gaps |
| FE-06 | done | Trend-map overlay (nearest-neighbour, alpha 0.8) + legend; click globe -> point analyse; result bbox drawn as cell outline |
| FE-07 | done | Wizard: Start -> region -> variable -> Investigate (4 clicks, tested) |
| FE-08 | done | Guide drawer, Zod action whitelist (unknown types dropped and logged), "Rules-based guide" label |
| FE-09 | done (fixtures) | Mekong, Amazon, Sahel walkthroughs; text has no digits (tested). Not yet run against real API |
| FE-10 | done (fixtures) | Save/list/restore with Zod validation; URL `/s/:id`. Fixture sessions are in memory only |
| FE-11 | done | Real API verified; see FRONTEND_HANDOFF.md |

## Verification
- `npm run build`, `npm run lint`, `npx tsc`: pass. `npm test`: 20 tests pass.
- Manual in browser pane (fixture mode): wizard -> result with chart, trend map overlay + legend + region outline rendered.
- NOT verified manually: click-to-analyse on the live globe (covered only by unit tests of lon/lat conversion), demos and Guide drawer in the browser, session save/restore in the browser (the latter two covered by unit tests), overlay/coastline alignment (fixture image is synthetic, so cannot be checked until the real PNG exists).

## API assumptions (to reconcile in FE-11)
- Region ids confirmed from the backend's `presets.geojson` (read-only): `mekong-delta`, `central-java`, `johor`, `amazon-central`, `sahel`. Fixtures now use exactly these five; demo ids already match.
- Backend notes: rainfall ends 2025-09 (2025 annual is null; default rainfall period effectively 2001-2024); only precipitation and soil_moisture trend maps exist in `data/maps` so far.
- Variable ids unchanged: Variable ids: `precipitation`, `soil_moisture`, `air_temperature`, `ndvi`. Demos hard-code these ids; the backend must use them or the demos need updating.
- Legend gradient colours are keyed on `legend.palette` (brown-green or blue-red) in CSS; they must match the colours the backend draws in the PNG.
- `alpha` is always sent (0.05) because the generated type marks it required.
- `imageUrl` from the API is used as-is for the overlay.

## Mismatches / change requests
- None filed. Note for architect: the contract's `BBox`/`LonLat` are plain `number[]`, so the frontend narrows them to tuples in `src/api/types.ts`.

## Blockers
- FE-11 needs the backend.

## Notes
- TypeScript pinned to 5.9: TS 7 conflicts with typescript-eslint and openapi-typescript peers.
- `npm audit`: see the fixes round table (triaged).
- Guide drawer starts closed so the globe has room at 1440 px wide.
- Fixture numbers are synthetic and shown only under the SAMPLE banner.

## Fixes round (branch `frontend/fixes`, contract 0.2.1)
| # | Status | Notes |
|---|---|---|
| 1 | done | Types regenerated. `endYear` is omitted unless set (store `endYear: null`); the period shown comes from the API result. Saved sessions with a fixed endYear still load. Fixtures derive the last complete year from `coverage.end` |
| 2 | done | `ApiError` carries the API message and code; 400s are not retried; no cell is drawn on error |
| 3 | done | Legend uses `legend.colorStops` when present, else the palette name |
| 4 | done | Overlay bounds clamped to the globe; legend notes a clamped west edge |
| 5 | pending | Needs the backend on :8000 (not running at the time of writing) |
| 6 | done | ion logo hidden with CSS; GIBS credit set to show on screen |
| 7 | pending | Screenshots, after 5 |
| 8 | done | `npm audit`: 0 vulnerabilities in production dependencies; 7 moderate, all dev-only (minimatch DoS advisory GHSA-g3hv-75wg-m249 inside typescript-eslint tooling), not shipped and only reachable through lint globs, so accepted; revisit when typescript-eslint releases a fix |
