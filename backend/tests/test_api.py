from __future__ import annotations

import os

import pytest

MEKONG = {"variableId": "precipitation", "region": {"presetId": "mekong-delta"}}


def test_variables_unavailable_without_cubes(client, contract):
    r = client.get("/api/v1/variables")
    contract.check("get", "/variables", r)
    items = r.json()["items"]
    assert len(items) == 4
    assert all(i["status"] == "unavailable" and i["unavailableReason"] for i in items)


def test_variables_with_cubes_and_topic_filter(cubes, client, contract):
    r = client.get("/api/v1/variables")
    contract.check("get", "/variables", r)
    by_id = {i["id"]: i for i in r.json()["items"]}
    assert by_id["precipitation"]["status"] == "source_backed"
    assert by_id["precipitation"]["coverage"] == {
        "start": "2001-01",
        "end": "2025-09",
        "landOnly": False,
    }
    assert by_id["ndvi"]["coverage"]["landOnly"] is True
    r = client.get("/api/v1/variables?topic=heat")
    contract.check("get", "/variables", r)
    assert [i["id"] for i in r.json()["items"]] == ["air_temperature"]


def test_incomplete_cube_is_unavailable(settings, client):
    from synth import make_cube

    make_cube(settings, "ndvi", incomplete=True)
    items = {i["id"]: i for i in client.get("/api/v1/variables").json()["items"]}
    assert items["ndvi"]["status"] == "unavailable"
    assert "not complete" in items["ndvi"]["unavailableReason"]


def test_regions(client, contract):
    r = client.get("/api/v1/regions")
    contract.check("get", "/regions", r)
    ids = [i["id"] for i in r.json()["items"]]
    assert ids == ["mekong-delta", "central-java", "johor", "amazon-central", "sahel"]
    r = client.get("/api/v1/regions?q=viet")
    assert [i["id"] for i in r.json()["items"]] == ["mekong-delta"]
    r = client.get("/api/v1/regions/mekong-delta")
    contract.check("get", "/regions/mekong-delta", r)
    assert r.json()["geometry"]["type"] in ("Polygon", "MultiPolygon")
    r = client.get("/api/v1/regions/atlantis")
    assert r.status_code == 404
    contract.check("get", "/regions/atlantis", r)


def test_analyze_preset_recovers_trend_and_validates(cubes, client, contract):
    from synth import TRUE_SLOPE_PER_YEAR

    r = client.post("/api/v1/trends/analyze", json=MEKONG)
    assert r.status_code == 200, r.text
    contract.check("post", "/trends/analyze", r)
    d = r.json()
    assert d["region"]["representativeness"] == "area_mean"
    assert d["region"]["cellCount"] > 5
    # precipitation has no source for 2025-10..12 → default endYear is the last complete year
    assert d["period"] == {"startYear": 2001, "endYear": 2024}
    assert len(d["monthly"]) == 288 and len(d["annual"]) == 24
    assert d["annual"][-1]["year"] == 2024 and d["annual"][-1]["value"] is not None
    assert d["mannKendall"]["n"] == 24
    assert "2001 to 2024" in d["interpretation"]["summary"]
    assert not any("No source data" in c for c in d["interpretation"]["caveats"])
    # annual sum of monthly values → slope per year = 12 × monthly slope
    assert d["mannKendall"]["senSlopePerDecade"] == pytest.approx(
        12 * TRUE_SLOPE_PER_YEAR * 10, rel=0.05
    )
    assert d["significance"]["status"] == "significant"
    assert d["significance"]["direction"] == "increasing"
    assert len(d["trendLines"]["sen"]) == 2
    assert d["dataStatus"] == "source_backed"


def test_default_end_year_is_2025_for_complete_variable(cubes, client, contract):
    r = client.post(
        "/api/v1/trends/analyze",
        json={"variableId": "air_temperature", "region": {"presetId": "mekong-delta"}},
    )
    contract.check("post", "/trends/analyze", r)
    d = r.json()
    assert d["period"] == {"startYear": 2001, "endYear": 2025}
    assert d["annual"][-1]["year"] == 2025 and "2001 to 2025" in d["interpretation"]["summary"]


