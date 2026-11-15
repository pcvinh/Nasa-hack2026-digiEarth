# PLAN 2 — Backend + Data | Earth Digital Twin — Trend Detective

> **Claude Code execution brief.** Build the NASA data pipeline, the statistics module and the FastAPI service defined by `contracts/trend-detective-api.openapi.yaml` (v0.2). Work only in `backend/` (and the gitignored `data/`). Do not touch `frontend/` or `contracts/`.
>
> Read first: `_Mission/ARCHITECTURE.md` (decisions, data rules, stats method, config). This plan does not repeat them.

## 0. Goal and done-ness

Done (P0) means: for the 4 P0 variables and 5 preset regions, the API returns real NASA-derived monthly and annual series, Sen's slope + Mann-Kendall, OLS + t-test + 95% CI, a plain-language interpretation and full provenance; global trend maps exist for each variable; the Guide and sessions endpoints work; every response validates against the contract; and one regional series has been cross-checked against NASA Giovanni.

Keep it simple: one Python project, one CLI, one API process, files on disk. No queues, no databases beyond SQLite, no microservices.

## 1. Start-of-work checklist

1. Confirm with the user that the prerequisites in `ARCHITECTURE.md` §8 are in place: **Earthdata Login** (in `~/.netrc` or `backend/.env`) and **`uv`** installed. Never ask the user to paste credentials into chat; refer to them by variable/file name only. Never print or log them.
2. Work in your own git worktree/branch (e.g. `backend/p0`). Set `DATA_ROOT` to the **absolute** path of the shared `DigiEarth/data` folder (not inside the worktree), so downloads survive worktree cleanup.
3. Keep `backend/BACKEND_PROGRESS.md`: completed packages, verified dataset facts, deviations, blockers. Commit after each package that passes its check.
4. If something in the contract is wrong or missing, add an entry to `contracts/CHANGE-REQUESTS.md` and tell the user. Do not edit the contract.

## 2. Stack

| Concern | Choice |
|---|---|
| Python | 3.12, managed by `uv` (`uv init`, `uv add`, `uv run`) |
| API | FastAPI + Uvicorn, Pydantic v2 models that mirror the contract |
| Arrays | xarray, numpy, zarr, netCDF4 / h5netcdf (GPM, GLDAS, MERRA-2), pyhdf (MODIS HDF4) |
| NASA access | `earthaccess` (search + download with Earthdata Login) |
| Stats | scipy, pymannkendall (statsmodels optional for FDR cross-check) |
| Geometry | shapely (point-in-polygon for cell centres) |
| Images | matplotlib colormaps + Pillow (write PNG) |
| Sessions | sqlite3 (standard library) |
| Quality | pytest, ruff, `openapi-core` (validate responses against the contract file) |

## 3. Code layout

```text
backend/
  pyproject.toml
  .env.example             # DATA_ROOT, SESSION_STORE=sqlite, ALLOWED_ORIGINS, GUIDE_LLM=off, EARTHDATA_TOKEN= (optional)
  src/edt/
    config.py              # reads env vars once
    catalogue.py           # variable definitions (single source: catalogue.yaml)
    catalogue.yaml         # 4 P0 variables: ids, names, plain definitions, units, datasets, coarsen factor
    pipeline/
      cli.py               # `uv run edt <command>`
      fetch.py             # earthaccess search/download per month
      readers.py           # one reader per dataset → xarray DataArray (lat, lon), native units
      coarsen.py           # integer block-mean, ≥50% valid sub-cells rule
      cube.py              # append month to data/cube/<var>.zarr
      maps.py              # per-cell trend → PNG + legend JSON
      manifest.py
    stats/
      core.py              # annual aggregation, trend_stats(), interpret()
      grid.py              # vectorised Mann-Kendall + Sen's slope, Benjamini-Hochberg
    regions/
      presets.geojson      # 5 preset regions with properties (id, name, type, source, suggested vars)
      select.py            # cells for preset / bbox / point; cos(lat)-weighted mean
    guide/
      rules.yaml           # region type → variables; keywords → variables; unsupported asks
      engine.py
    sessions/
      store.py             # SessionStore interface + SqliteSessionStore
    api/
      app.py               # FastAPI app, CORS, error handler → contract Error shape
      routes/{health,variables,regions,trends,trend_maps,guide,sessions}.py
      models.py            # Pydantic models matching the contract
  tests/
    golden/                # committed JSON results for demo regions
```

## 4. Pipeline

### CLI

```bash
uv run edt spike --variable precipitation --month 2020-07     # download 1 month, print vars/units/fill/shape, delete nothing
uv run edt ingest --variable precipitation --start 2001 --end 2025
uv run edt maps --variable precipitation
uv run edt manifest
uv run edt golden                                               # regenerate tests/golden/*.json
```

