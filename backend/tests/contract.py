"""Validate real API responses against contracts/trend-detective-api.openapi.yaml."""

from __future__ import annotations

from openapi_core import OpenAPI
from openapi_core.testing import MockRequest, MockResponse

from edt.config import CONTRACT_PATH

HOST_URL = "http://localhost:8000"
PREFIX = "/api/v1"


class ContractValidator:
    def __init__(self) -> None:
        self.spec = OpenAPI.from_file_path(str(CONTRACT_PATH))

    def check(self, method: str, path: str, response, path_pattern: str | None = None) -> None:
        """Raise if `response` (an httpx/Starlette test response) violates the contract.

        `path` is relative to /api/v1, e.g. "/health" or "/regions/mekong-delta".
        """
        request = MockRequest(HOST_URL, method.lower(), PREFIX + path, path_pattern=path_pattern)
        mock = MockResponse(
            response.content,
            status_code=response.status_code,
            content_type=response.headers.get("content-type", "application/json").split(";")[0],
        )
        self.spec.validate_response(request, mock)
