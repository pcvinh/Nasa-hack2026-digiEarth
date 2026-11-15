from __future__ import annotations

from fastapi import APIRouter, Request

from edt.api.models import TrendRequest, TrendResult
from edt.trends import analyze

router = APIRouter(tags=["trends"])


@router.post("/trends/analyze", response_model=TrendResult, operation_id="analyzeTrend")
def analyze_trend(request: Request, body: TrendRequest) -> dict:
    return analyze(request.app.state.settings, body.model_dump())