def test_explicit_end_year_still_works_and_reports_missing_months(cubes, client, contract):
    r = client.post("/api/v1/trends/analyze", json={**MEKONG, "endYear": 2025})
    assert r.status_code == 200, r.text
    contract.check("post", "/trends/analyze", r)
    d = r.json()
    assert d["period"]["endYear"] == 2025 and len(d["annual"]) == 25
    assert d["annual"][-1] == {"year": 2025, "value": None}  # 3 months without source
    assert d["monthly"][-1]["value"] is None
    assert d["mannKendall"]["n"] == 24
    assert any("2025" in c for c in d["interpretation"]["caveats"])
    assert any("No source data" in c for c in d["interpretation"]["caveats"])


def test_default_end_year_must_be_after_start_year(cubes, client, contract):
    r = client.post("/api/v1/trends/analyze", json={**MEKONG, "startYear": 2024})
    assert r.status_code == 400 and r.json()["code"] == "invalid_input"
    contract.check("post", "/trends/analyze", r)


def test_analyze_bbox_point_and_dropped_cells(cubes, client, contract):
    r = client.post(
        "/api/v1/trends/analyze",
        json={"variableId": "ndvi", "region": {"bbox": [108.0, 9.0, 110.0, 11.0]}},
    )
    contract.check("post", "/trends/analyze", r)
    d = r.json()
    assert d["region"]["cellCount"] == 4 * 2  # 4 rows × 2 valid columns; 2 columns dropped
    assert any(
        "left out because the dataset has no data" in c for c in d["interpretation"]["caveats"]
    )
    r = client.post(
        "/api/v1/trends/analyze",
        json={
            "variableId": "air_temperature",
            "region": {"point": [105.1, 10.1]},
            "startYear": 2005,
            "endYear": 2020,
        },
    )
    contract.check("post", "/trends/analyze", r)
    d = r.json()
    assert d["region"]["representativeness"] == "single_cell"
    assert d["region"]["cellCount"] == 1
    assert d["period"] == {"startYear": 2005, "endYear": 2020}
    assert len(d["annual"]) == 16


def test_point_in_always_missing_cell_is_data_unavailable(cubes, client, contract):
    r = client.post(
        "/api/v1/trends/analyze",
        json={"variableId": "ndvi", "region": {"point": [109.9, 10.0]}},
    )
    assert r.status_code == 400, r.text
    contract.check("post", "/trends/analyze", r)
    d = r.json()
    assert d["code"] == "data_unavailable"
    assert "no valid data for this point" in d["error"] and "land-only" in d["error"]


def test_bbox_with_no_valid_cells_is_data_unavailable(cubes, client, contract):
    # synthetic cubes have an always-missing strip at the two easternmost columns (109.25–110°E)
    r = client.post(
        "/api/v1/trends/analyze",
        json={"variableId": "ndvi", "region": {"bbox": [109.3, 8.0, 109.9, 12.0]}},
    )
    assert r.status_code == 400 and r.json()["code"] == "data_unavailable"
    assert "region" in r.json()["error"]
    contract.check("post", "/trends/analyze", r)


@pytest.mark.skipif(not os.environ.get("DATA_ROOT"), reason="needs the real data")
@pytest.mark.parametrize(
    "variable,region",
    [
        ("ndvi", {"point": [0.0, 0.0]}),
        ("soil_moisture", {"point": [-30.0, 0.0]}),
        ("ndvi", {"bbox": [-30.0, -10.0, -20.0, 0.0]}),
    ],
)
def test_real_ocean_is_data_unavailable_not_cellcount_zero(contract, variable, region):
    from fastapi.testclient import TestClient

    from edt.api.app import create_app
    from edt.config import load_settings

    c = TestClient(create_app(load_settings()))
    r = c.post("/api/v1/trends/analyze", json={"variableId": variable, "region": region})
    assert r.status_code == 400, r.text
    assert r.json()["code"] == "data_unavailable"
    contract.check("post", "/trends/analyze", r)


