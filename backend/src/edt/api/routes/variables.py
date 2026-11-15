from __future__ import annotations

from fastapi import APIRouter, Query, Request

from edt.api.models import Topic, VariableList
from edt.catalogue import cube_period, variables
from edt.data import cube_info, provenance, variable_status

router = APIRouter(tags=["catalogue"])


def variable_payload(settings, v) -> dict:
    status, reason = variable_status(settings, v)
    info = cube_info(settings, v.id)
    cov = info.coverage if info is not None and status == "source_backed" else None
    start, end = cov or cube_period()
    return {
        "id": v.id,
        "name": v["name"],
        "topic": v["topic"],
        "shortDefinition": " ".join(v["shortDefinition"].split()),
        "whyItMatters": " ".join(v["whyItMatters"].split()),
        "unit": v["unit"],
        "annualUnit": v["annualUnit"],
        "annualAggregation": v["annualAggregation"],
        "coverage": {"start": start, "end": end, "landOnly": bool(v["landOnly"])},
        "status": status,
        "unavailableReason": reason,
        "provenance": provenance(settings, v),
    }


@router.get(
    "/variables",
    response_model=VariableList,
    operation_id="listVariables",
    response_model_exclude_none=False,
)
def list_variables(request: Request, topic: Topic | None = Query(default=None)) -> dict:
    s = request.app.state.settings
    return {
        "items": [
            variable_payload(s, v)
            for v in variables().values()
            if topic is None or v["topic"] == topic
        ]
    }
