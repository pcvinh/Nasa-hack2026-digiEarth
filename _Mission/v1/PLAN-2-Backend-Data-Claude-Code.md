# PLAN 2 — Backend + NASA Data Implementation | Earth Digital Twin Farming MVP

> **Claude Code execution brief.** Build the source-backed data ingestion, canonical analysis store, statistics, GeoJSON serving, evidence-grounded Farming Agent and REST APIs. Do NOT build or modify the React/Cesium frontend in this workstream.
>
> **Top priority:** deliver reproducible, actual NASA-derived data for the Mekong Delta, first via NASA POWER and at least one challenge-named dataset such as **GPM / IMERG**; then add MODIS NDVI and GLDAS if acquisition succeeds. Do not make the demo dependent on all four being available.

## 0. Mission / success criteria

**First region:** Mekong Delta, Vietnam — a documented geographic AOI (Polygon/MultiPolygon). A manually chosen centroid can be used as a **point sample** in initial ingestion, never misrepresented as the entire region's average. Southeast Asia expansion (Johor, Central Java) is structurally supported, but real records are required to mark places as enabled.

**Product outcome:** Return authentic, source-attributed historical rainfall/temperature indicators; compute historical variability, rate of change and statistical significance; add a spatial representation with correct source resolution; power a causal-*hypothesis* explanation agent; optionally return climate scenario projections for the future. The backend returns insights rather than raw scientific format.

**NASA Space Apps alignment:** The official 2026 "Be An Earth System Trend Detective!" challenge focuses on chosen Earth science variables, geographic change, trends and significance. Named relevant sources include GPM, MODIS, GLDAS and MERRA-2. **Check the exact official Resources tab for submission requirements** and cite all sources in the project. NASA POWER is an excellent accessible adapter but does not by itself replace validation of an official Resources-tab dataset.

**Non-goals:** accurate crop-yield prediction; commodity trading signal; causal proof from simple correlation; 100-m risk map from 25–50-km climate input; real-time weather forecast; complete Southeast Asia ingestion; multi-tenant production IAM.

## 1. Start-of-work protocol (Claude Code)

1. Inspect the repository/workspace and any existing API/data code. Do not overwrite existing user's modules. Work in your **Backend/Data mission worktree** and keep `apps/web` untouched.
2. Import `earth-digital-twin-mvp-api.openapi.yaml` as the cross-team contract. Keep endpoint shape, ids (`mekong-delta`) and metric keys exactly aligned with Frontend.
3. Verify Earthdata Login availability securely (environment variables or token), NASA POWER access, and which datasets can actually be downloaded. Do not log credentials, NASA auth tokens or proprietary keys.
4. Prefer an **offline/cached ingest + fast local API**. No browser request should block on a new 20-year NASA download. NASA API failures must not erase previously verified snapshots.
5. Track completed tasks and actual dataset source/version/date/coverage in `BACKEND_PROGRESS.md`. Record any scientific limitations explicitly.
6. Run a minimal NASA real-data spike BEFORE designing complex pipelines. Fallback to NASA POWER + one successfully verified challenge-named source if time-constrained; show missing sources as unavailable.

## 2. Recommended architecture

```
NASA POWER -----------+                                    +--> REST /api/v1/places/...
NASA GPM IMERG -------+--> Python extract/normalize -------+--> time-series / trends
MODIS NDVI (P1) ------+          |                         +--> GeoJSON / grid layers
GLDAS (P1) ----------+          v                         +--> future projections
NASA POWER SSP (P2) -+     Raw files + manifest           +--> evidence pack
                                |                                     |
                                v                                     v
                      Parquet/JSON + GeoJSON                  Node/Fastify API
                      local cache (MVP)                      + deterministic Agent
                                |                                     |
                          optional GCS/BQ                             v
                                                                 React/Cesium
```

