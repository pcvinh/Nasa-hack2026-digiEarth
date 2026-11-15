"""Per-variable Zarr cube: value[time, lat, lon] float32 (NaN = missing) for the fixed cube period.

A pre-allocated cube makes ingest resumable: `status[t]` is 0 = not ingested, 1 = ingested,
2 = no granule exists at the source for this month.
"""

from __future__ import annotations

from pathlib import Path

import numpy as np
import zarr

NOT_INGESTED, INGESTED, NO_SOURCE = 0, 1, 2


def month_list(start: str, end: str) -> list[str]:
    y, m = map(int, start.split("-"))
    ey, em = map(int, end.split("-"))
    out = []
    while (y, m) <= (ey, em):
        out.append(f"{y:04d}-{m:02d}")
        m += 1
        if m == 13:
            y, m = y + 1, 1
    return out


def create(path: Path, months: list[str], lat: np.ndarray, lon: np.ndarray, attrs: dict) -> None:
    g = zarr.open_group(str(path), mode="w")
    nt, ny, nx = len(months), len(lat), len(lon)
    g.create_array(
        "value",
        shape=(nt, ny, nx),
        chunks=(12, min(ny, 60), min(nx, 64)),
        dtype="float32",
        fill_value=np.nan,
        dimension_names=("time", "lat", "lon"),
    )
    g.create_array("status", shape=(nt,), dtype="int8", fill_value=0, dimension_names=("time",))
    g.create_array("lat", shape=(ny,), dtype="float64", dimension_names=("lat",))[:] = lat
    g.create_array("lon", shape=(nx,), dtype="float64", dimension_names=("lon",))[:] = lon
    g.create_array("time", shape=(nt,), dtype="<U7", dimension_names=("time",))[:] = np.array(
        months
    )
    g.attrs.update(attrs)


def open_cube(path: Path, mode: str = "r") -> zarr.Group:
    return zarr.open_group(str(path), mode=mode)


def write_month(g: zarr.Group, t: int, values: np.ndarray) -> None:
    g["value"][t] = values.astype(np.float32)
    g["status"][t] = INGESTED


def mark_no_source(g: zarr.Group, t: int) -> None:
    g["status"][t] = NO_SOURCE
