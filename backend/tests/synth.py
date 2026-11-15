"""Synthetic cubes for API tests (small regional grid around the Mekong Delta)."""

from __future__ import annotations

import numpy as np

from edt.catalogue import cube_period
from edt.pipeline import cube as cubemod

LAT = np.arange(5.25, 15.0, 0.5)  # 20 rows, 5–15°N
LON = np.arange(100.25, 110.0, 0.5)  # 20 cols, 100–110°E
TRUE_SLOPE_PER_YEAR = 0.2  # in monthly units per year


def make_cube(
    settings,
    variable_id: str,
    *,
    trend: float = TRUE_SLOPE_PER_YEAR,
    no_source_last: int = 0,
    incomplete: bool = False,
    seed: int = 0,
) -> None:
    months = cubemod.month_list(*cube_period())
    path = settings.cube_dir / f"{variable_id}.zarr"
    cubemod.create(path, months, LAT, LON, {"variableId": variable_id})
    g = cubemod.open_cube(path, "a")
    rng = np.random.default_rng(seed)
    n = len(months)
    t = np.arange(n)
    season = 10 * np.sin(2 * np.pi * (t % 12) / 12)
    arr = 50 + season[:, None, None] + trend * (t // 12)[:, None, None]
    arr = arr + rng.normal(0, 0.5, (n, LAT.size, LON.size))
    arr[:, :, -2:] = np.nan  # an always-missing strip (e.g. sea for a land-only variable)
    status = np.full(n, cubemod.INGESTED, dtype=np.int8)
    if incomplete:
        arr[n // 2 :] = np.nan
        status[n // 2 :] = cubemod.NOT_INGESTED
    if no_source_last:
        arr[n - no_source_last :] = np.nan
        status[n - no_source_last :] = cubemod.NO_SOURCE
    g["value"][:] = arr.astype(np.float32)
    g["status"][:] = status
