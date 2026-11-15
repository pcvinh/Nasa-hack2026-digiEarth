from __future__ import annotations

import numpy as np
import pymannkendall as pmk
import pytest

from edt.stats.core import (
    annual_values,
    fmt_num,
    interpret,
    monthly_anomalies,
    sig2,
    trend_stats,
)
from edt.stats.grid import benjamini_hochberg, mann_kendall_sen

YEARS = np.arange(2001, 2026)


def test_known_slope_is_recovered_and_significant():
    rng = np.random.default_rng(42)
    y = 100 + 2.0 * (YEARS - 2001) + rng.normal(0, 3, YEARS.size)
    ts = trend_stats(YEARS, y)
    assert ts.status == "significant" and ts.direction == "increasing"
    assert ts.sen_per_year == pytest.approx(2.0, abs=0.3)
    lo, hi = ts.ols_ci_per_year
    assert lo <= 2.0 <= hi
    assert ts.agreement == "both"
    assert ts.n == 25


def test_flat_noise_is_not_significant():
    rng = np.random.default_rng(7)
    ts = trend_stats(YEARS, rng.normal(50, 5, YEARS.size))
    assert ts.status == "not_significant"
    assert ts.agreement == "neither"


def test_fewer_than_ten_years_is_insufficient():
    y = np.full(YEARS.size, np.nan)
    y[:9] = np.arange(9)
    ts = trend_stats(YEARS, y)
    assert ts.status == "insufficient_data" and ts.n == 9
    assert ts.sen_per_year is None and ts.mk_p is None


def test_matches_pymannkendall_without_gaps():
    rng = np.random.default_rng(1)
    y = rng.normal(0, 1, 25) + 0.05 * np.arange(25)
    ts = trend_stats(YEARS, y)
    ref = pmk.original_test(y)
    assert ts.mk_p == pytest.approx(ref.p)
    assert ts.tau == pytest.approx(ref.Tau)
    assert ts.sen_per_year == pytest.approx(ref.slope)


def test_null_years_are_excluded_not_zeroed():
    y = 10 + 0.5 * np.arange(25.0)
    y[-1] = np.nan
    ts = trend_stats(YEARS, y)
    assert ts.n == 24 and ts.excluded_years == [2025]
    assert ts.sen_per_year == pytest.approx(0.5)


def test_annual_sum_mean_and_missing_month():
    m = np.ones(36)
    m[13] = np.nan
    s = annual_values(m, "sum")
    assert s[0] == 12 and np.isnan(s[1]) and s[2] == 12
    assert annual_values(np.arange(12.0), "mean")[0] == pytest.approx(5.5)


def test_monthly_anomaly_uses_same_calendar_month():
    m = np.tile(np.arange(12.0), 3)
    m[12] = 3.0  # Jan of year 2
    a = monthly_anomalies(m)
    assert a[0] == pytest.approx(-1.0) and a[12] == pytest.approx(2.0)
    assert np.allclose(a[1:12], 0)


def test_grid_mk_matches_pymannkendall_on_200_cells():
    rng = np.random.default_rng(3)
    y = rng.normal(0, 1, (25, 200)) + rng.normal(0, 0.1, 200) * np.arange(25)[:, None]
    slope, tau, p = mann_kendall_sen(y)
    for c in range(200):
        ref = pmk.original_test(y[:, c])
        assert p[c] == pytest.approx(ref.p, abs=1e-9)
        assert tau[c] == pytest.approx(ref.Tau)
        assert slope[c] == pytest.approx(ref.slope)


def test_benjamini_hochberg_matches_statsmodels():
    from statsmodels.stats.multitest import multipletests

    rng = np.random.default_rng(5)
    p = np.concatenate([rng.uniform(0, 0.01, 50), rng.uniform(0, 1, 500)])
    ref = multipletests(p, alpha=0.05, method="fdr_bh")[0]
    assert (benjamini_hochberg(p, 0.05) == ref).all()


def test_rounding_helpers():
    assert sig2(0.012345) == 0.012
    assert sig2(12345) == 12000
    assert fmt_num(-0.0) == "0"


def test_interpretation_wording():
    rng = np.random.default_rng(42)
    ts = trend_stats(YEARS, 100 + 2.0 * (YEARS - 2001) + rng.normal(0, 3, 25))
    out = interpret(
        name="Rainfall",
        region_name="Test",
        annual_unit="mm/year",
        start=2001,
        end=2025,
        ts=ts,
        cell_size="0.5°",
    )
    assert out["headline"].startswith("Rainfall increased")
    assert "per decade" in out["summary"]
    flat = trend_stats(YEARS, rng.normal(50, 5, 25))
    out = interpret(
        name="Rainfall",
        region_name="Test",
        annual_unit="mm/year",
        start=2001,
        end=2025,
        ts=flat,
        cell_size="0.5°",
    )
    assert "longer record" in out["summary"]
    for text in [out["headline"], out["summary"], *out["caveats"]]:
        assert "yield" not in text.lower()
