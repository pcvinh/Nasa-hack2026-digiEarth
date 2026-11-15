from __future__ import annotations

from fastapi import APIRouter

from edt.api.errors import ApiError
from edt.api.models import Region, RegionList
from edt.regions.select import presets

router = APIRouter(tags=["catalogue"])


@router.get("/regions", response_model=RegionList, operation_id="listRegions")
def list_regions(q: str | None = None) -> dict:
    items = list(presets().values())
    if q:
        ql = q.lower()
        items = [r for r in items if ql in r["name"].lower() or ql in (r["country"] or "").lower()]
    return {"items": items}


@router.get("/regions/{regionId}", response_model=Region, operation_id="getRegion")
def get_region(regionId: str) -> dict:  # noqa: N803 (contract name)
    r = presets().get(regionId)
    if r is None:
        raise ApiError(404, "not_found", f"Unknown region '{regionId}'.")
    return r
