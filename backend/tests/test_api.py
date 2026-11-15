from __future__ import annotations

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
    assert len(d["monthly"]) == 300 and len(d["annual"]) == 25
    assert d["annual"][-1] == {"year": 2025, "value": None}  # 3 months without source
    assert d["monthly"][-1]["value"] is None
    assert d["mannKendall"]["n"] == 24
    # annual sum of monthly values → slope per year = 12 × monthly slope
    assert d["mannKendall"]["senSlopePerDecade"] == pytest.approx(
        12 * TRUE_SLOPE_PER_YEAR * 10, rel=0.05
    )
    assert d["significance"]["status"] == "significant"
    assert d["significance"]["direction"] == "increasing"
    assert len(d["trendLines"]["sen"]) == 2
    assert d["dataStatus"] == "source_backed"
    assert any("2025" in c for c in d["interpretation"]["caveats"])


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


def test_analyze_point_in_always_missing_cell_is_insufficient(cubes, client, contract):
    r = client.post(
        "/api/v1/trends/analyze", json={"variableId": "ndvi", "region": {"point": [109.9, 10.0]}}
    )
    contract.check("post", "/trends/analyze", r)
    d = r.json()
    assert d["significance"]["status"] == "insufficient_data"
    assert d["trendLines"] == {"sen": [], "ols": []}
    assert all(m["value"] is None for m in d["monthly"])
    assert d["totalChange"]["value"] is None


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
        ({"variableId": "precipitation", "region": {"point": [105, 60]}}, "invalid_input", 400),
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
