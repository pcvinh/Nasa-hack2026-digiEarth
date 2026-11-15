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

## Fixes round (contract 0.2.1) - verified on the real backend, dataVersion 2026-11-15.1
- Default period: `endYear` is omitted; rainfall results come back as 2001-2024, other variables 2001-2025. The UI shows `period` from the result.
- `400 data_unavailable` (topsoil moisture over open ocean): the API message is shown in the panel, no cell or marker is drawn (screenshot 07).
- Legend uses the API's `colorStops` (present for all four maps).
- MERRA-2 air-temperature map: bounds start at -180.3125; overlay clamped to -180 and the legend says so (screenshot 10).
- ion logo hidden; "Imagery: NASA GIBS" stays visible bottom left.
- Basemap bug found while checking alignment: GIBS tiles from level 1 up returned 400 because Cesium's default tile grid does not match GIBS (level 0 = 2x1 tiles of 288 degrees). Fixed in `GlobeView.tsx`; before the fix the globe went black when zoomed in. The fixture-mode screenshots from the first FE-11 round did not exercise zoom.

### Alignment check (Mekong Delta, soil moisture is land-only)
Overlay cells follow the Indochina coast and the Mekong delta boundary outline sits on the delta coast of the basemap (screenshots 04, 06). Coastal cells extend over the sea by up to one cell, as expected for 0.5 degree cells. No offset found. Not pixel-measured.

### Opposite trends (real data)
Air temperature, annual Sen's slope, both Mann-Kendall significant: Sahel negative (about -0.32 C per decade), central Amazon positive (about +0.36 C per decade). Screenshots 08-10. Values are the API's; a negative air-temperature trend in the Sahel is worth a second look by the backend/science owner, but this is a display check only.

### For the Architect / Backend
1. **Point requests return a zero-size bbox** (`region.bbox = [lon, lat, lon, lat]`, e.g. `[105.3, 10.5, 105.3, 10.5]` for a click at 105.3E 10.5N) although the plan says the returned cell is drawn. The frontend therefore draws a yellow ring at the point instead of the cell outline and does not guess cell edges. Wanted: the real cell extent in `region.bbox` for `single_cell` results. Not filed as a change request because this round forbade editing `contracts/`.
2. Screenshots in `docs/screenshots/` are 1440x900, headless Chrome with software WebGL.

### Not covered
- Pixel-level alignment measurement; tablet/mobile; P1 items (compare, glossary, Playwright).
- Screenshot 13 (insufficient data) comes from fixture mode, so it shows the SAMPLE banner; the real data produced no such case.
- Screenshots 08-12 were generated but I only inspected 01-07 (partly), 10 and 13 by eye.
