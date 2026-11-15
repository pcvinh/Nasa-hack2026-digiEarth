# Backend handoff — Trend Detective (P0)

Branch `backend/p0` + review fixes on `backend/fixes` · 15 Nov 2026 · `dataVersion` **2026-11-15.1** · contract v0.2.1

## Run

```bash
cd backend
export DATA_ROOT=/path/to/DigiEarth/data
uv run uvicorn edt.api.app:app --port 8000     # http://localhost:8000/api/v1, docs at /docs
uv run pytest                                  # 92 tests; real-data and golden tests need DATA_ROOT
uv run ruff check .
```

Pipeline commands: see `README.md` (`spike`, `ingest`, `maps`, `manifest`, `golden`, `regions`, `crosscheck`).
Environment variables: `DATA_ROOT` (required, absolute), `SESSION_STORE=sqlite`, `ALLOWED_ORIGINS` (default `http://localhost:5173`), `GUIDE_LLM=off`. Earthdata Login comes from `~/.netrc` and is used only by the pipeline.

## Review fixes (branch `backend/fixes`, contract v0.2.1 and Architect rulings A–C)

Each fix is its own commit with tests; golden files were regenerated in each commit.

1. **Default `endYear`.** Omitted `endYear` now means the variable's last complete year, derived from `coverage.end` (rainfall 2024, all other variables 2025). `period.endYear`, the annual series and the interpretation text use the same year. An explicit `endYear` (even 2025 for rainfall) still works and reports the missing months in caveats. A default end that is not after `startYear` returns `400 invalid_input`.
2. **No data → `400 data_unavailable`.** A point, bbox or preset with no valid cells for the variable (for example NDVI at [0, 0] in the ocean) returns `400 data_unavailable` with a clear message, never `200` with `cellCount 0`. Behaviour change: a point or bbox outside a variable's latitude range (for example soil moisture south of 60°S) is now also `data_unavailable`; it was `invalid_input`.
3. **Borderline caveat.** If the Mann-Kendall p-value is within 0.02 of α (either side), the first caveat says the verdict is close to the threshold and could change with a different area or grid. In the golden set this applies to Central Java air temperature, Central Amazon topsoil moisture and Sahel rainfall.
4. **Reanalysis note.** All `air_temperature` results carry a caveat and `provenance.qualityNotes` saying MERRA-2 is a reanalysis and can differ from station records. The note text lives in `catalogue.yaml` (`qualityNotes`), so other variables can use it later.
5. **`legend.colorStops`.** Trend-map JSON and `/trend-maps/{id}` return 11 hex colours from `min` to `max`, sampled with the exact colormap call that paints the PNG. Verified on the real PNGs: both end colours appear in each image. Maps built before this change get the same stops computed on the fly. The real maps were rebuilt.
6. **Sahel air temperature vs GLDAS (report only, results unchanged).** Same box (−17..35°E, 12..18°N), annual means 2001–2025:

   | Series | Sen's slope (°C/decade) | Mann-Kendall p | Mean annual |
   |---|---|---|---|
   | MERRA-2 T2M (served) | **−0.32** (decreasing) | 0.014 | 27.8 °C |
   | GLDAS Noah 2.1 `Tair_f_inst` | **+0.83** (increasing) | 0.0002 | 28.9 °C |

   Monthly correlation is 0.95 and MERRA-2 is 1.1 °C cooler on average, but the **trend direction is opposite** and both are significant. So the Sahel cooling in our served result is not robust across NASA products. I have not diagnosed the cause (for example MERRA-2 production-stream changes in 2011 and 2020, or GLDAS forcing changes); that needs a station-based check. Command: `uv run edt crosscheck-sahel`; output in `data/validation/sahel_temp_gldas.json`.

## What is enabled

- **Variables (all `source_backed`):** `precipitation`, `air_temperature`, `soil_moisture`, `ndvi`
- **Preset regions:** `mekong-delta`, `central-java`, `johor`, `amazon-central`, `sahel`
- **Endpoints:**
  - `/health`, `/variables`, `/regions`, `/regions/{id}`
  - `/trends/analyze` (preset, bbox or point)
  - `/trend-maps/{id}` and `/trend-maps/{id}/image.png` (all 4 variables)
  - `/guide/chat` (rules mode)
  - `/sessions` (CRUD, SQLite)

## Dataset facts (verified on real files)

