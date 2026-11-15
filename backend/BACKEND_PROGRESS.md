# Backend progress

Branch `backend/p0` (worktree `DigiEarth-backend`). `DATA_ROOT=/path/to/DigiEarth/data`.

## Packages

| Package | Status | Evidence |
|---|---|---|
| BE-01 scaffold | done | uvicorn serves `/api/v1/health`; tests pass |
| BE-02 data spike | done | `uv run edt spike --variable all --month 2020-07` output below; all 4 downloads OK |
| BE-03 stats | done | `tests/test_stats.py` (MK/Sen vs pymannkendall, BH vs statsmodels, CI contains slope) |
| BE-04 ingest | done | 4 cubes complete (1,197 months ingested; precipitation 2025-10..12 have no source); `data/manifest.json` dataVersion 2026-11-15.1 |
| BE-05 regions + catalogue | done | 5 presets (<500 vertices); Mekong cellCount 13 (0.5°); contract-valid |
| BE-06 /trends/analyze | done | contract-valid for all 5 presets × 4 variables (golden test); Mekong rainfall +121 mm/yr per decade, MK p = 0.011 |
| BE-07 trend maps | done | 4 PNG + JSON; inspected visually (continents/north-up correct) |
| BE-08 Guide | done | suggestions for every region type; yield/forecast/cause refused; whitelisted actions only |
| BE-09 sessions | done | create/get/list/update round-trip; >256 KB rejected |
| BE-10 validation + golden + handoff | done | Giovanni area-averaged CSV vs ours (Mekong bbox): r = 0.9993, mean diff −5.0 mm/month (−2.9%); Sen +117 vs +108 mm/yr per decade; MK p 0.045 vs 0.056 (borderline). Native IMERG check identical. 20 golden files; `BACKEND_HANDOFF.md` |

Tests: 92 passed (`DATA_ROOT` set), ruff clean.

## Review fixes (branch `backend/fixes`, from main a4209c7, contract v0.2.1)

| # | Fix | Status | Evidence |
|---|---|---|---|
| 1 | Default `endYear` = last complete year (rainfall 2024) | done | `test_analyze_preset_recovers_trend_and_validates`, `test_default_end_year_*`, `test_explicit_end_year_still_works_*` |
| 2 | No valid cells → `400 data_unavailable` | done | synthetic tests + real-data ocean tests (NDVI [0,0], soil moisture [-30,0], NDVI ocean bbox) |
| 3 | Caveat when MK p within 0.02 of α | done | `test_near_threshold_*`, `test_api_adds_borderline_caveat_for_p_near_alpha`; 3 golden results flagged |
| 4 | Reanalysis note on air temperature (caveat + `provenance.qualityNotes`) | done | `test_air_temperature_results_carry_reanalysis_note` and 2 others |
| 5 | `legend.colorStops` from the PNG palette | done | `test_trend_map_legend_color_stops_match_the_png`; both ends found in all 4 real PNGs |
| 6 | Sahel air temperature vs GLDAS (report only) | done | MERRA-2 −0.32 vs GLDAS +0.83 °C/decade: opposite sign; `data/validation/sahel_temp_gldas.json` |

Notes: the in-memory analysis cache is cleared between tests (autouse fixture); out-of-latitude points are now `data_unavailable` (was `invalid_input`); `provenance.qualityNotes` is additive and not yet in the contract.

## Run

```bash
cd backend
export DATA_ROOT=/path/to/DigiEarth/data
uv run uvicorn edt.api.app:app --port 8000
uv run pytest
uv run ruff check .
```

## Verified dataset facts (BE-02, real files, 15 Nov 2026, spike month 2020-07)

| Variable | Dataset (CMR) | Variable in file | Native unit / fill | Native grid (as stored) | Orientation | Served grid | Coverage at source (CMR) | File / download |
|---|---|---|---|---|---|---|---|---|
| precipitation | GPM_3IMERGM V07 (C2723754851-GES_DISC), DOI 10.5067/GPM/IMERG/3B-MONTH/07 | `Grid/precipitation` | mm/hr; `_FillValue` -9999.9 | (1, 3600, 1800), DimensionNames `time,lon,lat` | lat −89.95→89.95 asc, lon −179.95→179.95; transpose to lat×lon. Check: Jul 2020 India 75–85°E 20–25°N = 0.33 mm/hr vs Sahara 0–10°E = 0.009 mm/hr | 360×720, 0.5° (5×5 mean) | **2000-01 → 2025-09 only** (V07 is the only version in CMR) | 18.8 MB, ~6 s |
| air_temperature | M2TMNXSLV 5.12.4 (C1276812859-GES_DISC), DOI 10.5067/AP1B0BA5PD2K | `T2M` | K; `_FillValue` 1e15 (none present) | (1, 361, 576) | lat −90→90 asc (pole rows are cell centres), lon −180→179.375 | native 361×576, 0.5°×0.625° | 1980-01 → 2026-09; streams MERRA2_200/300/400/401 | 78.8 MB, ~9 s |
| soil_moisture | GLDAS_NOAH025_M 2.1 (C1342986036-GES_DISC), DOI 10.5067/SXAVCZFAQLNO | `SoilMoi0_10cm_inst` | kg m-2; `_FillValue` -9999 | (1, 600, 1440) | lat −59.875→89.875 asc, lon −179.875→179.875; land only (28% valid) | 300×720, 0.5° (2×2 mean), 60°S–90°N | 2000-01 → 2026-07 | 24.5 MB, ~6 s |
| ndvi | MOD13C2 061 (C2565788914-LPCLOUD), DOI 10.5067/MODIS/MOD13C2.061 | SDS `CMG 0.05 Deg Monthly NDVI` (int16) | `scale_factor` 10000 (value = raw/10000), `valid_range` −2000..10000, `_FillValue` −3000 | (3600, 7200) | GCTP_GEO, upper-left (−180, 90): rows north→south; flipped to ascending | 360×720, 0.5° (10×10 mean) | 2000-02 → 2026-10 | 106 MB, ~9 s; pyhdf works on arm64 |

Served value ranges in the spike month: rainfall 0–2394 mm/month; T2M −65.7…41.5 °C; topsoil 2–100 kg/m²; NDVI −0.2…0.998.

### Differences from ARCHITECTURE.md §5.1

1. **Precipitation coverage ends 2025-09** (GPM_3IMERGM V07 has no granules after Sep 2025; no V08 in CMR). Months 2025-10..12 are stored as missing (status `no source`), so the 2025 annual value is `null` and default-period precipitation statistics use n = 24 years (2001–2024). Rainfall trend map period = 2001–2024. No data is filled in.
2. MERRA-2 native grid includes pole-centred rows (lat ±90) and lon centres start at −180.0, so the served cell edges are lon −180.3125…179.6875 and lat −90.25…90.25. Trend-map PNG for air temperature uses those exact bounds clipped to ±90 latitude (pole rows dropped from the image only) — see maps note below.
3. GLDAS covers 60°S–90°N only (served grid 300×720); Antarctica is absent, not zero.
4. GES DISC CMR "landing page" links point to unrelated collections; `sourceUrl` uses the citation link (`disc.gsfc.nasa.gov/datacollection/...`) instead.
5. MOD13C2 attribute `scale_factor` is 10000 and is a divisor (MODIS convention), matching the 0.0001 in §5.1.

## Deviations from the plan

- Health `dataVersion` is `"uninitialised"` until the pipeline writes `manifest.json` with a `dataVersion` field.
- Contract validation helper (`tests/contract.py`) uses openapi-core with a server prefix of `/api/v1`.

## Blockers

None.
