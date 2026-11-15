# Frontend handoff (FE-11)

Branch `frontend/p0` · contract v0.2.0 · tested against backend branch `backend/p0` at `localhost:8000`, 15 Nov 2026.

## Run
```bash
cd frontend
cp .env.example .env.local      # set VITE_USE_FIXTURES=false for the real API
npm install && npm run dev      # http://localhost:5173, /api proxied to :8000
npm run build && npm test && npm run lint
```
`npm run gen:api` regenerates `src/api/schema.d.ts` from `contracts/trend-detective-api.openapi.yaml`.

## START-HERE demo script against the real backend (no sample banner shown)
| Step | Result |
|---|---|
| 1. Start investigation -> Mekong Delta -> Rainfall -> Investigate | Pass: verdict "statistically significant", 13 cells, `dataStatus` = source-backed |
| 2. Verdict numbers, "What does significant mean?" | Pass (numbers shown are the API's; rounded to 2 s.f.) |
| 3. Monthly anomaly chart; Source section | Pass: chart label "Anomaly (mm/month)"; source shows dataset, version, processing, citation |
| 4. Show trend map, click a cell elsewhere | Pass: overlay + legend (2001–2024, FDR note); click gave a single-cell result ("about 55 km") |
| 5. Guide: "What should I look at in a desert?" -> chip -> run on Sahel | Pass (Guide replied "Rules-based"; chose Sahel via search box, clicked the suggestion) |
| 6. Save session -> reload `/s/:id` -> Saved sessions | Pass: variable, region, trend map restored; list shows the session |
| Demos (Mekong, Amazon, Sahel) | All steps ran to the end against the API, including the global rainfall map |

Not checked: visual alignment of the overlay with coastlines at high zoom (only seen at globe scale); opposite-trend regions were not inspected in detail; no screenshots are saved to files (viewed in the pane only); tablet/mobile (P1).

## Observations for the Architect / Backend
1. Rainfall ends 2025-09: 2025 annual value is null; rainfall map period is 2001–2024 while analyses default to 2001–2025 (the result says so in caveats). Worth deciding whether the default period for rainfall should be 2001–2024.
2. Point on the ocean (e.g. `[0, 0]` NDVI) returns `bbox [0,0,0,0]`, `cellCount 0`, and `insufficient_data` with `dataStatus: source_backed`. Frontend skips drawing a zero-size cell. A `bbox` of the real cell would be nicer.
3. MERRA-2 results show cell size "0.5° × 0.625°" (from `cellSize`); fine, displayed as given.
4. `health.dataVersion` was `uninitialised` and status `degraded` during testing (NDVI ingest was finishing; NDVI became source-backed during the session).
5. Contract types `BBox`/`LonLat` are `number[]`; frontend narrows them to tuples.
6. Generated request type marks `alpha` required (it has a default); the frontend always sends 0.05.

## Known gaps
- Cesium's default "ion" credit logo is visible although no ion assets are used.
- `npm audit` advisories on dev dependencies are untriaged.
- Legend gradient colours are hard-coded per `legend.palette`; they must match the backend PNG palette (visually plausible, not pixel-verified).
- P1 items (FE-12 compare, FE-13 mobile/glossary/Playwright) not started.