| Variable | Dataset, version | Native → served | Served unit (annual) | Coverage in cube | Access date |
|---|---|---|---|---|---|
| precipitation | GPM_3IMERGM V07 | 0.1° → 0.5° (5×5 mean) | mm/month (sum, mm/year) | 2001-01 → **2025-09** | 15 Nov 2026 |
| air_temperature | M2TMNXSLV 5.12.4 (T2M) | 0.5°×0.625° native | °C (mean) | 2001-01 → 2025-12 | 15 Nov 2026 |
| soil_moisture | GLDAS_NOAH025_M 2.1 (SoilMoi0_10cm_inst) | 0.25° → 0.5° (2×2 mean), 60°S–90°N, land only | kg/m² (mean) | 2001-01 → 2025-12 | 15 Nov 2026 |
| ndvi | MOD13C2 061 | 0.05° → 0.5° (10×10 mean), land only | NDVI (mean) | 2001-01 → 2025-12 | 15 Nov 2026 |

The full facts table (fills, grids, orientation checks) is in `BACKEND_PROGRESS.md`. Per-file URLs and SHA-256 hashes are in `data/manifest.json`.

## Processing steps

1. Download one month at a time (earthaccess, at most 4 parallel downloads).
2. Read the file: mask fill values and convert units (mm/hr × hours in month; K − 273.15; NDVI raw ÷ 10000).
3. Block-mean by an integer factor. A coarse cell is kept only if at least 50% of its sub-cells are valid.
4. Write the month to `cube/<var>.zarr`, then delete the raw file. The cube is pre-allocated, so ingest is resumable. Months with no source granule are marked and stay NaN.
5. Regional mean: cos(lat)-weighted over cells whose centre is inside the region. Cells with no data in any month of the period (sea for land-only variables) are dropped and reported in caveats. A month with under 50% valid cells is `null`.
6. Annual value: sum (precipitation) or mean (other variables). Any missing month makes the year `null`.
7. Statistics on annual values: Mann-Kendall + Sen's slope (headline), with OLS + t-test + 95% CI alongside. At least 10 non-null years are required.
8. Maps: per-cell Mann-Kendall/Sen (vectorised, checked against `pymannkendall` on 200 cells), Benjamini-Hochberg FDR q = 0.05, colour limits at the 98th percentile of |slope|.

Full ingest: about 28 minutes in total (precipitation 4 min, soil moisture 5 min, air temperature 8 min, NDVI 12 min). 63.4 GB downloaded (rainfall 5.6, air temperature 19.4, soil moisture 7.5, NDVI 30.9) and deleted after processing; the 5.4 GB re-download for the native cross-check is not included; `data/` is 509 MB on disk.

## Validation

- **Native IMERG cross-check (done).** I compared our `/trends/analyze` monthly series for the Mekong preset bbox `[103.838, 8.44, 106.8139, 11.0363]` with an area mean computed directly from the 297 native 0.1° files through a separate code path.
  - Correlation: **0.9993**
  - Mean difference: **−5.0 mm/month (−2.9%)**
  - Largest monthly difference: 32.6 mm

  The small negative bias is expected: the 0.5° cells whose centres fall inside the box cover a slightly different area from the native cells. Results are in `data/validation/native_mekong.json`.
- **MERRA-2 pipeline check (done).** Our Sahel box values equal the native T2M box mean to 4 decimals in 5 test months (2001-07, 2010-12, 2011-01, 2020-09, 2024-07), across the MERRA2_300 → 400 → 401 stream changes.
- **Giovanni cross-check (done, 15 Nov 2026).** Giovanni "Time Series, Area-Averaged", GPM_3IMERGM v07 precipitation, bbox 103.838, 8.44, 106.8139, 11.0363, 2001-01 to 2025-09. Giovanni's own data bounding box is 103.85, 8.45, 106.75, 10.95. The CSV values are in mm/hr and were converted to mm/month using each month's hours. Compared with our `/trends/analyze` for the same bbox (30 cells at 0.5°):
  - Correlation: **0.9993** (n = 297 months)
  - Mean difference: **−5.0 mm/month (−2.9%)**
  - Largest monthly difference: 32.6 mm

  Giovanni's series agrees with my native-file area mean to about 6 decimal places, which independently confirms the native check above. Trend statistics on annual sums, 2001–2024 (n = 24):

  | Series | Sen's slope (mm/yr per decade) | Mann-Kendall p | OLS slope, p | Mean annual |
  |---|---|---|---|---|
  | Ours (bbox, 0.5°) | +117 | **0.045 (significant)** | +104, 0.045 | 2,003 mm |
  | Giovanni (native 0.1°) | +108 | **0.056 (not significant)** | +105, 0.048 | 2,063 mm |

  Direction and size agree within 8%, and the OLS t-test is significant in both. The Mann-Kendall verdict, however, sits right at α = 0.05 and flips between the two grids. The difference comes from the 0.5° cell selection (about 3% less area-mean rainfall), not from a processing error. Results, including this table, are in `data/validation/giovanni_mekong.json`. The source CSV is `data/validation/giovanni_mekong.csv`.

  The Mekong **preset** (province polygon, 13 cells) is a different area from this box and gives +121 mm/yr per decade with p = 0.011, well clear of the threshold.
