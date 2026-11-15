# PLAN 1 — Frontend Implementation | Earth Digital Twin Farming MVP

> **Claude Code execution brief.** Implement the React + 3D-globe frontend. Do NOT implement NASA ETL, scientific statistical analysis, or backend application logic in this workstream. Those belong to `PLAN 2 — Backend + Data`.
>
> **Priority:** P0 is a working source-connected Earth Explorer and Mekong Delta farming analysis. P1 is richer interaction. P2 is projections/optional polish. Time-box aggressively if targeting the 2026 NASA Space Apps submission window.

## 0. Mission and boundaries

**Product:** Earth Digital Twin — unified environmental intelligence with the first industry-specific vertical slice **Farming**.

**First real region:** Mekong Delta, Vietnam. **SEA expansion hooks:** Johor (Malaysia) and Central Java (Indonesia) as disabled/unavailable catalog entries until backed by processed NASA observations; do not present invented indicators for those places.

**Primary user journey:** Open 3D Earth -> search Mekong Delta -> zoom and highlight its boundary -> toggle real NASA-derived climate/vegetation layers -> scrub a historical monthly timeline -> inspect trends, anomaly and significance -> open Farming Agent in a right drawer -> apply a suggested map action -> save and restore the workspace.

**UI reference:** Reuse the existing uploaded `earth_digital_twin_vantage_uiux.html` as a visual and behavioral reference. The Vantage screenshots establish layout and affordances, not production data. Do not copy fake analysis values into the production UI. Preserve design tokens/colors and behavior where reasonable.

**Core Vantage layout constraints:**
- Fixed/collapsible royal blue left navigation, expanded ~288px / icon-only ~76px; active state dark blue `#072F72`, primary `#1557BF`.
- Home: dominant globe + global place search + compact floating layer toggles/legend/events.
- Place Analysis: white contextual left panel ~420–460px, globe fills remaining width; resizable/collapsible on smaller screens.
- Farming Agent: right overlay/drawer ~360–400px; preserve place context and globe interaction. Closing/reopening maintains conversation for the current session.
- Timeline: bottom floating control; historical observations visually distinct from future scenario data.

### P0 scope and non-goals

P0 MUST:
1. Render a working rotatable 3D Earth via **CesiumJS**, fly to Mekong Delta, and display a sourced boundary and at least one real geospatial indicator layer or spatial sample points.
2. Use GET APIs defined in `earth-digital-twin-mvp-api.openapi.yaml`, with typed client and explicit `source_backed | sample | unavailable` status.
3. Show temperature and rainfall historical time series from returned real NASA-derived results; show trend slope/unit, significance status, period and data source.
4. Support switching a layer, a metric, and a historical year/month, synchronizing map, legend, side panel and chart; warn/no-gap-fill when data unavailable.
5. Open/close/reopen Farming Agent; send a contextual question and render evidence/caveats. If LLM is not ready, use the backend's deterministic evidence-based response.
6. Support save/reopen analysis, backend if available and explicitly marked browser-local fallback otherwise.
7. Mobile/desktop usable without losing region context; keyboard accessible controls and legible colors.

P1: MODIS NDVI/GLDAS soil moisture real layers; insight comparison and click a spatial cell; EONET event markers (if backend available).

P2: POWER climate projection time mode 2030–2050, multiple scenarios, agent map actions beyond show_layer, Google Photorealistic 3D Tiles optional.

**Do not claim** crop-yield prediction, scientifically calibrated farm suitability, precise farmland/city predictions, current/live satellite feed or causal attribution.

## 1. Start-of-work protocol (Claude Code)

1. Inspect repository structure and project setup before editing. Check `package.json`, existing React app and UX scaffold. Reuse existing app where possible; don't overwrite the prototype or unrelated modules.
2. Create your **Frontend mission worktree/branch**. If the repository is shared with Backend work, avoid editing `apps/api`, `pipeline`, `data`, or API spec except through explicit contract coordination.
3. Locate or copy `earth_digital_twin_vantage_uiux.html` to `design/reference/`; read it but refactor into components rather than embedding the entire HTML file as an iframe.
4. Copy shared `earth-digital-twin-mvp-api.openapi.yaml` into `contracts/` and generate/hand-author types matching it; contract changes require synchronization with Backend team.
5. Keep a `FRONTEND_PROGRESS.md` with completed tasks, API assumptions, blockers and screenshots. Commit after every independently working milestone.
6. Never report fake datasets as actual NASA observations. Fixtures use obvious `SAMPLE DATA` status visible on screen.

