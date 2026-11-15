"""data/manifest.json: per dataset provenance, coverage, file hashes; plus dataVersion."""

from __future__ import annotations

import json
import os
from datetime import UTC, datetime

from edt.catalogue import variables
from edt.config import Settings
from edt.data import cube_info
from edt.pipeline import cube as cubemod
from edt.pipeline.ingest import PROCESSING_VERSION, read_ingest_log


def write_manifest(settings: Settings) -> dict:
    datasets = {}
    latest = ""
    for vid, var in variables().items():
        info = cube_info(settings, vid)
        log = read_ingest_log(settings, vid)["months"]
        files = {
            m: {k: v[k] for k in ("granuleUR", "url", "sha256", "bytes")}
            for m, v in sorted(log.items())
            if "sha256" in v
        }
        dates = sorted(v["ingestedAt"][:10] for v in log.values() if "ingestedAt" in v)
        if dates:
            latest = max(latest, dates[-1])
        ds = var.dataset
        cov = info.coverage if info else None
        datasets[vid] = {
            "product": ds["datasetId"],
            "version": str(ds["datasetVersion"]),
            "missionOrModel": ds["missionOrModel"],
            "collectionUrl": ds["sourceUrl"],
            "doi": ds.get("doi"),
            "citation": " ".join(ds["citation"].split()),
            "sourceVariable": ds["sourceVariable"],
            "nativeUnit": ds["nativeUnit"],
            "servedUnit": var["unit"],
            "nativeFill": ds["nativeFill"],
            "nativeResolution": ds["nativeResolution"],
            "servedResolution": ds["servedResolution"],
            "servedGrid": [int(info.lat.size), int(info.lon.size)] if info else None,
            "processing": " ".join(ds["processing"].split()),
            "processingVersion": PROCESSING_VERSION,
            "accessDate": dates[-1] if dates else None,
            "accessDateFirst": dates[0] if dates else None,
            "coverage": {"start": cov[0], "end": cov[1]} if cov else None,
            "cubeComplete": bool(info.complete) if info else False,
            "monthsIngested": int((info.status == cubemod.INGESTED).sum()) if info else 0,
            "monthsNoSource": [
                m for m, s in zip(info.months, info.status, strict=True) if s == cubemod.NO_SOURCE
            ]
            if info
            else [],
            "totalBytesDownloaded": sum(f["bytes"] for f in files.values()),
            "files": files,
        }
    manifest = {
        "dataVersion": f"{latest or datetime.now(UTC).date().isoformat()}.{PROCESSING_VERSION}",
        "generatedAt": datetime.now(UTC).isoformat(timespec="seconds"),
        "datasets": datasets,
    }
    tmp = settings.manifest_path.with_suffix(".tmp")
    tmp.write_text(json.dumps(manifest, indent=1, ensure_ascii=False))
    os.replace(tmp, settings.manifest_path)
    return {
        "dataVersion": manifest["dataVersion"],
        "datasets": {
            k: {
                kk: v[kk]
                for kk in (
                    "coverage",
                    "cubeComplete",
                    "monthsIngested",
                    "monthsNoSource",
                    "accessDate",
                )
            }
            for k, v in datasets.items()
        },
    }
