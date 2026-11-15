# Earth Digital Twin — Trend Detective: Core Architecture

Version 0.2 · 15 Nov 2026 · Owner: Solution Architect session

This is the single source of truth for architecture decisions. Both implementation sessions (Frontend, Backend + Data) follow it. Changes go through the architect; see §9.

## 1. What we are building

A web tool that lets students and the public act as **Earth-data detectives**:

1. Choose **what** to investigate (rainfall, heat, soil water, vegetation) and **where** (a preset region or any point on the globe).
2. See the **time series** of a NASA mission/model variable for that place.
3. Get the **rate of change**, the **total change**, and whether the trend is **statistically significant** (Mann-Kendall test and t-test with confidence interval), in plain language.
4. See **where** things are changing on a 3D globe trend map, including places trending in opposite directions.

Mekong Delta farming is one guided demo walkthrough, not the product scope.

### Challenge objectives → features

| Challenge objective (NASA Space Apps 2026, Trend Detective) | Feature |
|---|---|
| Identify Earth science variables to investigate | Variable catalogue with plain definitions; guided "what" step; Guide suggestions by region type |
| Acquire the variables for a particular region | Preset regions + click any grid cell; area-weighted regional mean |
| Generate and visualise a long time series | Monthly + annual chart, 2001–2025 |
| Rate of change and significance (t-test, Mann-Kendall, CIs) | Stats card: Sen's slope + Mann-Kendall p; OLS slope + 95% CI + t-test p; total change |
| What / where / how much / significant | Global trend map (slope per decade, non-significant cells faded) |
| Audience: students/public; simple definitions; demo examples | Plain-language verdicts, glossary, 3 demo walkthroughs |
| Optional AI to suggest variables | Guide drawer: rules-based suggestions (P0), optional LLM wording (P1) |

## 2. Design principles (keep it simple)

1. **Pre-compute, then serve.** All NASA downloading happens offline in a pipeline. The API never calls NASA at request time.
2. **One data shape.** Every variable becomes one global monthly grid (`time × lat × lon`) in one Zarr store. Every feature reads that shape.
3. **Coarsen by averaging only.** Native grids are block-averaged by an integer factor to about 0.5°. No interpolation, no smoothing, no invented detail.
4. **One stats module.** The same function produces the stats card, the trend map and the Guide's evidence.
5. **Honest status.** Every result carries `dataStatus` (`source_backed | sample | unavailable`), units, period, resolution and provenance. Missing values are `null`, never 0.
6. **Stateless API, config by env vars.** Moving from laptop to GCP changes config, not code.
7. **Two codebases, one contract.** `contracts/trend-detective-api.openapi.yaml` is the only interface between Frontend and Backend.

## 3. System overview

```text
                 OFFLINE (run once, re-run to refresh)                     ONLINE (request time)

 NASA Earthdata ──► pipeline: fetch ──► coarsen ──► Zarr cube ──┐
 (GES DISC, LP DAAC)  (earthaccess)   (block-mean)  data/cube/   │
                                                                 ├──► FastAPI  ──► /api/v1/* ──► React + CesiumJS
                      pipeline: trend-maps ──► PNG + legend JSON ┘    (reads cube,     (JSON, PNG)     (globe, chart,
                                               data/maps/              stats module,                    stats card,
                                                                       SQLite sessions)                 Guide drawer)
 NASA GIBS (basemap imagery, no token) ─────────────────────────────────────────────────────────────►  Cesium basemap
```

## 4. Decisions

| # | Decision | Why | Rejected alternative |
|---|---|---|---|
| D1 | General variable × region tool; Mekong farming is a demo | Matches the challenge text | Farming-only vertical |
| D2 | Pre-ingested global monthly cube, ~0.5°, 2001–2025 | Any region in seconds; no live NASA dependency in the demo | Live Giovanni/API calls per request (slow, fragile) |
| D3 | Backend: Python 3.12, FastAPI, xarray, Zarr, SQLite — one Python project for pipeline + API | Science libraries and API share code; one toolchain | Node API + Python ETL (two toolchains for a read-only API) |
| D4 | Frontend: React + TypeScript + Vite + CesiumJS, NASA GIBS basemap | 3D globe with zero tokens for P0 | Cesium ion / Google 3D tiles (tokens, billing; not needed for science) |
| D5 | Stats on **annual values** (removes the seasonal cycle); Mann-Kendall + Sen's slope is the headline; OLS + t-test + 95% CI shown alongside | Both methods are named by the challenge; annual values are simple and reduce autocorrelation | Monthly deseasonalised regression with autocorrelation corrections (more complex; P1 option) |
| D6 | Trend maps pre-rendered as one PNG per variable, with Benjamini-Hochberg FDR to fade non-significant cells | Simple Cesium overlay; FDR avoids "1 in 20 cells significant by chance" | Vector tiles / per-cell GeoJSON (heavier) |
| D7 | Guide = rules engine (P0); optional LLM wording (P1) behind a flag | Works offline, no keys, no hallucinated numbers | LLM-first agent |
| D8 | Local first; GCP later with the same containers | Ship the demo before cloud work | Cloud-first |