def test_short_period_is_insufficient(cubes, client, contract):
    r = client.post("/api/v1/trends/analyze", json={**MEKONG, "startYear": 2010, "endYear": 2015})
    contract.check("post", "/trends/analyze", r)
    assert r.json()["significance"]["status"] == "insufficient_data"


@pytest.mark.parametrize(
    "body,code,status",
    [
        ({"variableId": "precipitation", "region": {}}, "invalid_input", 400),
        (
            {
                "variableId": "precipitation",
                "region": {"presetId": "mekong-delta", "point": [105, 10]},
            },
            "invalid_input",
            400,
        ),
        ({"variableId": "snowfall", "region": {"presetId": "mekong-delta"}}, "invalid_input", 400),
        ({"variableId": "precipitation", "region": {"presetId": "atlantis"}}, "not_found", 404),
        ({**MEKONG, "startYear": 1990}, "invalid_input", 400),
        ({**MEKONG, "startYear": 2020, "endYear": 2010}, "invalid_input", 400),
        (
            {"variableId": "precipitation", "region": {"bbox": [110, 0, 100, 10]}},
            "invalid_input",
            400,
        ),
        ({"variableId": "precipitation", "region": {"point": [105, 60]}}, "data_unavailable", 400),
        ({**MEKONG, "alpha": 0.5}, "invalid_input", 400),
        ({"region": {"presetId": "mekong-delta"}}, "invalid_input", 400),
    ],
)
def test_analyze_errors(cubes, client, contract, body, code, status):
    r = client.post("/api/v1/trends/analyze", json=body)
    assert r.status_code == status, r.text
    assert r.json()["code"] == code
    contract.check("post", "/trends/analyze", r)


def test_missing_cube_is_data_unavailable(client, contract):
    r = client.post("/api/v1/trends/analyze", json=MEKONG)
    assert r.status_code == 400 and r.json()["code"] == "data_unavailable"
    contract.check("post", "/trends/analyze", r)


def test_trend_maps(cubes, client, contract):
    from edt.catalogue import get_variable
    from edt.pipeline.maps import build_map

    r = client.get("/api/v1/trend-maps/precipitation")
    assert r.status_code == 404
    contract.check("get", "/trend-maps/precipitation", r)
    build_map(cubes, get_variable("precipitation"))
    r = client.get("/api/v1/trend-maps/precipitation")
    contract.check("get", "/trend-maps/precipitation", r)
    d = r.json()
    assert d["period"] == {"startYear": 2001, "endYear": 2024}
    assert d["bounds"] == [100.0, 5.0, 110.0, 15.0]
    assert d["legend"]["min"] == -d["legend"]["max"]
    img = client.get(d["imageUrl"])
    assert img.status_code == 200 and img.headers["content-type"] == "image/png"
    from io import BytesIO

    from PIL import Image

    im = Image.open(BytesIO(img.content))
    assert im.size == (20, 20) and im.mode == "RGBA"
    assert im.getpixel((19, 0))[3] == 0  # always-missing column is transparent
    assert im.getpixel((0, 0))[3] == round(0.9 * 255)  # strong synthetic trend → significant


@pytest.mark.parametrize(
    "region", ["mekong-delta", "central-java", "johor", "amazon-central", "sahel"]
)
def test_guide_suggests_for_each_region_type(client, contract, region):
    r = client.post(
        "/api/v1/guide/chat", json={"message": "What should I look at?", "regionId": region}
    )
    contract.check("post", "/guide/chat", r)
    d = r.json()
    assert 1 <= len(d["suggestions"]) <= 3 and d["mode"] == "rules"
    assert {a["type"] for a in d["actions"]} <= {
        "select_variable",
        "select_region",
        "run_analysis",
        "show_trend_map",
    }


@pytest.mark.parametrize(
    "msg",
    [
        "Can you predict rice yield next year?",
        "Why is it getting hotter?",
        "What will rainfall be in 2050?",
    ],
)
def test_guide_refuses_unsupported(client, contract, msg):
    r = client.post("/api/v1/guide/chat", json={"message": msg, "regionId": "mekong-delta"})
    contract.check("post", "/guide/chat", r)
    d = r.json()
    assert "can't" in d["reply"]
    assert all(a["type"] != "run_analysis" for a in d["actions"])