## 2. Recommended implementation stack

- React 18/19 + TypeScript + Vite, reuse existing versions if repository already configured.
- CesiumJS for globe, GeoJSON polygons, historical spatial cells/points and camera navigation.
- TanStack Query for API cache/loading/errors; Zustand for UI state (or existing state library).
- Recharts or ECharts for historical line charts, anomalies, projection bands and tooltips.
- Lucide icons, CSS Modules/Tailwind depending on existing UI; preserve Vantage colors/tokens.
- Zod for runtime validation of API responses; generated OpenAPI TS types preferred.
- Vitest + React Testing Library for units; Playwright for interaction smoke tests.

**Basemap strategy:** Start CesiumJS with a legally suitable publicly served imagery layer / configured Cesium ion token. If token unavailable, use an attribution-compliant fallback; always keep a working globe. Google Photorealistic 3D Tiles is OPTIONAL behind `VITE_ENABLE_GOOGLE_TILES`, requires Google billing/API key, visible credits and compliance with Maps Tile policies. Google tiles must never be used as analytical/ML input or cached outside permitted terms. Do not spend MVP time on Google tiles if science layers are incomplete.

## 3. Information architecture / routes

```
/                           Earth Explorer (globe + universal place search)
/places/:placeId            Function A — Place Analysis
/places/:placeId/farming    Same place, Farming Agent drawer open (deep-linkable)
/analyses                   Saved analyses/history
/analyses/:analysisId       Restore place/time/layers/agent conversation
```

Left navigation expanded:
- Earth Explorer
- Place Analysis
  - Farming (ONLY enabled industry in MVP)
  - Forest, Ocean, Minerals, Natural Disasters, Urban Development (disabled with "Coming later")
- Saved Analyses
- Sidebar collapse affordance; search independent of current page.

Important: Industry Agent is the **right-hand contextual chat drawer**, not a separate full-page replacement of the globe.

## 4. Component tree and suggested directory

```
apps/web/
  src/
    app/{router.tsx,AppShell.tsx,providers.tsx}
    components/layout/{Sidebar.tsx,SearchBar.tsx,Panel.tsx}
    components/globe/{EarthGlobe.tsx,RegionBoundary.tsx,DataLayer.tsx,MapLegend.tsx,MapPopup.tsx,GlobeControls.tsx}
    components/time/{Timeline.tsx,ScenarioSelector.tsx,TimeModeBadge.tsx}
    features/place/{PlaceAnalysisPanel.tsx,IndicatorCards.tsx,TrendChart.tsx,EvidencePanel.tsx}
    features/farming/{FarmingAgentDrawer.tsx,AgentMessage.tsx,SuggestedActions.tsx}
    features/sessions/{SaveAnalysisDialog.tsx,SavedAnalyses.tsx}
    api/{client.ts,types.ts,queries.ts,adapters.ts}
    state/{workspaceStore.ts,sessionStore.ts}
    fixtures/{samplePlace.json,sampleTimeseries.json,sampleSpatial.json,sampleAgent.json}
    styles/{tokens.css,global.css}
    tests/
```

Use lazy-loaded Cesium globe so route transitions don't recreate WebGL context unnecessarily. Use dynamic imports if required for Cesium worker assets; configure Vite assets correctly. Scope all listeners and destroy Cesium resources on unmount.

## 5. Exact API dependency contract

**Contract source of truth:** `earth-digital-twin-mvp-api.openapi.yaml` (use supplied file unchanged). These are the calls to implement:

