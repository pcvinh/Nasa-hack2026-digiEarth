from __future__ import annotations

from fastapi import APIRouter

from edt.api.errors import ApiError
from edt.api.models import GuideRequest, GuideResponse
from edt.catalogue import variables
from edt.guide.engine import chat
from edt.regions.select import presets

router = APIRouter(tags=["guide"])


@router.post("/guide/chat", response_model=GuideResponse, operation_id="guideChat")
def guide_chat(body: GuideRequest) -> dict:
    if body.regionId and body.regionId not in presets():
        raise ApiError(400, "invalid_input", f"Unknown regionId '{body.regionId}'.")
    if body.variableId and body.variableId not in variables():
        raise ApiError(400, "invalid_input", f"Unknown variableId '{body.variableId}'.")
    return chat(body.message, body.regionId, body.variableId, body.topic)
