from __future__ import annotations

import pytest
from contract import ContractValidator
from fastapi.testclient import TestClient

from edt.api.app import create_app
from edt.config import Settings


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