def test_guide_keywords_and_no_numbers(client, contract):
    r = client.post("/api/v1/guide/chat", json={"message": "Is the forest getting less green?"})
    contract.check("post", "/guide/chat", r)
    d = r.json()
    assert d["suggestions"][0]["variableId"] == "ndvi"
    assert not any(ch.isdigit() for ch in d["reply"])
    r = client.post("/api/v1/guide/chat", json={"message": "x", "regionId": "nowhere"})
    assert r.status_code == 400
    contract.check("post", "/guide/chat", r)
    r = client.post("/api/v1/guide/chat", json={"message": ""})
    assert r.status_code == 400


def test_sessions_round_trip(client, contract):
    r = client.post("/api/v1/sessions", json={"title": "Mekong rain", "state": {"a": [1, 2]}})
    assert r.status_code == 201
    contract.check("post", "/sessions", r)
    sid = r.json()["id"]
    r = client.get(f"/api/v1/sessions/{sid}")
    contract.check("get", f"/sessions/{sid}", r)
    assert r.json()["state"] == {"a": [1, 2]}
    client.post("/api/v1/sessions", json={"title": "Second", "state": {}})
    r = client.put(f"/api/v1/sessions/{sid}", json={"title": "Renamed", "state": {"b": True}})
    contract.check("put", f"/sessions/{sid}", r)
    assert r.json()["title"] == "Renamed" and r.json()["updatedAt"] >= r.json()["createdAt"]
    r = client.get("/api/v1/sessions")
    contract.check("get", "/sessions", r)
    assert [i["title"] for i in r.json()["items"]][0] == "Renamed"  # newest first
    r = client.get("/api/v1/sessions/nope")
    assert r.status_code == 404
    contract.check("get", "/sessions/nope", r)
    r = client.put("/api/v1/sessions/nope", json={"title": "x", "state": {}})
    assert r.status_code == 404


def test_sessions_reject_large_state(client, contract):
    r = client.post("/api/v1/sessions", json={"title": "big", "state": {"x": "a" * 300_000}})
    assert r.status_code == 400 and r.json()["code"] == "invalid_input"
    contract.check("post", "/sessions", r)


def test_api_adds_borderline_caveat_for_p_near_alpha(cubes, client, contract):
    """A series built so the Mann-Kendall p lands near 0.05 gets the caveat via the API."""
    import numpy as np
    from synth import LAT, LON

    from edt.pipeline import cube as cubemod

    settings = cubes
    g = cubemod.open_cube(settings.cube_dir / "air_temperature.zarr", "a")
    # annual means: weak trend + noise tuned (seeded) so that 0.03 <= p <= 0.07
    for seed in range(200):
        rng = np.random.default_rng(seed)
        annual = 20 + 0.03 * np.arange(25) + rng.normal(0, 0.25, 25)
        from edt.stats.core import trend_stats

        p = trend_stats(np.arange(2001, 2026), annual).mk_p
        if 0.04 <= p <= 0.06:
            break
    else:
        pytest.fail("no seed found")
    arr = np.repeat(annual, 12)[:, None, None] * np.ones((300, LAT.size, LON.size))
    arr[:, :, -2:] = np.nan
    g["value"][:] = arr.astype("float32")
    r = client.post(
        "/api/v1/trends/analyze",
        json={"variableId": "air_temperature", "region": {"presetId": "mekong-delta"}},
    )
    contract.check("post", "/trends/analyze", r)
    d = r.json()
    assert abs(d["mannKendall"]["pValue"] - 0.05) <= 0.02
    assert any("close to the significance threshold" in c for c in d["interpretation"]["caveats"])


NOTE = "reanalysis"