## 5. Data layer

### 5.1 Variable catalogue (P0)

| Variable id | Name | Source (dataset, version) | Native → served | Native unit → served monthly unit | Annual value | Topic |
|---|---|---|---|---|---|---|
| `precipitation` | Rainfall | GPM IMERG Final monthly, `GPM_3IMERGM` V07 | 0.1° → 0.5° | mm/hr → mm/month (× hours in month) | sum, mm/year | water |
| `air_temperature` | Air temperature (2 m) | MERRA-2 `M2TMNXSLV` (T2M) | 0.5°×0.625° → native | K → °C | mean, °C | heat |
| `soil_moisture` | Topsoil moisture (0–10 cm) | GLDAS Noah `GLDAS_NOAH025_M` V2.1 (`SoilMoi0_10cm_inst`) | 0.25° → 0.5° | kg/m² → kg/m² (= mm of water) | mean | water |
| `ndvi` | Vegetation greenness (NDVI) | MODIS Terra `MOD13C2` v061 | 0.05° → 0.5° | scaled int × 0.0001 → unitless | mean | vegetation |

The backend's first task (BE-02) verifies every name, version, unit and fill value above against real files and records the result in `data/manifest.json`. **If a real file disagrees with this table, the file wins**; the backend reports the difference to the architect.

P1 candidates: GLDAS evapotranspiration and surface runoff; MODIS land surface temperature (`MOD11C3`); OMI NO₂ for a megacity demo (daily product, heavier ingest). P2: AIRS, ocean-specific variables.

### 5.2 Storage layout (local)

```text
data/                      # outside git; DATA_ROOT points here (absolute path)
  raw/<datasetId>/         # downloaded granules (may be deleted after coarsening)
  cube/<variableId>.zarr   # dims: time (monthly, first of month UTC), lat, lon; float32; NaN = missing
  maps/<variableId>.png    # global equirectangular trend map, 1 pixel = 1 cell
  maps/<variableId>.json   # legend: min, max, unit, palette, period, method, alpha
  manifest.json            # per dataset: product, version, URLs, access date, units, fill, coverage, file hashes, processing version
  sessions.sqlite          # saved sessions
```

### 5.3 Processing rules

- Missing / fill values → NaN in the cube → `null` in the API.
- Regional mean = cos(latitude)-weighted mean of cells whose **centre** falls inside the region polygon. A month with < 50 % of the region's cells valid is `null`.
- Cells that have no data in any month of the analysis period (for example sea for land-only variables) are dropped from the region before the 50 % rule and listed in caveats. A region or point left with no valid cells returns `400 data_unavailable`.
- A point request (globe click) uses the single cell containing the point (`representativeness: single_cell`).
- A year is valid only if all 12 months are valid; otherwise its annual value is `null` (stated in caveats).
- Monthly anomaly (chart only) = value − mean of the same calendar month over the analysis period.

## 6. Statistics (one module, `edt.stats`)

