"""Region → grid cells → cos(lat)-weighted regional mean series (ARCHITECTURE.md section 5.3)."""

from __future__ import annotations

import json
from dataclasses import dataclass, field
from functools import lru_cache
from pathlib import Path

import numpy as np
import shapely
from shapely.geometry import shape

PRESETS_PATH = Path(__file__).with_name("presets.geojson")
MIN_VALID_FRACTION = 0.5


@lru_cache
def presets() -> dict[str, dict]:
    data = json.loads(PRESETS_PATH.read_text())
    out = {}
    for f in data["features"]:
        p = dict(f["properties"])
        p.pop("vertexCount", None)
        p["geometry"] = f["geometry"]
        out[p["id"]] = p
    return out


@lru_cache
def preset_shape(preset_id: str):
    g = shape(presets()[preset_id]["geometry"])
    shapely.prepare(g)
    return g


@dataclass
class Selection:
    name: str
    bbox: list[float]
    representativeness: str  # area_mean | single_cell
    preset_id: str | None
    iy: np.ndarray  # selected cell row indices
    ix: np.ndarray  # selected cell column indices
    caveats: list[str] = field(default_factory=list)


def _wrap(d: np.ndarray) -> np.ndarray:
    return (d + 180.0) % 360.0 - 180.0


def nearest_cell(lat: np.ndarray, lon: np.ndarray, x: float, y: float) -> tuple[int, int]:
    """Cell containing (x, y) on a regular grid = nearest cell centre (lon wraps)."""
    iy = int(np.argmin(np.abs(lat - y)))
    ix = int(np.argmin(np.abs(_wrap(lon - x))))
    return iy, ix


def select_cells(region: dict, lat: np.ndarray, lon: np.ndarray) -> Selection:
    """region: contract RegionInput as dict. Caller has validated exactly-one-of."""
    if region.get("presetId"):
        p = presets()[region["presetId"]]
        geom = preset_shape(p["id"])
        w, s, e, n = p["bbox"]
        ys = np.nonzero((lat >= s) & (lat <= n))[0]
        xs = np.nonzero((lon >= w) & (lon <= e))[0]
        gx, gy = np.meshgrid(lon[xs], lat[ys])
        inside = shapely.contains_xy(geom, gx, gy) if ys.size and xs.size else np.zeros((0, 0))
        iy, ix = np.nonzero(inside)
        sel = Selection(p["name"], list(p["bbox"]), "area_mean", p["id"], ys[iy], xs[ix])
        if sel.iy.size == 0:
            cy, cx = nearest_cell(lat, lon, *p["center"])
            sel.iy, sel.ix = np.array([cy]), np.array([cx])
            sel.caveats.append(
                "The region is smaller than one grid cell, so the single cell containing its "
                "centre is used."
            )
        return sel

    if region.get("bbox") is not None:
        w, s, e, n = region["bbox"]
        ys = np.nonzero((lat >= s) & (lat <= n))[0]
        xs = np.nonzero((lon >= w) & (lon <= e))[0]
        name = f"Box {w:g}°, {s:g}° to {e:g}°, {n:g}°"
        if ys.size and xs.size:
            gy, gx = np.meshgrid(ys, xs, indexing="ij")
            return Selection(name, [w, s, e, n], "area_mean", None, gy.ravel(), gx.ravel())
        cy, cx = nearest_cell(lat, lon, (w + e) / 2, (s + n) / 2)
        return Selection(
            name,
            [w, s, e, n],
            "area_mean",
            None,
            np.array([cy]),
            np.array([cx]),
            [
                "The box is smaller than one grid cell, so the single cell containing its centre "
                "is used."
            ],
        )

    x, y = region["point"]
    cy, cx = nearest_cell(lat, lon, x, y)
    name = f"Point {abs(y):.2f}°{'N' if y >= 0 else 'S'}, {abs(x):.2f}°{'E' if x >= 0 else 'W'}"
    return Selection(
        name,
        [x, y, x, y],
        "single_cell",
        None,
        np.array([cy]),
        np.array([cx]),
        [
            "This is the value of one grid cell (about 50 km across) containing the point, not "
            "the exact spot."
        ],
    )


def regional_series(
    cube: np.ndarray, lat_sub: np.ndarray, sel_iy: np.ndarray, sel_ix: np.ndarray
) -> tuple[np.ndarray, np.ndarray, int, int]:
    """cube: (time, ny, nx) slice; sel_* are indices into the slice; lat_sub its latitudes.

    Cells with no data in any month of the slice (outside the dataset's domain, e.g. sea for
    a land-only variable) are dropped. Returns (mean, validFraction, cellCount, droppedCount).
    A month with < 50% of the region's cells valid → NaN.
    """
    vals = cube[:, sel_iy, sel_ix]  # (time, cells)
    has_data = np.isfinite(vals).any(axis=0)
    dropped = int((~has_data).sum())
    vals = vals[:, has_data]
    w = np.cos(np.deg2rad(lat_sub[sel_iy[has_data]]))
    ncell = vals.shape[1]
    if ncell == 0:
        nt = cube.shape[0]
        return np.full(nt, np.nan), np.full(nt, np.nan), 0, dropped
    valid = np.isfinite(vals)
    frac = valid.sum(axis=1) / ncell
    wsum = (valid * w).sum(axis=1)
    with np.errstate(invalid="ignore", divide="ignore"):
        mean = np.where(valid, vals, 0.0) @ w / wsum
    mean[frac < MIN_VALID_FRACTION] = np.nan
    return mean, frac, ncell, dropped
