from __future__ import annotations

import json

from fastapi import APIRouter, Request
from fastapi.responses import FileResponse

from edt.api.errors import ApiError
from edt.api.models import TrendMap
from edt.catalogue import get_variable
from edt.data import provenance

router = APIRouter(tags=["trends"])


def _paths(settings, variable_id: str):
    var = get_variable(variable_id)
    if var is None:
        raise ApiError(404, "not_found", f"Unknown variable '{variable_id}'.")
    png = settings.maps_dir / f"{variable_id}.png"
    meta = settings.maps_dir / f"{variable_id}.json"
    if not (png.exists() and meta.exists()):
        raise ApiError(404, "not_found", f"No trend map has been built for '{variable_id}' yet.")
    return var, png, meta


@router.get("/trend-maps/{variableId}", response_model=TrendMap, operation_id="getTrendMap")
def get_trend_map(request: Request, variableId: str) -> dict:  # noqa: N803
    s = request.app.state.settings
    var, _, meta_path = _paths(s, variableId)
    meta = json.loads(meta_path.read_text())
    keys = ("variableId", "period", "bounds", "cellSize", "legend", "method")
    return {
        **{k: meta[k] for k in keys},
        "imageUrl": f"/api/v1/trend-maps/{variableId}/image.png",
        "dataStatus": "source_backed",
        "provenance": provenance(s, var),
    }


@router.get(
    "/trend-maps/{variableId}/image.png",
    operation_id="getTrendMapImage",
    response_class=FileResponse,
)
def get_trend_map_image(request: Request, variableId: str):  # noqa: N803
    _, png, _ = _paths(request.app.state.settings, variableId)
    return FileResponse(png, media_type="image/png")
