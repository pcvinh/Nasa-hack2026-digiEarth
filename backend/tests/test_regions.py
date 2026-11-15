from __future__ import annotations

import numpy as np
import pytest

from edt.regions.select import presets, regional_series, select_cells


def test_presets_have_contract_fields_and_small_geometry():
    for p in presets().values():
        assert {
            "id",
            "name",
            "regionType",
            "description",
            "center",
            "bbox",
            "geometry",
            "geometrySource",
            "suggestedVariableIds",
        } <= set(p)
        coords = str(p["geometry"]["coordinates"]).count("[") - 1
        assert coords < 1500


def test_cos_lat_weighting():
    lat = np.array([0.0, 60.0])
    cube = np.array([[[1.0], [3.0]]])  # time=1, lat=2, lon=1
    mean, frac, n, dropped = regional_series(cube, lat, np.array([0, 1]), np.array([0, 0]))
    # weights 1 and 0.5 → (1*1 + 3*0.5) / 1.5
    assert mean[0] == pytest.approx(2.5 / 1.5)
    assert frac[0] == 1 and n == 2 and dropped == 0


def test_month_with_under_half_valid_cells_is_null():
    lat = np.zeros(3)
    cube = np.array([[[1.0, np.nan, np.nan]], [[1.0, 2.0, np.nan]], [[1, 2, 3.0]]])
    cube = cube.reshape(3, 1, 3)
    mean, frac, n, _ = regional_series(cube, lat, np.zeros(3, int), np.arange(3))
    assert np.isnan(mean[0]) and mean[1] == pytest.approx(1.5) and mean[2] == pytest.approx(2)


def test_centre_in_polygon_and_tiny_region_fallback():
    lat = np.arange(-89.75, 90, 0.5)
    lon = np.arange(-179.75, 180, 0.5)
    sel = select_cells({"presetId": "sahel"}, lat, lon)
    assert sel.iy.size == 12 * 104  # 6° × 52° at 0.5°
    sel = select_cells({"bbox": [105.01, 10.01, 105.02, 10.02]}, lat, lon)
    assert sel.iy.size == 1 and sel.caveats
    sel = select_cells({"point": [179.99, 0.1]}, lat, lon)
    assert lon[sel.ix[0]] == pytest.approx(179.75)