**Implementation choice:** Node.js 20+/TypeScript + Fastify + Zod/OpenAPI for API; Python 3.11+ for scientific ETL (`earthaccess`, `xarray`, `h5py`, `rioxarray`, `rasterio`, `pandas`, `numpy`, `scipy`, `geopandas`, `pyarrow` as needed). For MVP, store results as **versioned JSON/Parquet + GeoJSON** on local disk and analysis sessions in SQLite. GCS + BigQuery GIS are deployment adapters, not requirements to show a working demo. Avoid starting with an entire microservice platform.

Example layout:

```
apps/api/
  src/{server.ts,app.ts,config.ts}
  src/routes/{health.ts,places.ts,catalog.ts,overview.ts,timeseries.ts,spatial.ts,projections.ts,farmingAgent.ts,analyses.ts}
  src/services/{dataRepository.ts,trendService.ts,evidenceService.ts,agentService.ts,sessionService.ts}
  src/contracts/{apiSchemas.ts}
  tests/
pipeline/
  requirements.txt
  src/edt_pipeline/{cli.py,registry.py,fetch_power.py,fetch_gpm.py,fetch_modis.py,fetch_gldas.py,normalize.py,spatial.py,statistics.py,projections.py,provenance.py,export.py}
  tests/
  manifests/sources.yaml
  areas/mekong_delta.geojson
  README.md
data/
  raw/           # ignored by git
  processed/     # versioned demo outputs/manifests
  fixtures/      # explicitly marked TEST/SAMPLE only
contracts/earth-digital-twin-mvp-api.openapi.yaml
```

## 3. Science and data-source priorities

| Priority | Dataset | Adapter | First variables / expected output | Caveats |
|---|---|---|---|---|
| P0a | NASA POWER monthly historical | HTTPS REST JSON/CSV | `T2M`, `PRECTOTCORR`; month-value time series | Source/coverage and unit metadata required; point not region |
| P0b | NASA GPM IMERG monthly `GPM_3IMERGM`, current available version | Earthdata/GES DISC or Giovanni verified export | Region-relevant precipitation monthly grid/time series | Inspect unit (often precipitation rate), product/quality and conversion |
| P1a | MODIS MOD13Q1 v061 | AppEEARS area/point extraction, or equivalent NASA-authorized mechanism | NDVI/EVI and pixel QA over AOI | Raw NDVI scaling factor 0.0001, cloud/QA mask |
| P1b | GLDAS `GLDAS_NOAH025_M` V2.1 | Earthdata/GES DISC | Soil-water and/or evapotranspiration monthly series | Check variable names, units and model status |
| P2a | POWER NEX-GDDP-CMIP6 projection API | HTTPS REST | `T2M`, `PRECTOTCORR`, 2030–2050, SSP scenarios | 0.25° grid, conditional projection, not a crop/yield forecast |
| P2b | MERRA-2 `M2TMNXSLV` | Earthdata / Giovanni | Temperature/humidity historical corroboration | More advanced download/processing |

**Immediate dependency-free real-data source:** `https://power.larc.nasa.gov/api/temporal/monthly/point` with `parameters=T2M,PRECTOTCORR`, `community=AG`, point lon/lat, `start=2001`, `end=2025`, `format=JSON`. Verify returned time series and parameter units; the monthly historical meteorology archive may lag the current year.

**Projection source:** `https://power.larc.nasa.gov/api/projection/monthly/point` with `parameters=T2M,PRECTOTCORR`, `community=AG`, lon/lat, `start=203001`, `end=205012`, `scenario=ssp245`, `time-standard=UTC`, `format=JSON`. Validate actual current response: nested `parameter -> scenario -> YYYYMM`, missing sentinel `-999`; other scenarios `ssp126` / `ssp370` supported. Never join projected and historical years as one observed series.

**GPM ingestion reality:** Query exact CMR short name / product version and download using Earthdata login or successful subset tool. Inspect granule metadata for unit/scale/fill values. Clip the scientific grid to AOI and compute an area-weighted aggregate (or document approximation). Convert `mm/hr` rates to monthly totals only after checking actual source units and month duration. Maintain separate `point_sample` / `area_mean` labels.

