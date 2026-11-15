"""BE-10 validation for precipitation over a bbox.

1. `native`: independent area mean from the native 0.1° IMERG files (separate code path: no
   coarsening, cells whose native centre is inside the bbox, cos(lat) weights), compared with
   /trends/analyze for the same bbox.
2. `giovanni`: compare with a Giovanni "Time Series, Area-Averaged" CSV downloaded by a person
   from the Giovanni web UI (same bbox, GPM_3IMERGM v07 precipitation).
"""

from __future__ import annotations

import calendar
import csv
import json
import re
from concurrent.futures import ThreadPoolExecutor
from pathlib import Path

import numpy as np

from edt.catalogue import get_variable
from edt.config import Settings
from edt.pipeline import fetch
from edt.trends import analyze


def _ours(settings: Settings, bbox: list[float]) -> dict[str, float | None]:
    res = analyze(
        settings,
        {
            "variableId": "precipitation",
            "region": {"bbox": bbox},
            "startYear": 2001,
            "endYear": 2025,
            "alpha": 0.05,
        },
    )
    return {m["time"]: m["value"] for m in res["monthly"]}


def _native_month(path: Path, bbox: list[float]) -> float:
    import h5py

    w, s, e, n = bbox
    with h5py.File(path, "r") as f:
        g = f["Grid"]
        lat, lon = g["lat"][:], g["lon"][:]
        xs = np.nonzero((lon >= w) & (lon <= e))[0]
        ys = np.nonzero((lat >= s) & (lat <= n))[0]
        sub = g["precipitation"][0, xs[0] : xs[-1] + 1, ys[0] : ys[-1] + 1].astype(np.float64)
    sub[sub < -9000] = np.nan  # (lon, lat)
    wts = np.cos(np.deg2rad(lat[ys]))[None, :] * np.isfinite(sub)
    return float(np.nansum(sub * wts) / wts.sum())  # mm/hr


def _stats(a: np.ndarray, b: np.ndarray) -> dict:
    ok = np.isfinite(a) & np.isfinite(b)
    a, b = a[ok], b[ok]
    return {
        "n": int(ok.sum()),
        "correlation": float(np.corrcoef(a, b)[0, 1]),
        "meanDifference": float(np.mean(a - b)),
        "meanRelativeDifferencePct": float(100 * np.mean(a - b) / np.mean(b)),
        "maxAbsDifference": float(np.max(np.abs(a - b))),
    }


def native_check(settings: Settings, bbox: list[float], out: Path) -> dict:
    var = get_variable("precipitation")
    ds = var.dataset
    ours = _ours(settings, bbox)
    granules = fetch.search_months(ds["shortName"], ds["cmrVersion"], "2001-01", "2025-12")
    tmp = settings.raw_dir / "crosscheck"

    def one(month: str):
        path, _ = fetch.download(granules[month], tmp)
        try:
            return month, _native_month(path, bbox)
        finally:
            path.unlink(missing_ok=True)

    with ThreadPoolExecutor(4) as pool:
        native = dict(pool.map(one, sorted(granules)))
    months = sorted(native)
    hours = np.array([calendar.monthrange(int(m[:4]), int(m[5:]))[1] * 24 for m in months])
    a = np.array([np.nan if ours[m] is None else ours[m] for m in months])
    b = np.array([native[m] for m in months]) * hours  # → mm/month
    result = {
        "bbox": bbox,
        "compare": "ours (0.5° cube, bbox) vs native 0.1° IMERG area mean",
        "unit": "mm/month",
        **_stats(a, b),
    }
    out.write_text(
        json.dumps(
            {"summary": result, "months": months, "ours": a.tolist(), "native": b.tolist()},
            indent=1,
        )
    )
    return result


def giovanni_check(settings: Settings, bbox: list[float], csv_path: Path, out: Path) -> dict:
    rows = []
    with open(csv_path, newline="") as f:
        for r in csv.reader(f):
            if r and re.match(r"^\d{4}-\d{2}", r[0].strip()):
                try:
                    rows.append((r[0].strip()[:7], float(r[1])))
                except (ValueError, IndexError):
                    continue
    if not rows:
        raise RuntimeError("no 'YYYY-MM...,value' rows found in the Giovanni CSV")
    gio = dict(rows)
    ours = _ours(settings, bbox)
    months = sorted(m for m in gio if m in ours)
    hours = np.array([calendar.monthrange(int(m[:4]), int(m[5:]))[1] * 24 for m in months])
    a = np.array([np.nan if ours[m] is None else ours[m] for m in months])
    b = np.array([gio[m] for m in months], dtype=np.float64)
    if np.nanmedian(b) < 5:  # Giovanni reports IMERG monthly in mm/hr
        b = b * hours
    result = {
        "bbox": bbox,
        "compare": "ours vs Giovanni area-averaged time series",
        "unit": "mm/month",
        "source": csv_path.name,
        **_stats(a, b),
    }
    out.write_text(
        json.dumps(
            {"summary": result, "months": months, "ours": a.tolist(), "giovanni": b.tolist()},
            indent=1,
        )
    )
    return result