- **Golden files.** `tests/golden/` holds 20 files (5 presets × 4 variables). The re-run reproduces them exactly, and each one validates against the contract.
- **Trend maps.** I inspected all four visually. Soil moisture and NDVI trace the continents with north up. Air temperature shows Arctic amplification and the North Atlantic warming hole. NDVI shows the India and China greening.

## Results for the preset regions (default period, α = 0.05)

| Region | Rainfall (mm/yr per decade) | Air temp (°C/decade) | Topsoil (kg/m² per decade) | NDVI (per decade) |
|---|---|---|---|---|
| Mekong Delta | +121, p = 0.011 ✔ | +0.061, p = 0.56 | +0.046, p = 0.94 | +0.031, p < 0.001 ✔ |
| Central Java | +56, p = 0.82 | +0.14, p = 0.038 ✔ | +0.19, p = 0.83 | +0.019, p = 0.008 ✔ |
| Johor | +112, p = 0.33 | +0.29, p < 0.001 ✔ | +0.075, p = 0.66 | +0.0051, p = 0.004 ✔ |
| Central Amazon | −40, p = 0.71 | +0.36, p = 0.013 ✔ | −0.47, p = 0.059 | +0.0020, p = 0.006 ✔ |
| Sahel | +31, p = 0.031 ✔ | **−0.32, p = 0.014 ✔** | −0.077, p = 0.34 | +0.0095, p < 0.001 ✔ |

✔ = significant (Mann-Kendall). Rainfall uses the default period 2001–2024 (n = 24); the other variables use 2001–2025 (n = 25). Borderline (p within 0.02 of 0.05, now flagged in caveats): Central Java air temperature, Central Amazon topsoil moisture, Sahel rainfall.

## Known limitations

- **IMERG V07 ends 2025-09.** 2025 rainfall is `null`. The default rainfall period is now 2001–2024 (n = 24), also in the trend map's `period`. Asking for `endYear` 2025 explicitly still works and says why the last year is missing.
- **Sahel air temperature cooling** (−0.32 °C/decade, significant). The pipeline matches native MERRA-2 exactly, so it is not a processing error, but GLDAS shows +0.83 °C/decade for the same box (fix 6), so the sign is not robust. A reanalysis note is now on every air-temperature result. Recommend not using the Sahel for the heat demo, or showing it as a data-disagreement example.
- **MERRA-2 map bounds** are `[-180.3125, -89.75, 179.6875, 89.75]`. The native lon centres start at −180, and the pole-centred rows are not drawn. West < −180 may need handling in Cesium (wrap or clamp) — see open questions.
- Boxes crossing the antimeridian are rejected (400).
- The point/box name is generated (for example "Point 10.10°N, 105.10°E").
- Annual values may be autocorrelated; trends are linear only; 0.5° cells are not field-level. All of these are always stated in caveats.
- Guide is rules only (P1 LLM wording not built). It refuses yield, forecast and cause questions, and air quality questions ("not available yet").
- The analysis cache is in memory per process.

## Open change requests

None filed by the backend. One additive item for the Architect to document: `Provenance.qualityNotes` (array of strings, `[]` when there are none) is returned by the API but is not in contract 0.2.1. It is optional for clients; the frontend should ignore unknown fields or the field should be added to the contract.

## Open questions for the Architect

0. ~~Borderline significance caveat~~ — done (fix 3, ruling).
1. ~~MERRA-2 map bounds~~ — ruling: keep the exact bounds; the frontend clamps the west edge to −180°.
2. **Sahel heat demo:** the reanalysis note is added (fix 4), but GLDAS disagrees on the sign of the trend (fix 6). Keep the Sahel for heat, relabel it as a disagreement example, or replace it?
3. **Region cells exclude permanently missing cells (and, if none remain, the request is `data_unavailable`)** (sea for land-only variables) before the 50% rule. This is my interpretation of §5.3; without it, coastal regions would be `null` for soil moisture and NDVI.
4. **Licences:**
   - Vietnam ADM1 (geoBoundaries) is Public Domain with 2008 boundaries, not CC BY 4.0 as in the plan.
   - Indonesia and Malaysia ADM1 are ODbL 1.0 (© OpenStreetMap contributors), which needs attribution and share-alike for the derived `presets.geojson`.
   - Confirm licensing before any commercial use.
