"""Pydantic models mirroring contracts/trend-detective-api.openapi.yaml v0.2."""

from __future__ import annotations

from typing import Any, Literal

from pydantic import BaseModel, ConfigDict, Field

DataStatus = Literal["source_backed", "sample", "unavailable"]
Topic = Literal["water", "heat", "vegetation", "air_quality"]


class _M(BaseModel):
    model_config = ConfigDict(extra="forbid")


class _In(BaseModel):
    """Request bodies: the contract allows extra properties, so ignore them."""

    model_config = ConfigDict(extra="ignore")


class VariableHealth(_M):
    id: str
    status: DataStatus


class Health(_M):
    status: Literal["ok", "degraded"]
    dataVersion: str
    variables: list[VariableHealth]


class Provenance(_M):
    datasetId: str
    datasetVersion: str
    missionOrModel: str
    sourceUrl: str
    doi: str | None = None
    accessDate: str
    processing: str
    nativeResolution: str
    servedResolution: str
    citation: str
    # Additive field (not in contract 0.2.1): data-quality notes; [] when there are none
    qualityNotes: list[str] = []


class Coverage(_M):
    start: str
    end: str
    landOnly: bool = False


class Variable(_M):
    id: str
    name: str
    topic: Topic
    shortDefinition: str
    whyItMatters: str
    unit: str
    annualUnit: str
    annualAggregation: Literal["mean", "sum"]
    coverage: Coverage
    status: DataStatus
    unavailableReason: str | None = None
    provenance: Provenance


class VariableList(_M):
    items: list[Variable]


class Region(_M):
    id: str
    name: str
    country: str | None = None
    regionType: Literal[
        "river_delta", "rainforest", "desert_edge", "agricultural", "megacity", "other"
    ]
    description: str
    center: list[float]
    bbox: list[float]
    geometry: dict[str, Any]
    geometrySource: str
    suggestedVariableIds: list[str]


class RegionList(_M):
    items: list[Region]


class RegionInput(_In):
    presetId: str | None = None
    bbox: list[float] | None = Field(default=None, min_length=4, max_length=4)
    point: list[float] | None = Field(default=None, min_length=2, max_length=2)


class TrendRequest(_In):
    variableId: str
    region: RegionInput
    startYear: int = 2001
    endYear: int | None = None  # omitted = variable's last complete year
    alpha: float = Field(default=0.05, ge=0.001, le=0.2)


class ResolvedRegion(_M):
    presetId: str | None = None
    name: str
    bbox: list[float]
    representativeness: Literal["area_mean", "single_cell"]
    cellCount: int
    cellSize: str | None = None


class MonthlyPoint(_M):
    time: str
    value: float | None
    anomaly: float | None
    validCellFraction: float | None = None


class AnnualPoint(_M):
    year: int
    value: float | None


class LinearTrend(_M):
    method: str
    slopePerDecade: float | None
    ci95: list[float] | None
    pValue: float | None
    rSquared: float | None = None
    n: int


class MannKendallTrend(_M):
    method: str
    senSlopePerDecade: float | None
    tau: float | None
    pValue: float | None
    n: int


class Significance(_M):
    alpha: float
    status: Literal["significant", "not_significant", "insufficient_data"]
    direction: Literal["increasing", "decreasing", "no_change"]
    agreement: Literal["both", "mann_kendall_only", "ols_only", "neither"]


class Interpretation(_M):
    headline: str
    summary: str
    caveats: list[str]


class Period(_M):
    startYear: int
    endYear: int


class TotalChange(_M):
    value: float | None
    unit: str


class TrendLines(_M):
    sen: list[AnnualPoint]
    ols: list[AnnualPoint]


class TrendResult(_M):
    variableId: str
    region: ResolvedRegion
    period: Period
    unit: str
    annualUnit: str
    dataStatus: DataStatus
    monthly: list[MonthlyPoint]
    annual: list[AnnualPoint]
    totalChange: TotalChange
    linear: LinearTrend
    mannKendall: MannKendallTrend
    trendLines: TrendLines
    significance: Significance
    interpretation: Interpretation
    provenance: Provenance
    dataVersion: str


class Legend(_M):
    min: float
    max: float
    unit: str
    palette: Literal["diverging_brown_green", "diverging_blue_red"]
    colorStops: list[str] | None = None  # optional in contract 0.2.1
    fadedMeaning: str


class TrendMap(_M):
    variableId: str
    period: Period
    imageUrl: str
    bounds: list[float]
    cellSize: str
    legend: Legend
    method: str
    dataStatus: DataStatus
    provenance: Provenance


class GuideAction(_M):
    type: Literal["select_variable", "select_region", "run_analysis", "show_trend_map"]
    payload: dict[str, Any]


class GuideRequest(_In):
    message: str = Field(min_length=1, max_length=1000)
    regionId: str | None = None
    variableId: str | None = None
    topic: Topic | None = None


class Suggestion(_M):
    variableId: str
    reason: str


class GuideResponse(_M):
    reply: str
    suggestions: list[Suggestion]
    actions: list[GuideAction]
    mode: Literal["rules", "llm"]


class SessionInput(_In):
    title: str = Field(min_length=1, max_length=160)
    state: dict[str, Any]


class SessionSummary(_M):
    id: str
    title: str
    createdAt: str
    updatedAt: str


class Session(SessionSummary):
    state: dict[str, Any]


class SessionList(_M):
    items: list[SessionSummary]
