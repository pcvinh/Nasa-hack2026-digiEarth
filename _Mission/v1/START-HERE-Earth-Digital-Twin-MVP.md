# Earth Digital Twin — Claude Code Implementation Pack

This pack contains **two independent Claude Code implementation plans** plus their shared API contract and the earlier Vantage-style UI reference.

## Deliverables

1. `PLAN-1-Frontend-Claude-Code.md` — React / Cesium globe / Place Analysis / Farming Agent / historical timeline / session UX.
2. `PLAN-2-Backend-Data-Claude-Code.md` — NASA data ingestion, normalization, trend and significance, evidence agent, region APIs and local persistence.
3. `earth-digital-twin-mvp-api.openapi.yaml` — **single shared contract** to prevent FE/BE divergence.
4. `earth_digital_twin_vantage_uiux.html` — optional existing visual scaffold/reference; **not production code and its values are illustrative**.

## Parallel Claude Code execution

**Frontend Claude Code session:**

> Implement `PLAN-1-Frontend-Claude-Code.md` in your own worktree. First inspect the repo and the UI scaffold. Treat `earth-digital-twin-mvp-api.openapi.yaml` as the frozen interface. Start with the globe and typed fixtures, then integrate the real backend. Keep all illustrative figures clearly marked. Run build/tests and provide handoff.

**Backend/Data Claude Code session:**

> Implement `PLAN-2-Backend-Data-Claude-Code.md` in your own worktree. First verify an actual NASA data source and record its units/source/coverage. Treat the OpenAPI contract as frozen. Prioritize historical NASA data -> normalized series -> valid trends -> APIs -> grounded farming answers, then optional data/model expansions. Run tests and provide reproducible NASA-source evidence.

Both sessions may work in parallel. One owner should control modifications to the shared contract. Before merging, resolve conflicts through schema review and run an integration smoke test with `dataStatus=source_backed`.

## MVP priority

- **P0:** Mekong Delta, a working 3D globe, actual NASA historical temperature and rainfall, proven source product, trend significance, place panel, farming evidence agent, save/reopen.
- **P1:** MODIS NDVI and GLDAS soil-water integration, improved map layers and explanatory comparisons.
- **P2:** NASA POWER CMIP6 projections, additional regions, optional Google Photorealistic Tiles.

Do **not** claim crop yield forecasting, proven causality, or calibrated farm-risk probabilities. The 2026 NASA challenge favors real geographical trend evidence and scientific significance.

## Repository layout

The plans assume a monorepo, adaptable to existing repos:

```text
apps/web        Frontend mission
apps/api        Backend API mission
pipeline        Python ETL mission (within Backend/Data plan)
contracts       Shared OpenAPI
reference       Original UI scaffold
```

The archive does not include live NASA datasets, credentials, or a working implementation. Its purpose is execution planning and interface alignment.
