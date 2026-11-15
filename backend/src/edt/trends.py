"""POST /trends/analyze service: cube slice → regional series → annual values → statistics."""

from __future__ import annotations

import json
from collections import OrderedDict

import numpy as np

from edt.api.errors import ApiError
from edt.catalogue import get_variable
from edt.config import Settings
from edt.data import cube_info, data_version, provenance, variable_status
from edt.regions.select import presets, regional_series, select_cells
from edt.stats.core import (
    MK_METHOD,
    OLS_METHOD,
    annual_values,
    interpret,
    monthly_anomalies,
    trend_stats,
)

_CACHE: OrderedDict[str, dict] = OrderedDict()
_CACHE_MAX = 256


def _r(v: float, nd: int = 4) -> float | None:
    return None if v is None or not np.isfinite(v) else round(float(v), nd)


def _bad(msg: str, **details) -> ApiError:
    return ApiError(400, "invalid_input", msg, details or None)


def _no_data(msg: str, **details) -> ApiError:
    return ApiError(400, "data_unavailable", msg, details or None)


def validate_region(region: dict) -> None:
    given = [k for k in ("presetId", "bbox", "point") if region.get(k) is not None]
    if len(given) != 1:
        raise _bad("region must have exactly one of presetId, bbox or point.", given=given)
    if region.get("presetId") is not None and region["presetId"] not in presets():
        raise ApiError(404, "not_found", f"Unknown preset region '{region['presetId']}'.")
    if region.get("bbox") is not None:
        w, s, e, n = region["bbox"]
        if not (-180 <= w < e <= 180 and -90 <= s < n <= 90):
            raise _bad(
                "bbox must be [west, south, east, north] with west < east and south < "
                "north, within -180..180 and -90..90 (boxes crossing the antimeridian "
                "are not supported)."
            )
    if region.get("point") is not None:
        x, y = region["point"]
        if not (-180 <= x <= 180 and -90 <= y <= 90):
            raise _bad("point must be [longitude, latitude] within -180..180 and -90..90.")


def _check_in_domain(region: dict, lat: np.ndarray, var_name: str) -> None:
    half = abs(lat[1] - lat[0]) / 2
    lo, hi = lat[0] - half, lat[-1] + half
    if region.get("point") is not None:
        y = region["point"][1]
        inside = lo <= y <= hi
    elif region.get("bbox") is not None:
        _, s, _, n = region["bbox"]
        inside = n >= lo and s <= hi
    else:
        return
    if not inside:
        raise _no_data(
            f"The region is outside the area covered by {var_name} "
            f"(latitude {lo:.0f}° to {hi:.0f}°)."
        )


