# Backend handoff — Trend Detective (P0)

Branch `backend/p0` · 15 Nov 2026 · `dataVersion` **2026-11-15.1** · contract v0.2 (unchanged)

## Run

```bash
cd backend
export DATA_ROOT=/path/to/DigiEarth/data
uv run uvicorn edt.api.app:app --port 8000     # http://localhost:8000/api/v1, docs at /docs
uv run pytest                                  # 63 tests; golden tests need DATA_ROOT
uv run ruff check .
```

Pipeline commands: see `README.md` (`spike`, `ingest`, `maps`, `manifest`, `golden`, `regions`, `crosscheck`).
Environment variables: `DATA_ROOT` (required, absolute), `SESSION_STORE=sqlite`, `ALLOWED_ORIGINS` (default `http://localhost:5173`), `GUIDE_LLM=off`. Earthdata Login comes from `~/.netrc` and is used only by the pipeline.

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
- **Giovanni cross-check (not done; tooling ready).** Giovanni's REST `/timeseries` endpoint is reported to return single points only, not area averages. Area averages come from the Giovanni web UI as a CSV, or from a Harmony-based service with quotas that I have not verified. To finish this check:
  1. In Giovanni, choose "Time Series, Area-Averaged" for GPM_3IMERGM v07 precipitation.
  2. Use bbox 103.838, 8.44, 106.8139, 11.0363 and 2001-01 to 2025-09.
  3. Download the CSV and run `uv run edt crosscheck --giovanni-csv <file>`. It reports correlation and mean difference and writes `data/validation/giovanni_mekong.json`.
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

✔ = significant (Mann-Kendall). Rainfall uses n = 24 (2025 is `null`); the other variables use n = 25.

## Known limitations

- **IMERG V07 ends 2025-09.** 2025 rainfall is `null`, rainfall statistics use 2001–2024 (n = 24), and the rainfall map period is 2001–2024. This is stated in caveats and in `TrendMap.period`.
- **Sahel air temperature cooling** (−0.32 °C/decade, significant; the blue patch over North Africa on the map). The pipeline matches native MERRA-2 exactly, so this is a property of the MERRA-2 reanalysis, not a processing error. I have not checked it against station data. Suggest the Architect adds a "reanalysis, may differ from station records" note, or picks a different region for the heat demo.
- **MERRA-2 map bounds** are `[-180.3125, -89.75, 179.6875, 89.75]`. The native lon centres start at −180, and the pole-centred rows are not drawn. West < −180 may need handling in Cesium (wrap or clamp) — see open questions.
- Boxes crossing the antimeridian are rejected (400).
- The point/box name is generated (for example "Point 10.10°N, 105.10°E").
- Annual values may be autocorrelated; trends are linear only; 0.5° cells are not field-level. All of these are always stated in caveats.
- Guide is rules only (P1 LLM wording not built). It refuses yield, forecast and cause questions, and air quality questions ("not available yet").
- The analysis cache is in memory per process.

## Open change requests

None filed. The contract v0.2 fitted all P0 behaviour.

## Open questions for the Architect

1. **MERRA-2 trend map:** keep the exact bounds (west −180.3125), or should the frontend clamp or wrap? Any server-side fix would shift cells, so I have not made one.
2. **Sahel heat result:** add a reanalysis caveat, or change the demo region for heat?
3. **Region cells exclude permanently missing cells** (sea for land-only variables) before the 50% rule. This is my interpretation of §5.3; without it, coastal regions would be `null` for soil moisture and NDVI.
4. **Licences:**
   - Vietnam ADM1 (geoBoundaries) is Public Domain with 2008 boundaries, not CC BY 4.0 as in the plan.
   - Indonesia and Malaysia ADM1 are ODbL 1.0 (© OpenStreetMap contributors), which needs attribution and share-alike for the derived `presets.geojson`.
   - Confirm licensing before any commercial use.