**MODIS ingestion reality:** If source yields scaled integer NDVI, apply documented `0.0001` factor, QA cloud and invalid flags; compute monthly composite from 16-day observations with explicit aggregation rule. NDVI describes greenness, not necessarily crop yield. If authentication/time blocks this adapter, display it as unavailable, not synthetic production truth.

**AOI requirement:** Build `areas/mekong_delta.geojson` from an authoritative or documented public administrative/environmental boundary. Cite origin, licence and date. Mekong Delta is a *region*, not a single standard polygon; record the chosen definition and handle relevant administrative changes. Do not silently treat a wide rectangle as the Mekong Delta or turn sampled points into a region average.

## 4. Canonical logical data schema and quality

Store full source files + metadata (raw layer); output normalized observations and derived intelligence (analytical layer). Logical observation fields:

```
observation_id, place_id, geometry_id, geometry_type, lon, lat,
metric_id, value, canonical_unit, time_start_utc, time_end_utc,
source_dataset, source_product_version, source_url, retrieval_time,
spatial_resolution, temporal_resolution, representativeness,
aggregation_method, quality_flag, is_missing, is_derived,
processing_version, data_status, scenario_id, model_id, uncertainty
```

Canonical metric keys agreed with FE:
- `precipitation_mm` — monthly total in millimeters (ONLY if scientifically calculated from native data; otherwise adapt unit/key to contract via coordinated change).
- `temperature_c` — 2-m air temperature °C (not land-surface temperature).
- `soil_moisture` — value + explicit native/canonical unit (unit varies by model layer).
- `ndvi` — unitless, properly scaled, clear QA.

All time series use `YYYY-MM` with no fabricated monthly points. Missing values (`-999`, NaN, fill values) become `null` and carry quality flags. For area mean, preserve valid pixel count and coverage fraction, source native resolution and resampling choices.

**Dataset manifest** contains `{datasetId, officialProduct, version, sourceUrl, accessDate, originalUnit, variables, temporalCoverage, spatialCoverage, nativeResolution, transformation, fileHash, processingVersion, licence, caveats}`.

**Avoid false precision:** GPM ~0.1° and POWER grid point samples are not parcel-level facts. For P0, map a true grid/area aggregation or sample markers on Cesium; if only place-level means exist, render boundary coloring/label only, not high-resolution simulated heatmap.

## 5. Trend / anomaly analysis design

The 2026 challenge explicitly asks what is changing, where, by how much and whether statistically significant. Therefore statistical output is **P0**, not a later ML feature.

### Historical preprocessing

1. Normalize measured period, units, missing flags and geometry.
2. Choose a declared historical interval long enough for meaningful trend tests (e.g., 2001–2025 if source availability permits).
3. For temperature: compute monthly anomaly relative to month-of-year baseline (e.g., 2001–2020, or a valid documented subset).
4. For monthly precipitation: use month-specific baselines; distinguish total mm/month from rate; report changes in mm/year or %/decade only if well-defined.
5. For NDVI: apply QA, month-of-year baseline; note land-cover/seasonal cropping confounders.
6. Test trend on annual summaries or deseasonalized monthly anomalies. Explicitly record method and limitations.

### P0 trend method and significance

- Start with least-squares trend on annual values or monthly deseasonalized anomalies. Report slope with correct unit (e.g., °C/decade, mm/decade), method, sample count, p-value, alpha=0.05 and period.
- Because autocorrelation / irregular sampling can invalidate naive p-values, use annual aggregates for initial MVP when possible, or a documented autocorrelation-aware approach such as HAC/Newey-West. If scientifically adequate significance cannot be calculated, mark `not_computed` or `insufficient_data` rather than claim certainty.
- Correlation between rainfall, soil moisture and NDVI is association, not proven causal attribution. Report lag, overlap period and limitations; don't claim generalizable predictive accuracy.
- For P0, an explicitly exploratory agriculture watchlist is acceptable; DO NOT invent an objective farm opportunity risk probability or yield forecast.

