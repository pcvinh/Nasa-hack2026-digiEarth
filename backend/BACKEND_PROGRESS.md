# Backend progress

Branch `backend/p0` (worktree `DigiEarth-backend`). `DATA_ROOT=/path/to/DigiEarth/data`.

## Packages

| Package | Status | Evidence |
|---|---|---|
| BE-01 scaffold | done | `uv run pytest` 6 passed; `uv run ruff check` clean; uvicorn serves `/api/v1/health` |
| BE-02 data spike | not started | |
| BE-03 stats | not started | |
| BE-04..BE-10 | not started | |

## Run

```bash
cd backend
export DATA_ROOT=/path/to/DigiEarth/data
uv run uvicorn edt.api.app:app --port 8000
uv run pytest
uv run ruff check .
```

## Verified dataset facts

(filled by BE-02; real files win over ARCHITECTURE.md section 5.1)

Pre-observed before BE-02, to be re-confirmed in the spike: IMERG Grid/precipitation mm/hr, fill -9999.9,
shape (1, 3600, 1800) = lon x lat; MOD13C2 CMG 0.05 Deg Monthly NDVI 3600x7200, scale 10000, fill -3000,
readable with pyhdf.

## Deviations from the plan

- `catalogue.py` holds only the four variable ids until BE-02 creates `catalogue.yaml` from verified facts.
- Health `dataVersion` is `"uninitialised"` until the pipeline writes `manifest.json` with a `dataVersion` field.
- Contract validation helper (`tests/contract.py`) uses openapi-core with a server prefix of `/api/v1`.

## Blockers

None.
