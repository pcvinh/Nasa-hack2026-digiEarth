from __future__ import annotations

import sys
from pathlib import Path

import pytest
from fastapi.testclient import TestClient

from edt.api.app import create_app
from edt.config import Settings

sys.path.insert(0, str(Path(__file__).parent))

from contract import ContractValidator  # noqa: E402


@pytest.fixture
def settings(tmp_path) -> Settings:
    return Settings(
        data_root=tmp_path,
        session_store="sqlite",
        allowed_origins=("http://localhost:5173",),
        guide_llm="off",
    )


@pytest.fixture
def client(settings) -> TestClient:
    return TestClient(create_app(settings))


@pytest.fixture(scope="session")
def contract() -> ContractValidator:
    return ContractValidator()


@pytest.fixture
def cubes(settings):
    from synth import make_cube

    for vid in ("precipitation", "air_temperature", "soil_moisture", "ndvi"):
        make_cube(settings, vid, no_source_last=3 if vid == "precipitation" else 0)
    return settings
