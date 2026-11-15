"""Re-running the analysis reproduces tests/golden/*.json for the same dataVersion.

Runs only when DATA_ROOT points at the real data whose dataVersion matches the golden files.
"""

from __future__ import annotations

import json
import os
from pathlib import Path

import pytest

GOLDEN = sorted((Path(__file__).parent / "golden").glob("*.json"))


@pytest.mark.skipif(not GOLDEN, reason="no golden files yet")
def test_golden_reproduces():
    from edt.config import load_settings
    from edt.data import data_version
    from edt.trends import _CACHE, analyze

    if not os.environ.get("DATA_ROOT"):
        pytest.skip("DATA_ROOT not set")
    settings = load_settings()
    version = data_version(settings)
    first = json.loads(GOLDEN[0].read_text())
    if first["result"]["dataVersion"] != version:
        pytest.skip(f"golden dataVersion {first['result']['dataVersion']} != data {version}")
    _CACHE.clear()
    for path in GOLDEN:
        g = json.loads(path.read_text())
        got = json.loads(json.dumps(analyze(settings, g["request"])))
        assert got == g["result"], path.name