`ingest` processes **one month at a time**: download → read → convert units → coarsen → append to Zarr → delete the raw file (unless `--keep-raw`). It is resumable: months already in the cube are skipped. Use at most 4 parallel downloads. Run the full 25-year backfill only after the spike for that variable passes.

### Dataset notes to verify in the spike (BE-02)

| Variable | Check |
|---|---|
| `precipitation` (GPM_3IMERGM V07) | HDF5 group `Grid`, variable `precipitation`, unit mm/hr; grid is stored **lon × lat** — transpose and confirm orientation (e.g. July monsoon rainfall over South Asia should appear in the right place). Convert with hours in that month (Feb 2024 = 696 h). |
| `air_temperature` (M2TMNXSLV) | Variable `T2M` in K; grid 576 × 361 at 0.625° × 0.5°; keep native grid. |
| `soil_moisture` (GLDAS_NOAH025_M V2.1) | Variable `SoilMoi0_10cm_inst`, kg/m²; latitude starts at about -60°; land only. Coarsen factor 2. |
| `ndvi` (MOD13C2 v061) | HDF4 SDS "CMG 0.05 Deg Monthly NDVI"; scale 0.0001; fill −3000; coarsen factor 10. If HDF4 reading fails on macOS arm64 after 1 hour of effort, mark NDVI `unavailable` and move on; tell the user. |

Record for each: dataset id, version, URL, access date, variable name, native unit, fill value, grid shape, first/last available month, file size, download time per month. Update `catalogue.yaml` from facts, not from this table. Report any difference from `ARCHITECTURE.md` §5.1 to the user.

### Trend maps (`edt maps`)

1. Build annual values per cell for the default period (2001–2025); cells with any null year are left transparent.
2. Vectorised Mann-Kendall S, variance (no-ties formula is fine for continuous data), two-sided p; Sen's slope = median of pairwise slopes. Verify against `pymannkendall` on 200 random cells in a test.
3. Benjamini-Hochberg across all valid cells at q = 0.05.
4. Colour: symmetric limits at ±98th percentile of |slope per decade|; palette `BrBG` for water/vegetation, `RdBu_r` for temperature; significant cells alpha 0.9, not significant 0.35.
5. Write `maps/<var>.png` (one pixel per cell, north-up, west edge −180) and `maps/<var>.json` (contract `TrendMap` fields).

## 5. Regions

Five P0 presets in `presets.geojson` (properties: `id, name, country, regionType, description, geometrySource, suggestedVariableIds`):

| id | Type | Boundary source (record licence + date) |
|---|---|---|
| `mekong-delta` | river_delta | Union of the Mekong Delta provinces of Vietnam from geoBoundaries ADM1 (CC BY 4.0). Note: Vietnam merged provinces in 2025 — record which boundary edition is used. |
| `central-java` | agricultural | geoBoundaries ADM1, Indonesia |
| `johor` | agricultural | geoBoundaries ADM1, Malaysia |
| `amazon-central` | rainforest | Documented simplified polygon (state the coordinates and rationale in `geometrySource`) |
| `sahel` | desert_edge | Documented simplified band (e.g. latitude/longitude limits stated in `geometrySource`) |

Simplify polygons to < 500 vertices. Cell selection: cells whose centre falls inside the polygon; if none (very small region), use the cell containing the region centre and say so in caveats. Expose `cellCount` in every result.

## 6. API behaviour

- `GET /variables`, `/regions`, `/regions/{id}`: from `catalogue.yaml`, `presets.geojson` and cube availability. A variable with no cube → `status: unavailable` + reason.
- `POST /trends/analyze`: validate exactly one of `presetId | bbox | point`; years within coverage; `400 invalid_input` otherwise, `400 data_unavailable` if the cube is missing. Load only the needed lat/lon slice (lazy Zarr). Return everything in `TrendResult`, including `trendLines` and `dataVersion`. Cache results in memory by request + `dataVersion`.
- Interpretation templates (in `stats/core.py`): headline + summary + caveats. Use "increased/decreased/no clear change", the variable's own units, rounded sensibly (2 significant figures for slopes). When not significant, say so plainly and add: "A trend can become significant with a longer record." Never mention causes or yields.
- `GET /trend-maps/{id}` and `/image.png`: serve files from `maps/`.
- `POST /guide/chat` (rules mode): detect region type from `regionId`, topic/variable from keywords in `rules.yaml`; return 1–3 suggestions with reasons and whitelisted actions only. For questions about crop yield, causes, forecasts or the future, reply that the tool cannot answer that and suggest what it can show. The Guide never returns statistics; the frontend gets numbers only from `/trends/analyze`.
- `/sessions`: SQLite; ids are random URL-safe strings; reject `state` larger than 256 KB.
- Errors always use the contract `Error` shape. CORS allows `ALLOWED_ORIGINS` only.

