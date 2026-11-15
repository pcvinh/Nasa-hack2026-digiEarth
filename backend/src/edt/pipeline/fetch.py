"""Search and download NASA granules with earthaccess (Earthdata Login from ~/.netrc)."""

from __future__ import annotations

import hashlib
import logging
import time
from pathlib import Path

log = logging.getLogger(__name__)

_logged_in = False


def login() -> None:
    global _logged_in
    if not _logged_in:
        import earthaccess

        auth = earthaccess.login(strategy="netrc")
        if not getattr(auth, "authenticated", False):
            raise RuntimeError(
                "Earthdata Login failed (check ~/.netrc entry for urs.earthdata.nasa.gov)."
            )
        _logged_in = True


def granule_month(g) -> str:
    return g["umm"]["TemporalExtent"]["RangeDateTime"]["BeginningDateTime"][:7]


def search_months(short_name: str, version: str, start: str, end: str) -> dict[str, object]:
    """Return {YYYY-MM: granule} for the period. Fails loudly if a month has >1 granule."""
    import earthaccess

    login()
    ey, em = map(int, end.split("-"))
    last_day = "31" if em in (1, 3, 5, 7, 8, 10, 12) else ("29" if em == 2 else "30")
    results = earthaccess.search_data(
        short_name=short_name, version=version, temporal=(f"{start}-01", f"{end}-{last_day}")
    )
    out: dict[str, object] = {}
    for g in results:
        m = granule_month(g)
        if m in out:
            raise RuntimeError(f"{short_name}: more than one granule for {m}")
        out[m] = g
    return out


def download(granule, dest_dir: Path, retries: int = 3) -> tuple[Path, float]:
    import earthaccess

    login()
    dest_dir.mkdir(parents=True, exist_ok=True)
    last_err: Exception | None = None
    for attempt in range(1, retries + 1):
        t0 = time.time()
        try:
            files = earthaccess.download([granule], str(dest_dir), threads=1, show_progress=False)
            if files:
                return Path(files[0]), time.time() - t0
            last_err = RuntimeError("earthaccess returned no file")
        except Exception as e:  # network errors: retry
            last_err = e
        log.warning("download attempt %s failed: %s", attempt, last_err)
        time.sleep(5 * attempt)
    raise RuntimeError(
        f"download failed after {retries} attempts: {last_err}. If this is an auth error "
        "(401/403), the Earthdata app approval for this archive (GES DISC or LP DAAC) is "
        "likely missing."
    )


def sha256(path: Path) -> str:
    h = hashlib.sha256()
    with open(path, "rb") as f:
        for chunk in iter(lambda: f.read(1 << 20), b""):
            h.update(chunk)
    return h.hexdigest()


def granule_url(granule) -> str:
    links = granule.data_links()
    return links[0] if links else ""
