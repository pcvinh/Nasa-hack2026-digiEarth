"""Global trend map per variable: per-cell Sen slope + Mann-Kendall, BH FDR → PNG + JSON."""

from __future__ import annotations

import json

import numpy as np
from PIL import Image

from edt.catalogue import VariableDef, default_years
from edt.config import Settings
from edt.data import cube_info
from edt.pipeline import cube as cubemod
from edt.stats.grid import benjamini_hochberg, mann_kendall_sen

PALETTES = {"diverging_brown_green": "BrBG", "diverging_blue_red": "RdBu_r"}
ALPHA_SIG, ALPHA_NOT = 0.9, 0.35
FDR_Q = 0.05
METHOD = (
    "Per-cell Sen's slope and Mann-Kendall p on annual values; Benjamini-Hochberg FDR "
    "q = 0.05 across all cells with a complete record"
)
CHUNK = 20000


def map_years(info, var: VariableDef) -> tuple[int, int]:
    """Default period, clipped to years whose 12 months were all ingested from source."""
    y0, y1 = default_years()
    complete = []
    for y in range(y0, y1 + 1):
        idx = [info.months.index(f"{y}-{m:02d}") for m in range(1, 13)]
        if (info.status[idx] == cubemod.INGESTED).all():
            complete.append(y)
    return complete[0], complete[-1]


def build_map(settings: Settings, var: VariableDef) -> dict:
    import matplotlib

    info = cube_info(settings, var.id)
    if info is None or not info.complete:
        raise RuntimeError(f"{var.id}: cube missing or incomplete")
    y0, y1 = map_years(info, var)
    t0, t1 = info.months.index(f"{y0}-01"), info.months.index(f"{y1}-12") + 1
    g = cubemod.open_cube(info.path)
    vals = np.asarray(g["value"][t0:t1], dtype=np.float64)  # (months, ny, nx)
    ny, nx = vals.shape[1:]
    m = vals.reshape(-1, 12, ny, nx)
    complete = np.isfinite(m).all(axis=1)
    annual = m.sum(axis=1) if var["annualAggregation"] == "sum" else m.mean(axis=1)
    annual = np.where(complete, annual, np.nan)  # (years, ny, nx)
    flat = annual.reshape(annual.shape[0], -1)
    valid = np.isfinite(flat).all(axis=0)
    idx = np.nonzero(valid)[0]
    years = np.arange(y0, y1 + 1, dtype=np.float64)
    slope = np.full(flat.shape[1], np.nan)
    pval = np.full(flat.shape[1], np.nan)
    for k in range(0, idx.size, CHUNK):
        sl, _, p = mann_kendall_sen(flat[:, idx[k : k + CHUNK]], years)
        slope[idx[k : k + CHUNK]], pval[idx[k : k + CHUNK]] = sl, p
    sig = np.zeros(flat.shape[1], dtype=bool)
    sig[idx] = benjamini_hochberg(pval[idx], FDR_Q)

    per_dec = (slope * 10).reshape(ny, nx)
    sig = sig.reshape(ny, nx)
    limit = float(np.nanpercentile(np.abs(per_dec), 98))
    if not limit > 0:
        limit = float(np.nanmax(np.abs(per_dec))) or 1.0
    cmap = matplotlib.colormaps[PALETTES[var["palette"]]]
    norm = np.clip((per_dec / limit + 1) / 2, 0, 1)
    rgba = cmap(np.nan_to_num(norm, nan=0.5))
    rgba[..., 3] = np.where(sig, ALPHA_SIG, ALPHA_NOT)
    rgba[~np.isfinite(per_dec)] = 0.0

    lat, lon = info.lat, info.lon
    keep = np.abs(lat) < 90  # MERRA-2 pole-centred rows would extend past ±90°; not drawn
    rgba, lat_k = rgba[keep], lat[keep]
    dy, dx = abs(lat[1] - lat[0]), abs(lon[1] - lon[0])
    bounds = [
        round(float(lon[0] - dx / 2), 4),
        round(float(lat_k[0] - dy / 2), 4),
        round(float(lon[-1] + dx / 2), 4),
        round(float(lat_k[-1] + dy / 2), 4),
    ]
    img = (rgba[::-1] * 255).round().astype(np.uint8)  # north at top
    settings.maps_dir.mkdir(parents=True, exist_ok=True)
    Image.fromarray(img, "RGBA").save(settings.maps_dir / f"{var.id}.png", optimize=True)

    meta = {
        "variableId": var.id,
        "period": {"startYear": y0, "endYear": y1},
        "bounds": bounds,
        "cellSize": var.dataset["servedResolution"],
        "legend": {
            "min": -round(limit, 6),
            "max": round(limit, 6),
            "unit": f"{var['annualUnit']} per decade",
            "palette": var["palette"],
            "fadedMeaning": f"Not significant after FDR correction (q = {FDR_Q})",
        },
        "method": METHOD,
        "alpha": {"significant": ALPHA_SIG, "notSignificant": ALPHA_NOT},
        "stats": {
            "cellsWithCompleteRecord": int(idx.size),
            "cellsSignificant": int(sig.sum()),
            "imageSize": [int(img.shape[1]), int(img.shape[0])],
            "colourLimitPercentile": 98,
        },
    }
    (settings.maps_dir / f"{var.id}.json").write_text(
        json.dumps(meta, indent=1, ensure_ascii=False)
    )
    return meta["stats"] | {"period": meta["period"], "limit": limit}
