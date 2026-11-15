"""Integer block-mean coarsening. A coarse cell is NaN unless ≥50% of its sub-cells are valid."""

from __future__ import annotations

import numpy as np


def block_mean(a: np.ndarray, factor: int) -> np.ndarray:
    if factor == 1:
        return a.astype(np.float32, copy=True)
    ny, nx = a.shape
    if ny % factor or nx % factor:
        raise ValueError(f"grid {a.shape} not divisible by factor {factor}")
    b = a.reshape(ny // factor, factor, nx // factor, factor)
    valid = np.isfinite(b)
    count = valid.sum(axis=(1, 3))
    total = np.where(valid, b, 0).astype(np.float64).sum(axis=(1, 3))
    with np.errstate(invalid="ignore", divide="ignore"):
        out = total / count
    out[count * 2 < factor * factor] = np.nan
    return out.astype(np.float32)


def coarsen_coords(c: np.ndarray, factor: int) -> np.ndarray:
    if factor == 1:
        return c.copy()
    return c.reshape(-1, factor).mean(axis=1)