Output standardized `Trend` and `Insight` structures from the OpenAPI contract with `evidenceIds`, source URLs and caveats.

### P2 projection method

Use the POWER projection API to return values per scenario. Do not derive unprovided confidence intervals or pretend the multi-model ensemble's average is a probabilistic confidence bound. If model quantiles are available and computed, report their precise definition; otherwise omit `lower/upper` and show "ensemble estimate / scenario range" separately. Distinguish climate 2030–2050 conditions from projected agriculture outcomes.

## 6. Backend API routes (contract locked)

Build exactly the endpoints in shared `earth-digital-twin-mvp-api.openapi.yaml`:

```
GET   /api/v1/health
GET   /api/v1/places?q=...
GET   /api/v1/places/:placeId
GET   /api/v1/catalog/layers?placeId=...
GET   /api/v1/places/:placeId/overview?asOf=YYYY-MM
GET   /api/v1/places/:placeId/timeseries?metric=...&start=...&end=...&mode=observed|anomaly
GET   /api/v1/places/:placeId/spatial?metric=...&period=YYYY-MM&mode=observed|anomaly|trend
GET   /api/v1/places/:placeId/projections?metric=...&scenario=ssp245&start=2030&end=2050
POST  /api/v1/agent/farming/chat
GET   /api/v1/analyses
POST  /api/v1/analyses
GET   /api/v1/analyses/:analysisId
PUT   /api/v1/analyses/:analysisId
```

Data classes:
- `source_backed`: actual source processed, NOT a validated causal/prediction claim.
- `sample`: fixtures only, clearly identified for UI developers.
- `unavailable`: data not connected or no coverage; return honest error/empty response and reason.

Explicitly return source product, retrieval date, spatial/temporal resolution and method. For map API, return actual GeoJSON FeatureCollection with per-feature metric, measurement/period, quality and source resolution. Reject unsupported metric/region/year requests with descriptive 400/404, not silent defaults.

**API engineering:** Zod input/output validation, CORS restricted to local frontend origin, rate limiting for chat, no NASA API keys or LLM keys in browser, simple health/source readiness endpoint, query result cache by `place+metric+time+mode+processingVersion`. Maintain OpenAPI contract tests.

## 7. Farming Agent — evidence before language

Implement deterministic grounded explanation first, optional LLM second. No agent should independently fetch and fabricate scientific values.

1. Parse user request into supported intent: summarize change, compare metrics, explain anomaly, show data limitations, compare future scenario.
2. Retrieve typed evidence: `timeseries`, `trend`, `insight`, `sourceProvenance` and current `placeId`/year.
3. Build an **evidence pack** with real measures, caveats and available sources. If user asks for yield or causal attribution, respond with "not supported by current evidence" and state what would be needed.
4. Generate a template-based response that names only available metrics; optional LLM summarization with strict grounding and validation.
5. Emit safe, whitelisted frontend actions: `show_layer`, `focus_place`, `open_chart`, `set_year`. No arbitrary tool call or mutation.
6. Return `answerType`, `confidenceLabel` (evidence support, not numeric certainty), `evidence[]`, `caveats[]`, `actions[]`.

Example user question: **"What changed in the Mekong Delta's farming environment between 2001 and 2025?"** Agent should cite actual computed rainfall/temperature/NDVI results or explicitly say which series are missing. No claim that lower NDVI equals lower rice yield without crop and ground-truth data.

## 8. Save and restore MVP sessions

Implement SQLite `analyses` table with `id`, `title`, `place_id`, `year`, `mode`, `scenario`, `enabled_layers_json`, `ui_state_json`, `messages_json`, `created_at`, `updated_at`. This is a single-user development prototype, not secure multi-tenant SaaS. Validate payload size, limit chat messages and sanitize display text on frontend. No auth claims.

If time constrained, persist analysis sessions in a local JSON store with atomic writes, clearly label backend persistence as development-only and provide migration notes to SQLite/GCP.

