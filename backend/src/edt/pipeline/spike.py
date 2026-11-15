"""BE-02 spike: download (or reuse) one month and print the facts needed for the catalogue."""

from __future__ import annotations

import time

import numpy as np

from edt.catalogue import VariableDef
from edt.config import Settings
from edt.pipeline import fetch
from edt.pipeline.ingest import process_file
from edt.pipeline.readers import READERS


def spike(settings: Settings, var: VariableDef, month: str) -> dict:
    ds = var.dataset
    granules = fetch.search_months(ds["shortName"], ds["cmrVersion"], month, month)
    if month not in granules:
        return {"variable": var.id, "month": month, "error": "no granule at source"}
    raw_dir = settings.raw_dir / ds["datasetId"]
    gran = granules[month]
    name = fetch.granule_url(gran).rsplit("/", 1)[-1]
    path = raw_dir / name
    secs = None
    if not path.exists():
        t = time.time()
        path, _ = fetch.download(gran, raw_dir)
        secs = round(time.time() - t, 1)
    y, m = map(int, month.split("-"))
    a, lat, lon = READERS[ds["reader"]](path, y, m)
    c, clat, clon = process_file(var, path, month)
    fin = a[np.isfinite(a)]
    return {
        "variable": var.id,
        "month": month,
        "granule": gran["umm"]["GranuleUR"],
        "url": fetch.granule_url(gran),
        "fileMB": round(path.stat().st_size / 1e6, 1),
        "downloadSeconds": secs,
        "nativeGrid": list(a.shape),
        "nativeLat": [float(lat[0]), float(lat[-1])],
        "nativeLon": [float(lon[0]), float(lon[-1])],
        "nativeValidFraction": round(float(np.isfinite(a).mean()), 4),
        "servedUnitMinMax": [round(float(fin.min()), 4), round(float(fin.max()), 4)],
        "servedGrid": list(c.shape),
        "servedLat": [float(clat[0]), float(clat[-1])],
        "servedLon": [float(clon[0]), float(clon[-1])],
        "servedValidFraction": round(float(np.isfinite(c).mean()), 4),
    }
