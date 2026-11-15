# PLAN 1 — Frontend | Earth Digital Twin — Trend Detective

> **Claude Code execution brief.** Build the React + CesiumJS web app that consumes `contracts/trend-detective-api.openapi.yaml` (v0.2). Work only in `frontend/`. Do not touch `backend/`, `data/` or `contracts/`.
>
> Read first: `_Mission/ARCHITECTURE.md` (product, decisions, config). Visual reference: `_Mission/earth_digital_twin_vantage_uiux.html` — reuse its colours, typography and layout feel; its numbers are illustrative and must not appear in the app.

## 0. Goal and done-ness

Done (P0) means a student can: open the globe → start an investigation (where → what) or click any point → see the chart, the stats card and a plain-language verdict with provenance → turn on the global trend map → ask the Guide for variable ideas → follow one of three demo walkthroughs → save and reopen the session. Every number shown comes from the API; nothing scientific is computed or worded in the browser.

Keep it simple: one page app, a handful of components, one store, no server-side rendering, no auth.

## 1. Start-of-work checklist

1. Work in your own git worktree/branch (e.g. `frontend/p0`).
2. Start with **contract-valid fixtures** (`VITE_USE_FIXTURES=true`); switch to the real API when the backend reports BE-06 ready. Same components either way.
3. Keep `frontend/FRONTEND_PROGRESS.md`; commit after each package that passes its check.
4. Contract problems → entry in `contracts/CHANGE-REQUESTS.md` + tell the user. Do not edit the contract.
5. No third-party tokens are needed for P0 (NASA GIBS basemap). If you think one is needed, ask the user; never ask for values in chat.

## 2. Stack

| Concern | Choice |
|---|---|
| Build | Vite + React + TypeScript (strict) |
| Globe | CesiumJS via `vite-plugin-cesium`; no Cesium ion assets |
| Basemap | NASA GIBS WMTS (EPSG:4326, e.g. `BlueMarble_ShadedRelief_Bathymetry`; confirm layer name and URL template from GIBS GetCapabilities); credit "Imagery: NASA GIBS" |
| API types | `openapi-typescript` generated from the contract + `openapi-fetch` |
| Server state | TanStack Query |
| UI state | Zustand (one store) |
| Charts | Recharts |
| Runtime checks | Zod for Guide actions and saved-session state |
| Styling | CSS Modules + `tokens.css` (Vantage: primary `#1557BF`, active `#072F72`) |
| Tests | Vitest + React Testing Library (Playwright smoke in P1) |

Vite dev server on 5173 proxies `/api` → `http://localhost:8000`.

## 3. Layout

```text
┌──────┬──────────────────────────────────────────────┬────────────┐
│ Nav  │  Top bar: region search · variable chip ·     │            │
│      │           [Start investigation]               │   Guide    │
│ Exp- ├───────────────┬──────────────────────────────┤  drawer    │
│ lore │ Investigation │                              │  (right,   │
│ Demos│ panel (left,  │        3D globe              │  360 px,   │
│ Saved│ ~440 px)      │   (trend map overlay,        │  toggle)   │
│      │ chart, stats, │    region outline, cell)     │            │
│      │ verdict,      │                     [legend] │            │
│      │ provenance    │                              │            │
└──────┴───────────────┴──────────────────────────────┴────────────┘
```

Left nav (collapsible, 288 px / 76 px): Explore, Demos, Saved sessions. Desktop ≥ 1280 px is P0; tablet/mobile layout is P1.

## 4. Journeys

### A. Guided investigation (wizard, 3 steps)
1. **Where?** Preset cards (name, region type, one-line description) or "Pick a point on the globe" (closes wizard, enters pick mode).
2. **What?** Variable cards grouped by topic, each with `shortDefinition`; variables in the region's `suggestedVariableIds` get a "Suggested for this region" badge. Unavailable variables are shown disabled with `unavailableReason`.
3. **Investigate** → calls `POST /trends/analyze` (default 2001–2025), flies to the region, opens the result.

### B. Explore
Pick a variable → "Show trend map" → overlay + legend. Click anywhere → `analyze` with `{point}`; draw the returned cell (`region.bbox`) as an outline. Search box filters `/regions` client-side and flies to the selected preset.

