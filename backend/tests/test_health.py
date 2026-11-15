from __future__ import annotations

import pytest
from fastapi.testclient import TestClient
from openapi_core.exceptions import OpenAPIError

from edt.api.app import create_app
from edt.config import Settings


def test_health_degraded_without_cubes_validates_contract(client, contract):
    r = client.get("/api/v1/health")
    assert r.status_code == 200
    contract.check("get", "/health", r)
    body = r.json()
    assert body["status"] == "degraded"
    assert {v["status"] for v in body["variables"]} == {"unavailable"}
    assert [v["id"] for v in body["variables"]] == [
        "precipitation",
        "air_temperature",
        "soil_moisture",
        "ndvi",
    ]


def test_health_ok_when_all_cubes_exist(settings, contract):
    for vid in ("precipitation", "air_temperature", "soil_moisture", "ndvi"):
        (settings.cube_dir / f"{vid}.zarr").mkdir(parents=True)
    (settings.data_root / "manifest.json").write_text('{"dataVersion": "2026-11-20.1"}')
    r = TestClient(create_app(settings)).get("/api/v1/health")
    contract.check("get", "/health", r)
    assert r.json()["status"] == "ok"
    assert r.json()["dataVersion"] == "2026-11-20.1"


def test_unknown_route_uses_contract_error_shape(client, contract):
    r = client.get("/api/v1/nope")
    assert r.status_code == 404
    assert r.json() == {"error": "Not Found", "code": "not_found"}


def test_cors_allows_only_configured_origin(client):
    ok = client.get("/api/v1/health", headers={"Origin": "http://localhost:5173"})
    assert ok.headers.get("access-control-allow-origin") == "http://localhost:5173"
    bad = client.get("/api/v1/health", headers={"Origin": "http://evil.example"})
    assert "access-control-allow-origin" not in bad.headers


def test_load_settings_requires_absolute_data_root(monkeypatch):
    from edt.config import load_settings

    monkeypatch.setenv("DATA_ROOT", "relative/path")
    with pytest.raises(RuntimeError):
        load_settings()
    monkeypatch.delenv("DATA_ROOT")
    with pytest.raises(RuntimeError):
        load_settings()
    assert Settings  # imported for type reference


def test_contract_helper_rejects_a_violating_response(contract):
    class Bad:
        content = b'{"status": "ok"}'
        status_code = 200
        headers = {"content-type": "application/json"}

    with pytest.raises(OpenAPIError):
        contract.check("get", "/health", Bad())
