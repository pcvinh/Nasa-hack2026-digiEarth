"""One reader per dataset → (values[lat, lon] in served units, lat centres asc, lon centres asc).

Readers only mask fill values and convert units; they never fill, interpolate or smooth.
"""

from __future__ import annotations

import calendar
from collections.abc import Callable
from pathlib import Path

import numpy as np

Grid = tuple[np.ndarray, np.ndarray, np.ndarray]


def hours_in_month(year: int, month: int) -> int:
    return calendar.monthrange(year, month)[1] * 24


def read_imerg(path: Path, year: int, month: int) -> Grid:
    import h5py

    with h5py.File(path, "r") as f:
        g = f["Grid"]
        p = g["precipitation"]
        dims = p.attrs.get("DimensionNames", b"")
        dims = dims.decode() if isinstance(dims, bytes) else str(dims)
        if dims != "time,lon,lat":
            raise ValueError(f"IMERG: unexpected DimensionNames {dims!r}")
        fill = float(np.asarray(p.attrs["_FillValue"]).ravel()[0])
        a = p[0].astype(np.float32).T  # lon x lat -> lat x lon
        lat = g["lat"][:].astype(np.float64)
        lon = g["lon"][:].astype(np.float64)
    a[a == np.float32(fill)] = np.nan
    a *= hours_in_month(year, month)  # mm/hr -> mm/month
    return _ascending(a, lat, lon)


def read_merra2(path: Path, year: int, month: int) -> Grid:
    import netCDF4

    with netCDF4.Dataset(path) as n:
        v = n["T2M"]
        v.set_auto_maskandscale(False)
        a = np.asarray(v[0], dtype=np.float32)
        fill = float(getattr(v, "_FillValue", 1e15))
        lat = np.asarray(n["lat"][:], dtype=np.float64)
        lon = np.asarray(n["lon"][:], dtype=np.float64)
    a[(a == np.float32(fill)) | (a > 1e10)] = np.nan
    a -= np.float32(273.15)  # K -> °C
    return _ascending(a, lat, lon)


def read_gldas(path: Path, year: int, month: int) -> Grid:
    import netCDF4

    with netCDF4.Dataset(path) as n:
        v = n["SoilMoi0_10cm_inst"]
        v.set_auto_maskandscale(False)
        a = np.asarray(v[0], dtype=np.float32)
        fill = float(getattr(v, "_FillValue", -9999.0))
        lat = np.asarray(n["lat"][:], dtype=np.float64)
        lon = np.asarray(n["lon"][:], dtype=np.float64)
    a[a == np.float32(fill)] = np.nan
    return _ascending(a, lat, lon)


def read_mod13c2(path: Path, year: int, month: int) -> Grid:
    from pyhdf.SD import SD, SDC

    h = SD(str(path), SDC.READ)
    try:
        d = h.select("CMG 0.05 Deg Monthly NDVI")
        at = d.attributes()
        raw = d.get().astype(np.int32)
        d.endaccess()
    finally:
        h.end()
    lo, hi = at["valid_range"]
    fill = at["_FillValue"]
    scale = float(at["scale_factor"])  # MODIS convention: value = raw / scale_factor
    a = raw.astype(np.float32) / np.float32(scale)
    a[(raw == fill) | (raw < lo) | (raw > hi)] = np.nan
    ny, nx = a.shape
    # Grid: upper-left (-180, 90), 0.05°; rows run north -> south. Centres:
    lat = 90.0 - (np.arange(ny) + 0.5) * (180.0 / ny)
    lon = -180.0 + (np.arange(nx) + 0.5) * (360.0 / nx)
    return _ascending(a, lat, lon)


def _ascending(a: np.ndarray, lat: np.ndarray, lon: np.ndarray) -> Grid:
    if lat[0] > lat[-1]:
        a, lat = a[::-1], lat[::-1]
    if lon[0] > lon[-1]:
        a, lon = a[:, ::-1], lon[::-1]
    return np.ascontiguousarray(a, dtype=np.float32), lat.copy(), lon.copy()


READERS: dict[str, Callable[[Path, int, int], Grid]] = {
    "imerg": read_imerg,
    "merra2": read_merra2,
    "gldas": read_gldas,
    "mod13c2": read_mod13c2,
}
