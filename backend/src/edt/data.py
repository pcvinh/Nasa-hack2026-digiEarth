"""Read-only access to the cubes, ingest logs and manifest under DATA_ROOT (lazy Zarr reads)."""

from __future__ import annotations

import json
from dataclasses import dataclass
from functools import lru_cache
from pathlib import Path

import numpy as np

from edt.catalogue import VariableDef, get_variable, variables
from edt.config import Settings
from edt.pipeline import cube as cubemod

UNINITIALISED_VERSION = "uninitialised"


@dataclass(frozen=True)
class CubeInfo:
    path: Path
    months: tuple[str, ...]
    lat: np.ndarray
    lon: np.ndarray
    status: np.ndarray

    @property
    def complete(self) -> bool:
        return bool((self.status != cubemod.NOT_INGESTED).all())

    @property
    def coverage(self) -> tuple[str, str] | None:
        idx = np.nonzero(self.status == cubemod.INGESTED)[0]
        if idx.size == 0:
            return None
        return self.months[idx[0]], self.months[idx[-1]]

    @property
    def last_complete_year(self) -> int | None:
        """Last year whose 12 months are all present (derived from coverage.end)."""
        cov = self.coverage
        if cov is None:
            return None
        year, month = int(cov[1][:4]), int(cov[1][5:])
        return year if month == 12 else year - 1

    def read(self, y0: int, y1: int, x0: int, x1: int) -> np.ndarray:
        g = cubemod.open_cube(self.path)
        return np.asarray(g["value"][:, y0:y1, x0:x1], dtype=np.float64)


def _mtime(path: Path) -> float:
    """Changes whenever ingest writes a month (status chunks are rewritten), busting the cache."""
    return max((q.stat().st_mtime for q in (path / "status").rglob("*")), default=0.0)


@lru_cache(maxsize=16)
def _load_cube(path: Path, mtime: float) -> CubeInfo:
    g = cubemod.open_cube(path)
    return CubeInfo(
        path=path,
        months=tuple(str(m) for m in g["time"][:]),
        lat=np.asarray(g["lat"][:]),
        lon=np.asarray(g["lon"][:]),
        status=np.asarray(g["status"][:]),
    )


def cube_info(settings: Settings, variable_id: str) -> CubeInfo | None:
    path = settings.cube_dir / f"{variable_id}.zarr"
    if not (path / "zarr.json").exists():
        return None
    return _load_cube(path, _mtime(path))


def manifest(settings: Settings) -> dict:
    try:
        return json.loads(settings.manifest_path.read_text())
    except (OSError, ValueError):
        return {}


def data_version(settings: Settings) -> str:
    return str(manifest(settings).get("dataVersion", UNINITIALISED_VERSION))


def access_date(settings: Settings, variable_id: str) -> str:
    """Date the data was downloaded (latest ingest), from the ingest log; manifest first."""
    m = manifest(settings).get("datasets", {}).get(variable_id, {})
    if m.get("accessDate"):
        return m["accessDate"]
    p = settings.data_root / "ingest" / f"{variable_id}.json"
    try:
        months = json.loads(p.read_text())["months"].values()
        dates = [v["ingestedAt"][:10] for v in months if "ingestedAt" in v]
        return max(dates) if dates else "1970-01-01"
    except (OSError, ValueError, KeyError):
        return "1970-01-01"


def variable_status(settings: Settings, var: VariableDef) -> tuple[str, str | None]:
    info = cube_info(settings, var.id)
    if info is None:
        return "unavailable", "Data has not been ingested yet."
    if not info.complete:
        done = int((info.status != cubemod.NOT_INGESTED).sum())
        return "unavailable", f"Data ingest not complete ({done}/{len(info.months)} months)."
    return "source_backed", None


def provenance(settings: Settings, var: VariableDef) -> dict:
    ds = var.dataset
    return {
        "datasetId": ds["datasetId"],
        "datasetVersion": str(ds["datasetVersion"]),
        "missionOrModel": ds["missionOrModel"],
        "sourceUrl": ds["sourceUrl"],
        "doi": ds.get("doi"),
        "accessDate": access_date(settings, var.id),
        "processing": " ".join(ds["processing"].split()),
        "nativeResolution": ds["nativeResolution"],
        "servedResolution": ds["servedResolution"],
        "citation": " ".join(ds["citation"].split()),
        "qualityNotes": [" ".join(n.split()) for n in var.raw.get("qualityNotes", [])],
    }


__all__ = [
    "cube_info",
    "data_version",
    "provenance",
    "variable_status",
    "variables",
    "get_variable",
]
