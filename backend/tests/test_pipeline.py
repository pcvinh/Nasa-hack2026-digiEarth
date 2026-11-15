from __future__ import annotations

import numpy as np
import pytest

from edt.pipeline.coarsen import block_mean, coarsen_coords
from edt.pipeline.cube import month_list
from edt.pipeline.readers import _ascending, hours_in_month


def test_hours_in_month_including_leap_february():
    assert hours_in_month(2024, 2) == 696
    assert hours_in_month(2023, 2) == 672
    assert hours_in_month(2020, 7) == 744


def test_block_mean_known_values_and_half_rule():
    a = np.arange(16, dtype=np.float32).reshape(4, 4)
    out = block_mean(a, 2)
    assert out.tolist() == [[2.5, 4.5], [10.5, 12.5]]
    a[0, 0] = a[0, 1] = np.nan  # 2 of 4 valid = 50% → kept
    assert block_mean(a, 2)[0, 0] == pytest.approx((4 + 5) / 2)
    a[1, 0] = np.nan  # 1 of 4 valid → NaN
    assert np.isnan(block_mean(a, 2)[0, 0])


def test_block_mean_rejects_non_divisible():
    with pytest.raises(ValueError):
        block_mean(np.zeros((5, 4)), 2)


def test_coarsen_coords():
    c = np.array([-0.15, -0.05, 0.05, 0.15])
    assert np.allclose(coarsen_coords(c, 2), [-0.1, 0.1])


def test_orientation_flip_to_ascending():
    a = np.array([[1, 2], [3, 4]], dtype=np.float32)  # row0 = north
    out, lat, lon = _ascending(a, np.array([10.0, -10.0]), np.array([5.0, -5.0]))
    assert lat.tolist() == [-10.0, 10.0] and lon.tolist() == [-5.0, 5.0]
    assert out.tolist() == [[4, 3], [2, 1]]


def test_imerg_transpose(tmp_path):
    import h5py

    from edt.pipeline.readers import read_imerg

    p = tmp_path / "imerg.h5"
    lon = np.array([-179.95, 179.95])
    lat = np.array([-89.95, 0.05, 89.95])
    data = np.zeros((1, 2, 3), dtype=np.float32)  # time, lon, lat
    data[0, 1, 2] = 1.0  # lon=179.95, lat=89.95
    data[0, 0, 0] = -9999.9
    with h5py.File(p, "w") as f:
        g = f.create_group("Grid")
        d = g.create_dataset("precipitation", data=data)
        d.attrs["DimensionNames"] = b"time,lon,lat"
        d.attrs["_FillValue"] = np.float32(-9999.9)
        g["lat"], g["lon"] = lat, lon
    a, la, lo = read_imerg(p, 2024, 2)
    assert a.shape == (3, 2)
    assert a[2, 1] == pytest.approx(696.0)  # 1 mm/hr × 696 h
    assert np.isnan(a[0, 0])


def test_month_list():
    m = month_list("2001-11", "2002-02")
    assert m == ["2001-11", "2001-12", "2002-01", "2002-02"]


def test_merra2_kelvin_to_celsius_and_fill(tmp_path):
    import netCDF4

    from edt.pipeline.readers import read_merra2

    p = tmp_path / "m.nc4"
    with netCDF4.Dataset(p, "w") as n:
        n.createDimension("time", 1)
        n.createDimension("lat", 2)
        n.createDimension("lon", 2)
        n.createVariable("lat", "f8", ("lat",))[:] = [-90.0, 90.0]
        n.createVariable("lon", "f8", ("lon",))[:] = [-180.0, 179.375]
        v = n.createVariable("T2M", "f4", ("time", "lat", "lon"), fill_value=1e15)
        v[:] = np.array([[[273.15, 300.0], [250.0, 1e15]]], dtype=np.float32)
    a, lat, lon = read_merra2(p, 2020, 7)
    assert a[0, 0] == pytest.approx(0.0, abs=1e-4)
    assert a[0, 1] == pytest.approx(26.85, abs=1e-3)
    assert np.isnan(a[1, 1])


def test_ndvi_scale_fill_and_north_up_flip(tmp_path):
    from pyhdf.SD import SD, SDC

    from edt.pipeline.readers import read_mod13c2

    p = tmp_path / "m.hdf"
    h = SD(str(p), SDC.WRITE | SDC.CREATE)
    d = h.create("CMG 0.05 Deg Monthly NDVI", SDC.INT16, (2, 2))
    d[:] = np.array([[5000, -3000], [-2500, 10000]], dtype=np.int16)  # row 0 = north
    d.valid_range = [-2000, 10000]
    d.setfillvalue(-3000)
    d.scale_factor = 10000.0
    d.endaccess()
    h.end()
    a, lat, lon = read_mod13c2(p, 2020, 7)
    assert lat.tolist() == [-45.0, 45.0] and lon.tolist() == [-90.0, 90.0]
    assert np.isnan(a[0, 0])  # -2500 outside valid range (south-west after flip)
    assert a[0, 1] == pytest.approx(1.0)
    assert a[1, 0] == pytest.approx(0.5)
    assert np.isnan(a[1, 1])  # fill
