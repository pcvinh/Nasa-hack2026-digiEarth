"""Pydantic models mirroring the contract (grown package by package)."""

from __future__ import annotations

from typing import Literal

from pydantic import BaseModel

DataStatus = Literal["source_backed", "sample", "unavailable"]


class VariableHealth(BaseModel):
    id: str
    status: DataStatus


class Health(BaseModel):
    status: Literal["ok", "degraded"]
    dataVersion: str
    variables: list[VariableHealth]