def _gldas_tair_box_month(path: Path, bbox: list[float]) -> float:
    """cos(lat)-weighted mean of GLDAS Tair_f_inst (°C) over native 0.25° cells inside bbox."""
    import netCDF4

    w, s, e, n = bbox
    with netCDF4.Dataset(path) as nc:
        lat = np.asarray(nc["lat"][:], dtype=np.float64)
        lon = np.asarray(nc["lon"][:], dtype=np.float64)
        ys = np.nonzero((lat >= s) & (lat <= n))[0]
        xs = np.nonzero((lon >= w) & (lon <= e))[0]
        v = nc["Tair_f_inst"]
        v.set_auto_maskandscale(False)
        a = np.asarray(v[0, ys[0] : ys[-1] + 1, xs[0] : xs[-1] + 1], dtype=np.float64)
    a[a < -9000] = np.nan
    wts = np.cos(np.deg2rad(lat[ys]))[:, None] * np.isfinite(a)
    return float(np.nansum(np.where(np.isfinite(a), a, 0.0) * wts) / wts.sum()) - 273.15


def sahel_gldas_check(settings: Settings, out: Path) -> dict:
    """Does GLDAS (Noah, forced by observations) show the same Sahel air-temperature trend
    direction as MERRA-2 (our served series)? Report only; results are not changed."""
    from edt.pipeline.cube import month_list
    from edt.regions.select import presets
    from edt.stats.core import annual_values, trend_stats

    bbox = presets()["sahel"]["bbox"]
    ours = analyze(
        settings,
        {
            "variableId": "air_temperature",
            "region": {"presetId": "sahel"},
            "startYear": 2001,
            "endYear": 2025,
            "alpha": 0.05,
        },
    )
    ours_m = np.array([np.nan if m["value"] is None else m["value"] for m in ours["monthly"]])
    months = month_list("2001-01", "2025-12")
    granules = fetch.search_months("GLDAS_NOAH025_M", "2.1", "2001-01", "2025-12")
    tmp = settings.raw_dir / "crosscheck_gldas"

    def one(month: str):
        path, _ = fetch.download(granules[month], tmp)
        try:
            return month, _gldas_tair_box_month(path, bbox)
        finally:
            path.unlink(missing_ok=True)

    with ThreadPoolExecutor(4) as pool:
        gl = dict(pool.map(one, months))
    gl_m = np.array([gl[m] for m in months])
    years = np.arange(2001, 2026)

    def summary(series: np.ndarray) -> dict:
        ts = trend_stats(years, annual_values(series, "mean"), 0.05)
        return {
            "senPerDecade": round(ts.sen_per_year * 10, 3),
            "mkP": round(ts.mk_p, 4),
            "status": ts.status,
            "direction": ts.direction,
            "olsPerDecade": round(ts.ols_per_year * 10, 3),
            "olsP": round(ts.ols_p, 4),
            "n": ts.n,
            "meanAnnualC": round(float(np.nanmean(annual_values(series, "mean"))), 2),
        }

    result = {
        "bbox": bbox,
        "years": [2001, 2025],
        "merra2_T2M": summary(ours_m),
        "gldas_Tair_f_inst": summary(gl_m),
        "monthlyCorrelation": float(np.corrcoef(ours_m, gl_m)[0, 1]),
        "meanDifferenceC_merra2_minus_gldas": float(np.mean(ours_m - gl_m)),
        "note": "Report only; served results are unchanged. GLDAS 0.25° native, cos(lat) weights, "
        "cells with centre inside the box.",
    }
    out.write_text(
        json.dumps(
            {
                "summary": result,
                "months": months,
                "merra2": ours_m.tolist(),
                "gldas": gl_m.tolist(),
            },
            indent=1,
        )
    )
    return result
