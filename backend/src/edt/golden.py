"""Golden results: default analysis for every preset × variable → tests/golden/*.json."""

from __future__ import annotations

import json
from pathlib import Path

from edt.catalogue import default_years, variables
from edt.config import Settings
from edt.regions.select import presets
from edt.trends import analyze

GOLDEN_DIR = Path(__file__).resolve().parents[2] / "tests" / "golden"


def golden_requests():
    y0, _ = default_years()
    for vid in variables():
        for rid in presets():
            yield (
                f"{vid}__{rid}",
                {
                    "variableId": vid,
                    "region": {"presetId": rid},
                    "startYear": y0,
                    "alpha": 0.05,
                },
            )


def write_golden(settings: Settings) -> None:
    GOLDEN_DIR.mkdir(parents=True, exist_ok=True)
    for name, req in golden_requests():
        res = analyze(settings, req)
        (GOLDEN_DIR / f"{name}.json").write_text(
            json.dumps({"request": req, "result": res}, indent=1, ensure_ascii=False)
        )
        mk = res["mannKendall"]
        sen, p = mk["senSlopePerDecade"], mk["pValue"]
        print(
            f"{name:36s} n={mk['n']:2d} cells={res['region']['cellCount']:4d} "
            f"sen/dec={'-' if sen is None else f'{sen:.4g}':>9} "
            f"p={'-' if p is None else f'{p:.3g}':>8} {res['significance']['status']}"
        )
