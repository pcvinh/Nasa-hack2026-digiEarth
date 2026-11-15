from __future__ import annotations

import json

from fastapi import APIRouter, Request

from edt.api.models import Health, VariableHealth
from edt.catalogue import P0_VARIABLE_IDS

router = APIRouter(tags=["system"])

UNINITIALISED_VERSION = "uninitialised"


def read_data_version(manifest_path) -> str:
    """dataVersion comes from manifest.json once the pipeline has written it."""
    try:
        return str(json.loads(manifest_path.read_text())["dataVersion"])
    except (OSError, KeyError, ValueError):
        return UNINITIALISED_VERSION


def cube_exists(settings, variable_id: str) -> bool:
    return (settings.cube_dir / f"{variable_id}.zarr").exists()


@router.get("/health", response_model=Health, operation_id="getHealth")
def get_health(request: Request) -> Health:
    settings = request.app.state.settings
    variables = [
        VariableHealth(
            id=vid,
            status="source_backed" if cube_exists(settings, vid) else "unavailable",
        )
        for vid in P0_VARIABLE_IDS
    ]
    degraded = any(v.status == "unavailable" for v in variables)
    return Health(
        status="degraded" if degraded else "ok",
        dataVersion=read_data_version(settings.manifest_path),
        variables=variables,
    )
