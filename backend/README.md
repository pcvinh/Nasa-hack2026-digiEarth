# edt — Trend Detective backend

One Python 3.12 project (uv): NASA data pipeline, statistics module and FastAPI service for
`contracts/trend-detective-api.openapi.yaml` (v0.2). See `BACKEND_HANDOFF.md` for the full handoff.

```bash
cd backend
export DATA_ROOT=/path/to/DigiEarth/data   # absolute path, outside git

uv run uvicorn edt.api.app:app --port 8000      # API on http://localhost:8000/api/v1
uv run pytest                                   # tests (contract validation included)
uv run ruff check .

# pipeline (Earthdata Login from ~/.netrc)
uv run edt spike --variable precipitation --month 2020-07
uv run edt ingest --variable all                # resumable; months already in the cube are skipped
uv run edt maps --variable all
uv run edt manifest
uv run edt golden                               # regenerate tests/golden/*.json
uv run edt regions                              # rebuild src/edt/regions/presets.geojson
uv run edt crosscheck                           # native 0.1° IMERG vs our Mekong bbox series
uv run edt crosscheck --giovanni-csv FILE.csv   # Giovanni area-averaged CSV vs ours
```