### C. Result panel (the core screen)
- Header: variable name @ region name, period, representativeness badge built from `region.cellCount` and `region.cellSize` ("Average of N cells of 0.5°" or "Single 0.5° cell, about 55 km across"), `dataStatus` chip.
- **Verdict card:** `interpretation.headline`; big numbers: change per decade (Sen's slope, `annualUnit` per decade), total change, Mann-Kendall p; status badge with **text** (Significant / Not significant / Not enough data), not colour alone; methods-agreement line.
- **Chart:** annual values (nulls are gaps, never 0) with Sen's and OLS lines from `trendLines`; toggle to monthly values or monthly anomalies.
- **"What does significant mean?"** expandable explainer (static text: p-value, α = 0.05, why a trend can be real but not yet significant).
- **Details:** OLS slope with 95% CI and t-test p; τ; n.
- **Source:** provenance fields + citation + link. **Caveats** list from the API.
- Actions: Show trend map · Ask the Guide · Save session.

### D. Guide drawer
Chat UI calling `POST /guide/chat` with the message plus current `regionId`/`variableId`. Render `reply`, suggestion chips (click = select variable) and action buttons. Actions run only when the user clicks, and only if their `type` is in the whitelist (validated with Zod; unknown types are dropped and logged). Show a "Rules-based guide" label when `mode = rules`.

### E. Demo walkthroughs (3, frontend-owned)
Step-by-step overlays in `src/demos/`: each step has short text and one whitelisted action. Text asks questions ("Has rainfall changed here? Let's check.") and **never contains numbers or claimed outcomes**; the numbers come from the live result.
1. Mekong Delta — rainfall, then topsoil moisture (farming angle).
2. Amazon (central) — vegetation greenness and air temperature.
3. Sahel — rainfall and vegetation greenness, then the global rainfall trend map to compare regions.

### F. Sessions
Save → `POST /sessions` with `state = {version: 1, variableId, region, startYear, endYear, showTrendMap, chartMode, camera?, guideMessages}`; URL becomes `/s/:sessionId`; "Saved sessions" lists `GET /sessions`; opening one restores everything. Validate loaded state with Zod; if invalid, open the app empty with a message.

## 5. Globe rules

- Viewer options: no base layer picker, geocoder, timeline or animation widgets; `baseLayer` = GIBS provider; ellipsoid terrain.
- Trend map: `SingleTileImageryProvider` over `bounds`, alpha ≈ 0.8, **nearest-neighbour magnification** so 0.5° cells look like cells (no fake smoothness). Always show the legend with unit, period and `fadedMeaning`.
- Region outline: `GeoJsonDataSource` from `region.geometry`; fly to `bbox`. GeoJSON is `[lon, lat]` — test it.
- Create the viewer once; destroy it and its handlers on unmount.

## 6. Data display rules

- Units, labels, definitions and interpretations come from the API; do not hard-code them.
- `dataStatus = sample` → large visible "SAMPLE DATA — not NASA results" banner; `unavailable` → disabled control with reason.
- Fixture mode always shows the sample banner.
- Round displayed numbers sensibly (2 significant figures for slopes; p-values as "p = 0.03" or "p < 0.001").

## 7. Code layout

```text
frontend/
  src/
    app/{App.tsx, router.tsx, providers.tsx}
    api/{schema.d.ts (generated), client.ts, queries.ts, fixtures/}
    state/store.ts
    components/{layout/, globe/, chart/, common/}
    features/{wizard/, result/, guide/, demos/, sessions/}
    demos/{mekong.ts, amazon.ts, sahel.ts}
    styles/{tokens.css, global.css}
  .env.example             # VITE_API_BASE=/api/v1, VITE_USE_FIXTURES=true
```

## 8. Work packages (in order)

| # | Pri | Package | Done when |
|---|---|---|---|
| FE-01 | P0 | Scaffold: Vite/React/TS strict, ESLint, Vitest, tokens from Vantage, app shell (nav, panel, drawer slots), Vite proxy | `npm run dev`, `npm run build`, `npm test` pass |
| FE-02 | P0 | Globe: Cesium + GIBS basemap, fly-to bbox, outline, click → lon/lat, cleanup | Globe renders without console errors; click logs correct lon/lat |
| FE-03 | P0 | API layer: generated types, client, query hooks, fixtures for every endpoint, sample banner | All endpoints callable in fixture mode |
| FE-04 | P0 | Region search/presets + variable picker with definitions | Selecting a preset flies to it and outlines it |
| FE-05 | P0 | Result panel: verdict, chart + trend lines, monthly/anomaly toggle, details, explainer, source, caveats | All three significance states render correctly from fixtures |
| FE-06 | P0 | Trend map overlay + legend + click-to-analyse a cell | Overlay aligns with coastlines; cell outline matches result bbox |
| FE-07 | P0 | Wizard (where → what → investigate) | Wizard reaches a result in ≤ 4 clicks |
| FE-08 | P0 | Guide drawer + action whitelist | Unknown action types are ignored |
| FE-09 | P0 | Three demo walkthroughs | Each runs start to finish against fixtures, then the real API |
| FE-10 | P0 | Sessions save/list/restore | Restore reproduces variable, region, period, map and chat |
| FE-11 | P0 | Switch to real API (after backend BE-06), fix mismatches, handoff | Demo script passes against the local backend; `FRONTEND_HANDOFF.md` |
| FE-12 | P1 | Compare two regions side by side (shows opposite trends) | — |
| FE-13 | P1 | Tablet/mobile layout, glossary page, Playwright smoke test | — |

## 9. Tests

- Fly-to and outline use `[lon, lat]` correctly (Mekong ≈ 105.8° E, 10° N).
- Fixture/sample banner always visible in sample mode.
- Significance badge text for `significant`, `not_significant`, `insufficient_data`.
- Null annual/monthly values render as gaps.
- Guide: whitelisted actions run on click; an unknown type is dropped.
- Session state round-trip through Zod.
- Changing variable or region triggers exactly one analyze request.

## 10. Prompt for the Frontend session

> You are the Frontend implementation agent for Earth Digital Twin — Trend Detective. Read `_Mission/ARCHITECTURE.md`, `_Mission/PLAN-1-Frontend.md` and `contracts/trend-detective-api.openapi.yaml`, and look at `_Mission/earth_digital_twin_vantage_uiux.html` for visual style only. Work only in `frontend/` on your own branch/worktree. Start in fixture mode with contract-valid fixtures and a visible sample banner; switch to the real API at `localhost:8000` when the backend reports it ready. Implement P0 packages in order, keep it simple (one store, no extra frameworks), take every number, unit and interpretation from the API, and never invent scientific values. Finish with build and tests passing, screenshots and `FRONTEND_HANDOFF.md`.
