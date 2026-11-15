from __future__ import annotations

from fastapi import APIRouter, Request

from edt.api.models import Health
from edt.catalogue import variables
from edt.data import data_version, variable_status

router = APIRouter(tags=["system"])


@router.get("/health", response_model=Health, operation_id="getHealth")
def get_health(request: Request) -> dict:
    settings = request.app.state.settings
    items = [
        {"id": vid, "status": variable_status(settings, v)[0]} for vid, v in variables().items()
    ]
    degraded = any(i["status"] != "source_backed" for i in items)
    return {
        "status": "degraded" if degraded else "ok",
        "dataVersion": data_version(settings),
        "variables": items,
    }