| UI feature | API | Needed fields |
|---|---|---|
| Search/preset places | `GET /api/v1/places?q=mekong` | place id, country, center, geometry, geometrySource |
| Select and fly to place | `GET /api/v1/places/mekong-delta` | real AOI geometry and documented boundary source |
| Layer selector | `GET /api/v1/catalog/layers?placeId=mekong-delta` | status, coverage period, metric, enabled modes |
| Place overview | `GET /api/v1/places/mekong-delta/overview` | indicators, insights, provenance |
| Chart | `GET /api/v1/places/mekong-delta/timeseries?metric=precipitation_mm&mode=observed` | month/value/unit/trend/provenance/representativeness |
| Globe heat layer | `GET /api/v1/places/mekong-delta/spatial?metric=precipitation_mm&period=2024-06&mode=anomaly` | GeoJSON cells / measured grid values, not fabricated detail |
| Future scenario (P2) | `GET /api/v1/places/mekong-delta/projections?metric=temperature_c&scenario=ssp245&start=2030&end=2050` | conditional projection with model/resolution |
| Farming question | `POST /api/v1/agent/farming/chat` | question + place, year, active metrics, scenario; answer+evidence+actions |
| Session history | `GET/POST /api/v1/analyses` and `GET/PUT /api/v1/analyses/{analysisId}` | title, place, year, layers, scenario, uiState, messages |

Maintain correct semantics:
- `source_backed` means retrieved and processed from a cited source, not that the inference is peer-reviewed.
- `sample` must display a prominent fixture/demo label; never hide it in a tooltip.
- `unavailable` means disable layer or show source/missing-data explanation.
- `null` values are gaps, not 0.
- Values must include the exact unit and spatial representativeness (`point_sample` vs `area_mean`).
- Geospatial coordinates in API GeoJSON are `[longitude, latitude]` WGS84; UI lat/lon order must be tested.

### UI fixtures development rule

FE begins with contract-compatible fixtures for all endpoints. No auto-detection that swaps sample and real without banner. Add a visible source status chip and a developer-only fixture toggle. When BE arrives, switch same components through API client, not a new UI. Offline fixtures can demonstrate UX but cannot count as a real-data hackathon proof.

## 6. Primary user journeys and state transitions

### Journey A — Earth Explorer

1. Initial load: dark-space globe with real basemap, globe zoomed toward Southeast Asia, global search at top.
2. Place presets include **Mekong Delta** enabled. Johor and Central Java are either disabled or clearly marked "data onboarding pending".
3. Select Mekong Delta: navigate to `places/mekong-delta`, fly to verified region `geometry`, highlight its boundary, expand contextual left panel.
4. Display active source-backed layers as pills: Rainfall, Temperature; add NDVI and Soil Water only if real backend data exists.
5. Click layer/cell/marker: tooltip with measurement, period, unit, source product, spatial resolution, quality flag and action "View trend".

### Journey B — Place Analysis

1. Left panel: title, country/region, data coverage, "What changed?" summary, compact indicator cards.
2. Historical mode: month/year slider restricted to available observations, with play/pause and user-selectable speed. Animation must throttle API calls, prefetch or reuse cache, and visibly show gaps.
3. Chart panel: monthly series, seasonal anomaly/observed toggle; trend slope and significance badge with period, p-value when available, and method; line chart no arbitrary "confidence".
4. Show in globe: current selected period's actual spatial grid/polygons/points. If only an area-average or one NASA POWER sampling point exists, show a region outline + label/point—not a fake fine-grained heatmap.
5. User can ask "What changed since 2001?" and click the source reference to inspect provenance.

### Journey C — Farming Agent

1. Click Farming in the nav or the left panel => open right drawer, preserve place/time/layers.
2. Send `question`, `placeId`, `metricIds`, `scenario`, `year`, optionally `sessionId`.
3. Render answer with evidence cards and caveats. Clearly label observation, association, hypothesis or scenario.
4. For `actions` allow **whitelisted** UI transformations only: `show_layer`, `focus_place`, `open_chart`, `set_year`; never run arbitrary code from LLM text.
5. Close/reopen => history restored. Changing places asks whether to clear agent context or starts new place-scoped context; never silently mix region evidence.

### Journey D — Save and restore

Persist title, selected region, selected layers, timeline mode/year/month, scenario, camera state if stable, selected metric, agent history. Prefer backend API. In temporary local fallback use browser localStorage with explicit "Saved in this browser" label. No user login in MVP; no cloud persistence/security claims.

## 7. Map/visual design implementation rules

