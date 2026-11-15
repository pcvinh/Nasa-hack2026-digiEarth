# START HERE — Earth Digital Twin: Trend Detective

Version 0.2 · 15 Nov 2026 · NASA Space Apps 2026, "Be An Earth System Trend Detective!"

A web tool where students and the public pick a NASA variable and a place, see how it changed from 2001 to 2025, and learn whether the trend is statistically significant — on a 3D globe that also shows **where** things are changing.

## The pack

| File | Purpose | Read by |
|---|---|---|
| `_Mission/ARCHITECTURE.md` | Decisions, data and stats rules, config, access checklist, GCP path | Everyone, first |
| `contracts/trend-detective-api.openapi.yaml` | The only Frontend ↔ Backend interface (v0.2, architect-owned) | Both sessions |
| `contracts/CHANGE-REQUESTS.md` | How to request a contract change | Both sessions |
| `_Mission/PLAN-1-Frontend.md` | Frontend session brief | Frontend session |
| `_Mission/PLAN-2-Backend-Data.md` | Backend + Data session brief | Backend session |
| `_Mission/earth_digital_twin_vantage_uiux.html` | Visual reference only; numbers are illustrative | Frontend session |
| `_Mission/v1/` | Superseded farming-only plans (kept for reference) | — |

## Scope

- **P0:** 4 variables (rainfall — GPM IMERG; air temperature — MERRA-2; topsoil moisture — GLDAS; vegetation greenness — MODIS NDVI) · 5 presets (Mekong Delta, Central Java, Johor, central Amazon, Sahel) + click any point · chart + Sen's slope/Mann-Kendall + OLS/t-test/95% CI + plain verdict · global trend maps · rules-based Guide · 3 demo walkthroughs · save/reopen sessions · runs on this Mac.
- **P1:** more variables (evapotranspiration, runoff, land surface temperature, NO₂ + Jakarta), compare two regions, LLM wording for the Guide (after approval), mobile layout, Dockerfile.
- **P2:** GCP deployment, projections, ocean variables.
- **Never:** crop-yield prediction, claims about causes, field-level precision, invented numbers.

## Before starting the sessions — your checklist

1. **NASA Earthdata Login** — register at urs.earthdata.nasa.gov and approve "NASA GESDISC DATA ARCHIVE" under Authorized Apps. Store it in `~/.netrc` (`chmod 600`) or as `EARTHDATA_TOKEN` in `backend/.env`. **Do not paste credentials into chat**; just tell the session "Earthdata is set up".
2. **Install uv:** `brew install uv`
3. **Initialise git** (both sessions need their own worktree/branch): Claude can do this for you on request — `git init`, a `.gitignore` that excludes `data/` and `.env*`, and a first commit of the docs and contract.
4. **Create** `DigiEarth/data/` (gitignored, shared by absolute path).
5. **Confirm** the 2026 event dates and the Space Apps rules on work done before the hackathon starts — this decides whether you build now or only prepare.

Not needed now: Cesium ion token, LLM key (P1, optional, needs an approved provider), GCP project/service account (deployment phase). Details in `ARCHITECTURE.md` §8.

## Running the two sessions in parallel

| | Frontend session | Backend + Data session |
|---|---|---|
| Brief | `PLAN-1-Frontend.md` §10 prompt | `PLAN-2-Backend-Data.md` §10 prompt |
| Folder | `frontend/` only | `backend/` (+ `data/`) only |
| Branch | `frontend/p0` (own worktree) | `backend/p0` (own worktree) |
| Starts with | Fixtures (`VITE_USE_FIXTURES=true`) | Scaffold, then the NASA data spike |
| Sync point | Switches to real API when backend says BE-06 is ready | Announces BE-06 ready |
| Contract issues | `contracts/CHANGE-REQUESTS.md` → architect | same |

The architect session (this one) owns the contract and reviews change requests.

## Run locally (once built)

```bash
cd backend && uv run uvicorn edt.api.app:app --port 8000
```

```bash
cd frontend && npm run dev
```

Open http://localhost:5173.

## Integration check and 2-minute demo script

After merging both branches, with real data (`dataStatus = source_backed`, no sample banner):

1. Open the globe → **Start investigation** → Where: Mekong Delta → What: Rainfall → Investigate.
2. Read the verdict: change per decade, total change, significant or not, p-value; open "What does significant mean?".
3. Toggle the chart to monthly anomalies; open **Source** to show dataset, version and resolution.
4. **Show trend map** for rainfall → rotate to compare regions trending in opposite directions → click a cell elsewhere → its own result.
5. Ask the Guide: "What should I look at in a desert?" → click a suggestion → run it on the Sahel.
6. **Save session** → reload → reopen from Saved sessions.

## Open items

- Event dates and pre-work rules (checklist item 5).
- Review licences and attribution before publishing.
- Any LLM provider for the Guide must be an approved provider.