## 9. Ingestion CLI and reproducibility

CLI design (implement actual working equivalents):

```
python -m edt_pipeline.cli discover --place mekong-delta
python -m edt_pipeline.cli ingest --source power --place mekong-delta --start 2001 --end 2025
python -m edt_pipeline.cli ingest --source gpm --place mekong-delta --start 2001 --end 2025
python -m edt_pipeline.cli derive --place mekong-delta --metrics temperature_c,precipitation_mm
python -m edt_pipeline.cli export --place mekong-delta --format api-cache
```

Provide a manifest of which commands actually ran successfully. Include checksums and rerun/cache behavior. Do not introduce parallel massive downloads that risk timeout/quota; fetch small date slices first, verify variables and units, then backfill.

Separate:
- `data/raw/<dataset>/<version>` original downloaded items
- `data/processed/<processing_version>` normalized Parquet/JSON and GeoJSON
- `data/processed/<processing_version>/manifest.json` provenance/coverage/QA
- `data/fixtures/` test-only sample fixtures; never pass samples off as source-backed.

Run backend against frozen, processed results for deterministic demo. Refresh via CLI, not on every API request.

## 10. Work packages (dependency-ordered)

| Stage | Priority | Work package | Acceptance check |
|---|---|---|---|
| BE-01 | P0 | Repo inspection, API startup, OpenAPI validation, health | `npm run dev` responds and tests pass |
| BE-02 | P0 | AOI source and NASA POWER real-data spike | real response saved with metadata/units, clearly point-sampled |
| BE-03 | P0 | Source registry, raw store, normalized metric table | manifest reproducible; fill values handled |
| BE-04 | P0 | Historical trend/anomaly/scientific tests | slopes, p-values/status and units validated by tests |
| BE-05 | P0 | Places/layers/overview/timeseries APIs | response validates against contract |
| BE-06 | P0 | Official challenge source proof: GPM real dataset | at least one actual GPM series/spatial sample with NASA provenance |
| BE-07 | P0 | Spatial GeoJSON API + correct representativeness | FE can render only measured/aggregated geography |
| BE-08 | P0 | Farming deterministic evidence agent | no hallucinated values, actions validated |
| BE-09 | P0 | Save/reopen analysis session API | create/get/update/list success |
| BE-10 | P1 | MODIS NDVI + QA, optional GLDAS | proper units, source-backed seasonal series |
| BE-11 | P2 | NASA POWER projection scenarios | projection labeled and historically separated |
| BE-12 | P2 | GCS/BigQuery adapter + multi-region enrollment | only if core MVP reliable |

**Recommended minimum viable cut if deadline-critical:** BE-01 to BE-09, but keep actual GPM acquisition as explicit priority and do not substitute a fabricated rainfall surface. If GPM download fails, ship real POWER data with an honest "official challenge dataset still pending" caveat and investigate alternate verified Resources-tab source before submission.

## 11. Tests / scientific quality gates

**Python tests (pytest):**
- POWER JSON parser handles date keys, units, missing `-999` and data gaps; source status from successful fetch only.
- GPM and MODIS parsers (if enabled) respect units, scale factors and QA.
- Monthly/annual aggregation tests ensure totals vs averages not confused, leap year counts right, irregular gaps correctly handled.
- AOI longitude/latitude, polygon validity and area-weighted aggregation test; point samples distinguished from area means.
- Trend slope on synthetic known-slope *test fixtures*, zero/short/missing datasets; significant vs insufficient status; autocorrelation limitation documented.
- Multiple-source data alignment and time windows (never combine incomparable observation intervals blindly).
- Projection scenario/missing-value parser; no false probability interval.

**API tests (Vitest/Supertest/Fastify inject):**
- Contract shape, invalid input, 404, dates, enum validation, request cache, status and provenance fields.
- `/spatial` includes only geographic features corresponding to observed/native-cell or real aggregated values.
- Agent refuses unsupported "predict rice yield" claim and includes sources/caveats for trend answer.
- Session CRUD restores selected layer/time/messages.
- `/health` accurately lists source readiness; never reports connected before data exists.