Input: annual values for `start..end` (default 2001 to the variable's last complete year; for rainfall this is 2024 because IMERG V07 ends in 2025-09). Minimum 10 non-null years, otherwise `insufficient_data`.

| Output | Method | Library |
|---|---|---|
| Sen's slope (per decade) | Theil-Sen median slope × 10 | `pymannkendall` |
| Mann-Kendall τ and p | Original Mann-Kendall test, two-sided | `pymannkendall.original_test` |
| OLS slope, 95% CI, t-test p, R² | Least squares; CI = slope ± t(0.975, n−2) × SE | `scipy.stats.linregress` |
| Total change | Sen's slope per year × (end − start) | — |
| Significance status | `significant` if Mann-Kendall p < α (0.05); else `not_significant` | — |
| Method agreement | `both`, `mann_kendall_only`, `ols_only`, `neither` | — |
| Trend-map mask | Mann-Kendall per cell, then Benjamini-Hochberg FDR at q = 0.05 | own 10-line function or `statsmodels` |

Plain-language interpretation is generated from templates in the backend (for example: "Rainfall in the Mekong Delta increased by about X mm/year per decade from 2001 to 2025. This trend is statistically significant (Mann-Kendall p = 0.01)."). The frontend displays it; it does not compose scientific claims.

Stated limitations (always returned as caveats where relevant): linear trend only; annual values may still be autocorrelated; trend ≠ cause; ~0.5° cells (~55 km) are not field-level.

## 7. Repository layout

```text
DigiEarth/                    # git repo (monorepo)
  _Mission/                   # these docs (v1/ = superseded plans)
  contracts/
    trend-detective-api.openapi.yaml   # THE interface; architect-owned
    CHANGE-REQUESTS.md                 # sessions propose changes here
  frontend/                   # Frontend session only
  backend/                    # Backend + Data session only
    pyproject.toml            # uv-managed, Python 3.12
    src/edt/{config.py, api/, pipeline/, stats/, regions/, guide/, sessions/}
    tests/
  data/                       # gitignored; shared absolute DATA_ROOT
```

Ports: API `8000`, frontend dev server `5173` (Vite proxies `/api` → `http://localhost:8000`, so no CORS setup is needed locally).

## 8. Configuration and third-party access

### Environment variables

| Variable | Used by | Local value | GCP value (later) |
|---|---|---|---|
| `DATA_ROOT` | backend | absolute path to `DigiEarth/data` | `gs://<bucket>/data` |
| `SESSION_STORE` | backend | `sqlite` | `firestore` |
| `ALLOWED_ORIGINS` | backend | `http://localhost:5173` | frontend URL |
| `GUIDE_LLM` | backend | `off` | `off` or provider name (P1, after approval) |
| `VITE_API_BASE` | frontend | `/api/v1` | API URL |
| `VITE_USE_FIXTURES` | frontend | `false` (`true` before backend is ready) | `false` |

Secrets live only in gitignored files (`backend/.env`, `~/.netrc`). They are **never pasted into chat** — credentials should never be shared with an AI assistant. Sessions refer to variable names only.

### What you need to acquire

| # | Item | Needed by | When | How | Where it goes |
|---|---|---|---|---|---|
| 1 | **NASA Earthdata Login** account | Backend (BE-02) | **Before the backend session starts** | Register at urs.earthdata.nasa.gov. In your profile → Applications → Authorized Apps, approve **"NASA GESDISC DATA ARCHIVE"** (GPM, MERRA-2, GLDAS). LP DAAC (MODIS) may prompt for approval on first download. | `~/.netrc` (`machine urs.earthdata.nasa.gov login … password …`, `chmod 600`) or an Earthdata token in `backend/.env` as `EARTHDATA_TOKEN` |
| 2 | `uv` (Python tool manager) | Backend | Before backend session | `brew install uv` (not installed on this Mac; system Python is 3.14, we pin 3.12) | — |
| 3 | Cesium ion token | Frontend | **Not needed for P0** (NASA GIBS basemap) | Optional later for terrain | `frontend/.env.local` |
| 4 | LLM API key | Backend Guide | **P1 only** | Optional; requires an approved provider | `backend/.env` |
| 5 | GCP project, billing, deployer service account | Deployment | **After local MVP works** | Project + billing; enable Cloud Run, Artifact Registry, Cloud Storage, Firestore, Secret Manager; deployer roles: Cloud Run Admin, Artifact Registry Writer, Storage Admin, Service Account User | gcloud auth on your machine; Secret Manager for Earthdata |
| 6 | Remote git host (optional) | Both | When you want backup/CI | GitHub/GitLab repo | — |

Already available on this Mac: git, Node 26 / npm 11, Docker, gcloud SDK, Homebrew.

## 9. Contract and coordination rules

- The contract is frozen at v0.2 for both sessions. Neither session edits it directly.
- A session that needs a change writes an entry in `contracts/CHANGE-REQUESTS.md` (what, why, breaking or not) and tells the user. The architect updates the contract and bumps the version; both sessions then rebase.
- Each session works in its own git worktree and branch and touches only its own folder (`frontend/` or `backend/`).
- Integration: after both P0 sets are done, merge both branches, run backend + frontend together, and walk the demo script in `START-HERE.md`.

## 10. Path to GCP (later; no work now)

| Local | GCP |
|---|---|
| `uvicorn` on :8000 | Cloud Run service (backend container) |
| `data/` on disk | Cloud Storage bucket (Zarr reads via `gcsfs`; PNGs served by API or bucket) |
| SQLite sessions | Firestore (swap via `SESSION_STORE`) |
| Vite dev server | Static build on Firebase Hosting or Cloud Storage + CDN |
| Pipeline on laptop | Same pipeline, run locally or as a Cloud Run Job; Earthdata credential in Secret Manager |

Rules that keep this cheap: no hard-coded paths; all I/O through `DATA_ROOT`; sessions behind a `SessionStore` interface; API holds no state in memory beyond caches.

## 11. Non-goals

Crop-yield prediction; claims about causes; future projections (P2 at most, clearly separated); field-level precision; live or near-real-time data; user accounts and multi-tenant security.