## 7. Work packages (in order)

| # | Pri | Package | Done when |
|---|---|---|---|
| BE-01 | P0 | Scaffold: uv project, FastAPI app, config, `/health`, ruff, pytest, contract-validation test helper, `.env.example`, `.gitignore` | `uv run uvicorn edt.api.app:app --port 8000` serves `/api/v1/health`; tests pass |
| BE-02 | P0 | **Data spike** for all 4 datasets (needs Earthdata Login) | Dataset facts recorded in `BACKEND_PROGRESS.md` + `catalogue.yaml`; differences reported to user |
| BE-03 | P0 | Stats module + tests (can run while BE-02 downloads) | Tests in §8 pass |
| BE-04 | P0 | Ingest precipitation 2001–2025 → Zarr; then air_temperature, soil_moisture, ndvi | Cubes complete; manifest written; spot-check values plausible |
| BE-05 | P0 | Regions + `/variables` + `/regions` | Contract-valid; Mekong cellCount reported |
| BE-06 | P0 | `/trends/analyze` | Contract-valid for all presets × variables; **tell the user: frontend can integrate now** |
| BE-07 | P0 | Trend maps + endpoints | PNGs look geographically right (coastlines line up when overlaid) |
| BE-08 | P0 | Guide rules engine + `/guide/chat` | Suggestions for each region type; unsupported asks refused |
| BE-09 | P0 | Sessions | Create/get/list/update round-trip |
| BE-10 | P0 | Validation + golden + handoff | Giovanni cross-check done; `tests/golden/` written; `BACKEND_HANDOFF.md` |
| BE-11 | P1 | More variables (GLDAS evapotranspiration/runoff, MODIS LST; OMI NO₂ + Jakarta preset) | Same checks as P0 variables |
| BE-12 | P1 | Optional LLM wording for the Guide (only with an approved provider and a user-supplied key in `backend/.env`) | LLM only rephrases rules output; suggestions/actions unchanged |
| BE-13 | P1 | Dockerfile for the API (GCP prep) | `docker run` serves the API with `DATA_ROOT` mounted |

**Giovanni cross-check (BE-10):** with the same bounding box as the Mekong preset's `bbox`, download Giovanni's area-averaged monthly IMERG time series (2001–2025) and compare with our `/trends/analyze` result for that `bbox`. Report correlation and mean difference in the handoff. Expect small differences (coarsening, cell selection); large ones are a bug.

## 8. Tests (pytest)

- Unit conversion: IMERG mm/hr → mm/month, including leap-year February; K → °C; NDVI scale and fill.
- Coarsening: known block means; < 50 % valid sub-cells → NaN.
- Orientation: lat descending/ascending handled; lon −180..180; IMERG transpose.
- Regional mean: cos(lat) weighting on a synthetic grid; centre-in-polygon selection; tiny region fallback.
- Annual aggregation: sum vs mean per variable; year with a missing month → null.
- Stats: synthetic series with known slope + fixed-seed noise → Sen's slope within tolerance and significant; flat fixed-seed noise → not significant; n < 10 → `insufficient_data`; OLS CI contains true slope; agreement field.
- Grid stats: vectorised Mann-Kendall/Sen equals `pymannkendall` on sampled cells; BH matches a reference implementation.
- API: every endpoint's success and error responses validate against the contract file; exactly-one-of region rule; unknown variable → 400; missing cube → `data_unavailable`.
- Guide: each region type gets suggestions; "predict rice yield" is refused; actions are only whitelisted types.
- Golden: re-running analysis reproduces `tests/golden/*.json` for the same `dataVersion`.

## 9. Handoff (`backend/BACKEND_HANDOFF.md`)

Run commands; enabled variables and regions; dataset facts table (id, version, units, coverage, resolution, access date); processing steps; Giovanni cross-check result; known limitations; open change requests; disk space and time the full ingest took.

## 10. Prompt for the Backend + Data session

> You are the Backend + Data implementation agent for Earth Digital Twin — Trend Detective. Read `_Mission/ARCHITECTURE.md`, `_Mission/PLAN-2-Backend-Data.md` and `contracts/trend-detective-api.openapi.yaml`. Work only in `backend/` on your own branch/worktree, with `DATA_ROOT` set to the shared absolute `data/` folder. First confirm the Earthdata Login and `uv` prerequisites with the user (never ask for credential values in chat). Do BE-01, then the BE-02 data spike, reporting real dataset facts before backfilling. Implement P0 packages in order, keep it simple (one Python project, files on disk, SQLite), validate every response against the contract, and never fabricate or smooth data. Tell the user when BE-06 is ready for frontend integration. Finish with tests passing and `BACKEND_HANDOFF.md`.