@pytest.mark.parametrize(
    "region", [{"presetId": "johor"}, {"point": [105.1, 10.1]}, {"bbox": [102.0, 8.0, 106.0, 12.0]}]
)
def test_air_temperature_results_carry_reanalysis_note(cubes, client, contract, region):
    r = client.post(
        "/api/v1/trends/analyze", json={"variableId": "air_temperature", "region": region}
    )
    contract.check("post", "/trends/analyze", r)
    d = r.json()
    assert any(NOTE in c and "station records" in c for c in d["interpretation"]["caveats"])
    assert any(NOTE in n and "station records" in n for n in d["provenance"]["qualityNotes"])


def test_other_variables_have_no_quality_notes_or_reanalysis_caveat(cubes, client, contract):
    for vid in ("precipitation", "soil_moisture", "ndvi"):
        r = client.post(
            "/api/v1/trends/analyze", json={"variableId": vid, "region": {"presetId": "johor"}}
        )
        d = r.json()
        assert d["provenance"]["qualityNotes"] == []
        assert not any(NOTE in c for c in d["interpretation"]["caveats"])


def test_variables_and_trend_map_provenance_include_quality_notes(cubes, client, contract):
    from edt.catalogue import get_variable
    from edt.pipeline.maps import build_map

    items = {i["id"]: i for i in client.get("/api/v1/variables").json()["items"]}
    assert items["air_temperature"]["provenance"]["qualityNotes"]
    assert items["ndvi"]["provenance"]["qualityNotes"] == []
    r = client.get("/api/v1/variables")
    contract.check("get", "/variables", r)
    build_map(cubes, get_variable("air_temperature"))
    r = client.get("/api/v1/trend-maps/air_temperature")
    contract.check("get", "/trend-maps/air_temperature", r)
    assert r.json()["provenance"]["qualityNotes"]


@pytest.mark.parametrize(
    "variable,palette",
    [("precipitation", "diverging_brown_green"), ("air_temperature", "diverging_blue_red")],
)
def test_trend_map_legend_color_stops_match_the_png(cubes, client, contract, variable, palette):
    import re
    from io import BytesIO

    from PIL import Image

    from edt.catalogue import get_variable
    from edt.pipeline.maps import build_map

    build_map(cubes, get_variable(variable))
    r = client.get(f"/api/v1/trend-maps/{variable}")
    contract.check("get", f"/trend-maps/{variable}", r)
    legend = r.json()["legend"]
    stops = legend["colorStops"]
    assert legend["palette"] == palette and len(stops) >= 2
    assert all(re.fullmatch(r"#[0-9A-F]{6}", c) for c in stops)
    # cells at or beyond the colour limit (top 2% of |slope|, all positive here) are clipped to
    # the end of the palette, so their pixel colour must equal the last colour stop
    im = Image.open(BytesIO(client.get(r.json()["imageUrl"]).content)).convert("RGBA")
    drawn = [p for p in im.getdata() if p[3] > 0]
    assert drawn
    assert any("#{:02X}{:02X}{:02X}".format(*p[:3]) == stops[-1] for p in drawn)
    assert all("#{:02X}{:02X}{:02X}".format(*p[:3]) != stops[0] for p in drawn)
    assert stops[0] != stops[-1]


def test_color_stops_are_sampled_from_the_palette_endpoints():
    import matplotlib
    from matplotlib.colors import to_hex

    from edt.pipeline.maps import PALETTES, color_stops

    for name, cm in PALETTES.items():
        s = color_stops(name)
        assert len(s) == 11
        assert s[0] == to_hex(matplotlib.colormaps[cm](0.0)).upper()
        assert s[-1] == to_hex(matplotlib.colormaps[cm](1.0)).upper()


def test_trend_map_without_stored_color_stops_falls_back_to_palette(cubes, client, contract):
    import json

    from edt.catalogue import get_variable
    from edt.pipeline.maps import build_map

    build_map(cubes, get_variable("ndvi"))
    meta_path = cubes.maps_dir / "ndvi.json"
    meta = json.loads(meta_path.read_text())
    del meta["legend"]["colorStops"]
    meta_path.write_text(json.dumps(meta))
    r = client.get("/api/v1/trend-maps/ndvi")
    contract.check("get", "/trend-maps/ndvi", r)
    assert len(r.json()["legend"]["colorStops"]) == 11
