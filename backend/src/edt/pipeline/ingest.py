"""Ingest one variable month by month: download → read → convert → coarsen → cube → delete raw.

Resumable: months whose cube status is not 0 are skipped. At most 4 parallel downloads;
reading and writing happen in the main thread only.
"""

from __future__ import annotations

import json
import logging
import os
import time
from concurrent.futures import ThreadPoolExecutor, as_completed
from datetime import UTC, datetime
from pathlib import Path

import numpy as np

from edt.catalogue import VariableDef, cube_period
from edt.config import Settings
from edt.pipeline import cube as cubemod
from edt.pipeline import fetch
from edt.pipeline.coarsen import block_mean, coarsen_coords
from edt.pipeline.readers import READERS

log = logging.getLogger(__name__)
PROCESSING_VERSION = "1"


def ingest_log_path(settings: Settings, variable_id: str) -> Path:
    return settings.data_root / "ingest" / f"{variable_id}.json"


def read_ingest_log(settings: Settings, variable_id: str) -> dict:
    p = ingest_log_path(settings, variable_id)
    return json.loads(p.read_text()) if p.exists() else {"months": {}}


def _write_json_atomic(path: Path, data: dict) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    tmp = path.with_suffix(".tmp")
    tmp.write_text(json.dumps(data, indent=1, sort_keys=True))
    os.replace(tmp, path)


def process_file(var: VariableDef, path: Path, month: str):
    y, m = map(int, month.split("-"))
    a, lat, lon = READERS[var.dataset["reader"]](path, y, m)
    f = int(var.dataset["coarsenFactor"])
    lat_c = np.round(coarsen_coords(lat, f), 6)
    lon_c = np.round(coarsen_coords(lon, f), 6)
    return block_mean(a, f), lat_c, lon_c


def ingest(
    settings: Settings,
    var: VariableDef,
    start: str | None = None,
    end: str | None = None,
    keep_raw: bool = False,
    workers: int = 4,
) -> dict:
    cstart, cend = cube_period()
    months = cubemod.month_list(cstart, cend)
    start, end = start or cstart, end or cend
    wanted = [m for m in months if start <= m <= end]
    ds = var.dataset
    cube_path = settings.cube_dir / f"{var.id}.zarr"
    raw_dir = settings.raw_dir / ds["datasetId"]
    logdata = read_ingest_log(settings, var.id)

    g = cubemod.open_cube(cube_path, "a") if cube_path.exists() else None
    if g is not None:
        status = g["status"][:]
        wanted = [m for m in wanted if status[months.index(m)] == cubemod.NOT_INGESTED]
    if not wanted:
        log.info("%s: nothing to do", var.id)
        return {"ingested": 0, "noSource": 0}

    granules = fetch.search_months(ds["shortName"], ds["cmrVersion"], wanted[0], wanted[-1])
    have = [m for m in wanted if m in granules]
    missing = [m for m in wanted if m not in granules]
    log.info("%s: %d months to ingest, %d with no granule", var.id, len(have), len(missing))

    done = 0
    t_start = time.time()
    with ThreadPoolExecutor(max_workers=min(workers, 4)) as pool:
        futures = {pool.submit(fetch.download, granules[m], raw_dir): m for m in have}
        for fut in as_completed(futures):
            month = futures[fut]
            path, secs = fut.result()
            values, lat, lon = process_file(var, path, month)
            if g is None:
                cubemod.create(
                    cube_path,
                    months,
                    lat,
                    lon,
                    {
                        "variableId": var.id,
                        "unit": var["unit"],
                        "datasetId": ds["datasetId"],
                        "datasetVersion": ds["datasetVersion"],
                        "processingVersion": PROCESSING_VERSION,
                    },
                )
                g = cubemod.open_cube(cube_path, "a")
            if not (np.allclose(g["lat"][:], lat) and np.allclose(g["lon"][:], lon)):
                raise RuntimeError(f"{var.id} {month}: grid differs from cube grid")
            cubemod.write_month(g, months.index(month), values)
            gran = granules[month]
            logdata["months"][month] = {
                "granuleUR": gran["umm"]["GranuleUR"],
                "url": fetch.granule_url(gran),
                "bytes": path.stat().st_size,
                "sha256": fetch.sha256(path),
                "downloadSeconds": round(secs, 1),
                "ingestedAt": datetime.now(UTC).isoformat(timespec="seconds"),
                "validCells": int(np.isfinite(values).sum()),
            }
            _write_json_atomic(ingest_log_path(settings, var.id), logdata)
            if not keep_raw:
                path.unlink(missing_ok=True)
            done += 1
            if done % 12 == 0 or done == len(have):
                log.info("%s: %d/%d months (%.0fs)", var.id, done, len(have), time.time() - t_start)

    if g is not None:
        for m in missing:
            cubemod.mark_no_source(g, months.index(m))
            logdata["months"][m] = {"noSource": True, "checkedAt": datetime.now(UTC).isoformat()}
        _write_json_atomic(ingest_log_path(settings, var.id), logdata)
    return {"ingested": done, "noSource": len(missing), "seconds": round(time.time() - t_start)}
