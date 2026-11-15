"""Variable catalogue: single source is catalogue.yaml (filled from verified dataset facts)."""

from __future__ import annotations

from dataclasses import dataclass
from functools import lru_cache
from pathlib import Path
from typing import Any

import yaml

CATALOGUE_PATH = Path(__file__).with_name("catalogue.yaml")


@dataclass(frozen=True)
class VariableDef:
    id: str
    raw: dict[str, Any]

    @property
    def dataset(self) -> dict[str, Any]:
        return self.raw["dataset"]

    def __getitem__(self, key: str) -> Any:
        return self.raw[key]


@lru_cache
def load_catalogue() -> dict[str, Any]:
    return yaml.safe_load(CATALOGUE_PATH.read_text())


def cube_period() -> tuple[str, str]:
    c = load_catalogue()["cube"]
    return c["start"], c["end"]


def default_years() -> tuple[int, int]:
    c = load_catalogue()["cube"]
    return int(c["defaultStartYear"]), int(c["defaultEndYear"])


@lru_cache
def variables() -> dict[str, VariableDef]:
    return {v["id"]: VariableDef(v["id"], v) for v in load_catalogue()["variables"]}


def get_variable(variable_id: str) -> VariableDef | None:
    return variables().get(variable_id)


P0_VARIABLE_IDS: tuple[str, ...] = tuple(variables())