**Manual NASA reproducibility evidence:** one authentic source request/response, manifest, derived annual/monthly series, slope calculation run, then API response. Store a copy of source URLs and processing commands for presentation/citation. Do not commit Earthdata credentials or oversized raw files.

## 12. Local run / integration / deployment

- `apps/api/.env.example`: `PORT=8080`, `WEB_ORIGIN=http://localhost:5173`, `DATA_ROOT=../../data/processed`, `ANALYSES_DB=../../data/sessions.sqlite`, `NASA_EARTHDATA_TOKEN=` (optional, secret), `OPENAI_API_KEY=` (optional, secret), `DATA_MODE=source_backed`.
- `pipeline/.env.example`: Earthdata authentication environment; no credentials committed.
- `npm run dev` for API; `python -m edt_pipeline.cli ...` for ETL.
- Full demo should work offline after one successful real-data ingestion by loading immutable processed outputs; if a source wasn't acquired, state unavailable.
- Optional production: GCS bucket for raw/processed files, BigQuery monthly observations and area aggregates, Cloud Run API and job-based ingestion. Treat deployments/permissions as later stage.

## 13. Backend completion handoff

Deliver:
- Functional API with exact OpenAPI-aligned response schemas and tests.
- One real NASA POWER historical series and one successfully ingested challenge-named source with provenance (target GPM).
- Reproducible ingest/derive/export commands and manifest/quality caveats.
- Evidence-grounded agent and persisted sessions.
- `BACKEND_HANDOFF.md` containing enabled places, enabled metrics, spatial method, available history, actual status of each NASA dataset and API examples.
- Screenshots/JSON transcript of real data flow if convenient; never fill omitted sources with unlabeled sample data.

### Definition of Done — integration evidence

FrontEnd can select Mekong, request historical rainfall/temperature, show time series and trend+significance, render source-backed geography in the globe, ask an evidence-based Farming question and restore a saved analysis. The source version, native spatial resolution, transformation method and uncertainty/limitations are inspectable in UI. Backend tests pass and one complete NASA -> raw -> normalized -> trend -> REST pipeline is demonstrably reproducible.

## 14. Claude Code prompt to execute this plan

> You are the Backend/Data implementation agent for Earth Digital Twin Farming MVP. Read this plan and the shared OpenAPI YAML. First inspect the repo and verify NASA source accessibility. Work exclusively in your backend/data worktree. Prioritize acquiring authentic NASA data, a reproducible pipeline, correct units/spatial representation, valid trend and significance calculations, typed REST endpoints, and a deterministic evidence-grounded Farming Agent. Implement P0 end-to-end before P1/P2. Do not fabricate measurements, smooth coarse data into false high-resolution science, assert causality, or mislabel conditional climate projections as forecasts of farm yield. Run automated tests, demonstrate one real NASA input through a rendered API response, and produce a concise source/coverage/limitations handoff.

## 15. Verified references

- NASA 2026 Trend Detective challenge: https://www.spaceappschallenge.org/2026/challenges/earth-system-trend-detective/
- NASA POWER monthly historical API: https://power.larc.nasa.gov/docs/services/api/temporal/monthly/
- NASA POWER projection API: https://power.larc.nasa.gov/docs/services/api/projection/
- NASA GPM: https://gpm.nasa.gov/data/directory
- NASA GES DISC: https://disc.gsfc.nasa.gov/
- NASA Earthdata Search: https://search.earthdata.nasa.gov/
- NASA AppEEARS: https://appeears.earthdatacloud.nasa.gov/
- MOD13Q1 scale/QA reference: https://developers.google.com/earth-engine/datasets/catalog/MODIS_061_MOD13Q1/
- NASA GLDAS: https://ldas.gsfc.nasa.gov/gldas/dataset
