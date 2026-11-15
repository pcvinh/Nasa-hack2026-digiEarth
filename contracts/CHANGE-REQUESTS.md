# Contract change requests

The contract `trend-detective-api.openapi.yaml` is owned by the Solution Architect session. Implementation sessions do not edit it directly. Add a request below and tell the user; the architect decides, updates the contract, bumps the version and logs it here.

## Template

```text
### CR-<n> — <short title>
- Raised by: Frontend | Backend
- Date: DD MMM YYYY
- Endpoint / schema:
- Change:
- Why:
- Breaking? yes / no
- Status: open | accepted (vX.Y.Z) | rejected (reason)
```

## Log

| Version | Date | Change |
|---|---|---|
| 0.2.0 | 15 Nov 2026 | Repositioned to general Trend Detective API (replaces v0.1 farming contract in `_Mission/v1/`). |
| 0.2.1 | 15 Nov 2026 | `TrendRequest.endYear`: no fixed default; omitted = variable's last complete year (rainfall 2024). `TrendMap.legend.colorStops` added (optional). `BadRequest` text: no data for a region/point must be `400 data_unavailable`, never 200 with `cellCount 0`. Documentation/optional changes only; no breaking change. |

## Open requests

None. Architect rulings after the P0 reviews (15 Nov 2026):

- A. Default period follows each variable's last complete year (contract 0.2.1).
- B. No-data point/region returns `400 data_unavailable` (contract 0.2.1).
- C. Legend colours come from the API (`colorStops`, contract 0.2.1); frontend falls back to palette name until the backend provides them.
- Near-threshold p-values (within 0.02 of alpha) get a caveat; air-temperature results get a reanalysis note (backend wording only).
- MERRA-2 map keeps exact bounds; frontend clamps the west edge to -180 degrees.