def analyze(settings: Settings, req: dict) -> dict:
    var = get_variable(req["variableId"])
    if var is None:
        raise _bad(f"Unknown variable '{req['variableId']}'.")
    region = req["region"]
    validate_region(region)
    status, reason = variable_status(settings, var)
    info = cube_info(settings, var.id)
    if status == "unavailable" or info is None:
        raise ApiError(
            400, "data_unavailable", reason or "Data unavailable.", {"variableId": var.id}
        )
    cov = info.coverage
    cy0, cy1 = int(cov[0][:4]), int(cov[1][:4])
    start, alpha = int(req["startYear"]), float(req["alpha"])
    # endYear omitted → the variable's last complete year (contract 0.2.1); explicit values win
    end = int(req["endYear"]) if req.get("endYear") is not None else info.last_complete_year
    if not (cy0 <= start < end <= cy1):
        raise _bad(
            f"Years must satisfy {cy0} <= startYear < endYear <= {cy1} for {var['name']}.",
            coverage={"start": cov[0], "end": cov[1]},
        )
    _check_in_domain(region, info.lat, var["name"])

    version = data_version(settings)
    key = json.dumps([var.id, region, start, end, alpha, version], sort_keys=True)
    if key in _CACHE:
        _CACHE.move_to_end(key)
        return _CACHE[key]

    sel = select_cells(region, info.lat, info.lon)
    y0, y1 = int(sel.iy.min()), int(sel.iy.max()) + 1
    x0, x1 = int(sel.ix.min()), int(sel.ix.max()) + 1
    t0 = info.months.index(f"{start}-01")
    t1 = info.months.index(f"{end}-12") + 1
    block = info.read(y0, y1, x0, x1)[t0:t1]
    mean, frac, ncell, dropped = regional_series(block, info.lat[y0:y1], sel.iy - y0, sel.ix - x0)

    if ncell == 0:
        what = "point" if sel.representativeness == "single_cell" else "region"
        land = (
            " It is a land-only variable, so ocean and ice-free sea have no values."
            if (var["landOnly"])
            else ""
        )
        raise _no_data(
            f"{var['name']} has no valid data for this {what} between {start} and {end}.{land} "
            "Try a different location.",
            variableId=var.id,
            cellsChecked=int(sel.iy.size),
        )

    caveats = list(sel.caveats)
    if dropped:
        caveats.append(
            f"{dropped} grid cell(s) in the region were left out because the dataset has no "
            "data there (for example sea, for a land-only variable)."
        )
    months = info.months[t0:t1]
    no_source = [m for m, s in zip(months, info.status[t0:t1], strict=True) if s == 2]
    if no_source:
        caveats.append(
            f"No source data is available for {len(no_source)} month(s) "
            f"({no_source[0]} to {no_source[-1]}); they are shown as missing."
        )

    annual = annual_values(mean, var["annualAggregation"])
    anomalies = monthly_anomalies(mean)
    years = np.arange(start, end + 1)
    ts = trend_stats(years, annual, alpha)
    cell_size = var.dataset["servedResolution"]
    interp = interpret(
        name=var["name"],
        region_name=sel.name,
        annual_unit=var["annualUnit"],
        start=start,
        end=end,
        ts=ts,
        cell_size=cell_size,
        extra_caveats=caveats,
    )
    ok = ts.status != "insufficient_data"

    def per_dec(v):
        return None if v is None else float(v) * 10

    result = {
        "variableId": var.id,
        "region": {
            "presetId": sel.preset_id,
            "name": sel.name,
            "bbox": [float(v) for v in sel.bbox],
            "representativeness": sel.representativeness,
            "cellCount": ncell,
            "cellSize": cell_size,
        },
        "period": {"startYear": start, "endYear": end},
        "unit": var["unit"],
        "annualUnit": var["annualUnit"],
        "dataStatus": "source_backed",
        "monthly": [
            {
                "time": m,
                "value": _r(v),
                "anomaly": _r(a),
                "validCellFraction": _r(f, 3) if ncell else None,
            }
            for m, v, a, f in zip(months, mean, anomalies, frac, strict=True)
        ],
        "annual": [{"year": int(y), "value": _r(v)} for y, v in zip(years, annual, strict=True)],
        "totalChange": {
            "value": ts.sen_per_year * (end - start) if ok else None,
            "unit": var["annualUnit"],
        },
        "linear": {
            "method": OLS_METHOD,
            "slopePerDecade": per_dec(ts.ols_per_year),
            "ci95": [ts.ols_ci_per_year[0] * 10, ts.ols_ci_per_year[1] * 10] if ok else None,
            "pValue": ts.ols_p,
            "rSquared": ts.r_squared,
            "n": ts.n,
        },
        "mannKendall": {
            "method": MK_METHOD,
            "senSlopePerDecade": per_dec(ts.sen_per_year),
            "tau": ts.tau,
            "pValue": ts.mk_p,
            "n": ts.n,
        },
        "trendLines": {
            "sen": [
                {"year": y, "value": ts.sen_intercept + ts.sen_per_year * y} for y in (start, end)
            ]
            if ok
            else [],
            "ols": [
                {"year": y, "value": ts.ols_intercept + ts.ols_per_year * y} for y in (start, end)
            ]
            if ok
            else [],
        },
        "significance": {
            "alpha": alpha,
            "status": ts.status,
            "direction": ts.direction,
            "agreement": ts.agreement,
        },
        "interpretation": interp,
        "provenance": provenance(settings, var),
        "dataVersion": version,
    }
    _CACHE[key] = result
    if len(_CACHE) > _CACHE_MAX:
        _CACHE.popitem(last=False)
    return result
