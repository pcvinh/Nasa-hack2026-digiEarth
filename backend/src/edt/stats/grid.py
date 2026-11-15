"""Vectorised per-cell Mann-Kendall + Sen's slope and Benjamini-Hochberg FDR (for trend maps)."""

from __future__ import annotations

import numpy as np
from scipy.stats import norm


def mann_kendall_sen(y: np.ndarray, x: np.ndarray | None = None) -> tuple[np.ndarray, ...]:
    """y: (n_years, n_cells) with no NaN. Returns (sen_slope_per_year, tau, p) per cell.

    Uses the no-ties variance (continuous data) and the continuity-corrected z, two-sided p;
    equals pymannkendall.original_test when there are no ties.
    """
    n = y.shape[0]
    x = np.arange(n, dtype=np.float64) if x is None else np.asarray(x, dtype=np.float64)
    i, j = np.triu_indices(n, k=1)
    d = y[j] - y[i]  # (pairs, cells)
    s = np.sign(d).sum(axis=0)
    var_s = n * (n - 1) * (2 * n + 5) / 18.0
    z = np.where(s > 0, (s - 1) / np.sqrt(var_s), np.where(s < 0, (s + 1) / np.sqrt(var_s), 0.0))
    p = 2 * (1 - norm.cdf(np.abs(z)))
    tau = s / (0.5 * n * (n - 1))
    slope = np.median(d / (x[j] - x[i])[:, None], axis=0)
    return slope, tau, p


def benjamini_hochberg(p: np.ndarray, q: float = 0.05) -> np.ndarray:
    """Boolean mask of discoveries at FDR level q."""
    p = np.asarray(p, dtype=np.float64)
    m = p.size
    if m == 0:
        return np.zeros(0, dtype=bool)
    order = np.argsort(p)
    ranked = p[order]
    below = ranked <= q * np.arange(1, m + 1) / m
    out = np.zeros(m, dtype=bool)
    if below.any():
        k = np.nonzero(below)[0].max()
        out[order[: k + 1]] = True
    return out