- Use scientifically meaningful color ramps: diverging palette for signed anomalies, sequential for intensities, categorical only for categories. Always display legend, variable unit, time and valid range.
- Annual/monthly animation should update layers from source-backed datasets. For temperature vs rainfall use explicit unit/legend; do not place both on same color scale.
- Support GeoJSON boundary + point markers as baseline; real continuous raster coverage or measured aggregation polygons only if BE produces them.
- Interpolating a coarse model grid to visually smooth colors does NOT improve source resolution; display warning/original resolution.
- Historical vs future: hard UI divider at last observation; projections use dashed lines/different panel and SSP label; no automatic continuous "observed" animation into future.
- All dates are source-aware; UTC storage, local-friendly presentation. Prevent monthly-to-daily animation if only monthly data exist.
- Agent can't overwrite visualized data; it can only choose existing data layers and vetted actions.

## 8. Work breakdown (dependent order)

| Stage | Priority | Work package | Completion check |
|---|---|---|---|
| FE-01 | P0 | Repo inspect, Vite/Cesium setup, UI tokens | dev server and quality gates run |
| FE-02 | P0 | AppShell/sidebar and globe | collapse nav, flyTo Mekong, no WebGL errors |
| FE-03 | P0 | API client, generated types, fixtures and status banners | all required endpoints represented and testable |
| FE-04 | P0 | Place search, AOI boundary, layer selector and map legend | action on map correlates to metric/time/source |
| FE-05 | P0 | Place panel, history chart and trend/significance | provenance/units and missing-data behavior correct |
| FE-06 | P0 | Timeline, month selection and map synchronization | changing time updates map+chart+panel once |
| FE-07 | P0 | Farming Agent drawer + safe map actions | conversations retained; no arbitrary actions |
| FE-08 | P0 | Save/reopen session + responsive smoke tests | workspace recovers same context |
| FE-09 | P1 | NDVI/soil-water advanced visualization | only enabled on source-backed data |
| FE-10 | P2 | Projection mode and Google tiles integration | clearly differentiated from historical series |

## 9. Acceptance tests / Definition of Done

**Automated tests:**
- TypeScript strict compile + lint + production build.
- GeoJSON center/fly-to correct (lon/lat), border visible, Cesium mounts/unmounts.
- Search returns Mekong Delta and navigates to place route.
- Changing metric updates API request, chart unit, legend, tooltip and layer.
- Historical slider cannot select unsupported data; empty/null data remains empty.
- Trend badge says `insufficient_data` when API returns it; never fabricate p-values.
- Distinct visual labels for `source_backed`, `sample`, `unavailable`.
- Agent safe action whitelist with rejected unknown action.
- Save/reopen preserves place, year, layers, panel and chat state.
- Mobile viewport: collapsing side panels does not hide globe interaction completely.

**Manual demo script (under 2 minutes):** open globe -> Mekong -> Rainfall layer -> move to a past month -> select temperature trend -> show source and significance -> open Farming Agent and ask "Which environmental factors show stress?" -> show layer action -> save -> reopen. All displayed numeric facts must be provenance-backed.

**Required handoff artifacts:** working frontend code, run commands, `.env.example`, screenshot(s), Playwright smoke tests, `FRONTEND_PROGRESS.md`, and `FRONTEND_HANDOFF.md` including API mismatches and any remaining sample features.

## 10. Claude Code prompt to execute this plan

> You are the Frontend implementation agent for Earth Digital Twin Farming MVP. Read this full plan and the accompanying OpenAPI contract. Inspect the existing repository and the provided Vantage-style UI scaffold before making edits. Work only on the frontend worktree. Implement P0 tasks in order with working React/Cesium components; use contract-valid fixtures while backend is unavailable, keeping fixtures visibly labeled. Integrate live APIs without changing UX component contracts. Run tests/build, fix errors, and produce a concise handoff with screenshots, commands, feature status, and blockers. Do not fake NASA results or make crop yield, causality, or forecast-confidence claims.

## 11. Verified references

- NASA 2026 Trend Detective challenge: https://www.spaceappschallenge.org/2026/challenges/earth-system-trend-detective/
- CesiumJS: https://cesium.com/platform/cesiumjs/
- Cesium imagery API: https://cesium.com/learn/cesiumjs/ref-doc/ImageryLayer.html
- Google tile policies: https://developers.google.com/maps/documentation/tile/policies
- Google tile billing: https://developers.google.com/maps/documentation/tile/usage-and-billing
- NASA POWER historical API: https://power.larc.nasa.gov/docs/services/api/temporal/monthly/
- NASA POWER climate projection API: https://power.larc.nasa.gov/docs/services/api/projection/
