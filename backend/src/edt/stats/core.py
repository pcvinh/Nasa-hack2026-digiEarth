"""One statistics module: annual aggregation, trend statistics and plain-language interpretation.

Method (ARCHITECTURE.md section 6): stats on annual values; Mann-Kendall (original, two-sided)
+ Sen's slope is the headline; OLS + two-sided t-test + 95% CI alongside.
"""

from __future__ import annotations

import math
from dataclasses import dataclass, field

import numpy as np
import pymannkendall as pmk
from scipy import stats as sps

MIN_YEARS = 10
NEAR_THRESHOLD = 0.02  # |p − alpha| within this → "close to the threshold" caveat
MK_METHOD = "Mann-Kendall (original, two-sided) with Sen's slope on annual values"
OLS_METHOD = "OLS on annual values; two-sided t-test; 95% CI = slope ± t(0.975, n−2) × SE"


def annual_values(monthly: np.ndarray, aggregation: str) -> np.ndarray:
    """monthly: shape (n_years*12,), NaN = missing. A year with any missing month → NaN."""
    m = np.asarray(monthly, dtype=np.float64).reshape(-1, 12)
    complete = np.isfinite(m).all(axis=1)
    agg = m.sum(axis=1) if aggregation == "sum" else m.mean(axis=1)
    return np.where(complete, agg, np.nan)


def monthly_anomalies(monthly: np.ndarray) -> np.ndarray:
    """Value minus the mean of the same calendar month over the analysis period."""
    m = np.asarray(monthly, dtype=np.float64).reshape(-1, 12)
    with np.errstate(invalid="ignore"), _quiet():
        clim = np.nanmean(m, axis=0)
    return (m - clim).ravel()


class _quiet:
    def __enter__(self):
        import warnings

        self._w = warnings.catch_warnings()
        self._w.__enter__()
        warnings.simplefilter("ignore", RuntimeWarning)

    def __exit__(self, *a):
        self._w.__exit__(*a)


def sen_slope(x: np.ndarray, y: np.ndarray) -> tuple[float, float]:
    """Theil-Sen slope with real x spacing; intercept = median(y) − slope·median(x)."""
    i, j = np.triu_indices(len(x), k=1)
    slope = float(np.median((y[j] - y[i]) / (x[j] - x[i])))
    return slope, float(np.median(y) - slope * np.median(x))


@dataclass
class TrendStats:
    n: int
    alpha: float
    status: str  # significant | not_significant | insufficient_data
    direction: str  # increasing | decreasing | no_change
    agreement: str  # both | mann_kendall_only | ols_only | neither
    sen_per_year: float | None = None
    sen_intercept: float | None = None
    tau: float | None = None
    mk_p: float | None = None
    ols_per_year: float | None = None
    ols_intercept: float | None = None
    ols_ci_per_year: tuple[float, float] | None = None
    ols_p: float | None = None
    r_squared: float | None = None
    excluded_years: list[int] = field(default_factory=list)


def trend_stats(years: np.ndarray, values: np.ndarray, alpha: float = 0.05) -> TrendStats:
    years = np.asarray(years, dtype=np.float64)
    values = np.asarray(values, dtype=np.float64)
    ok = np.isfinite(values)
    x, y = years[ok], values[ok]
    n = int(ok.sum())
    excluded = [int(v) for v in years[~ok]]
    if n < MIN_YEARS:
        return TrendStats(
            n, alpha, "insufficient_data", "no_change", "neither", excluded_years=excluded
        )

    mk = pmk.original_test(y, alpha=alpha)
    slope, intercept = sen_slope(x, y)
    lr = sps.linregress(x, y)
    tcrit = float(sps.t.ppf(0.975, n - 2))
    ci = (float(lr.slope - tcrit * lr.stderr), float(lr.slope + tcrit * lr.stderr))
    mk_sig = bool(mk.p < alpha)
    ols_sig = bool(lr.pvalue < alpha)
    agreement = {
        (True, True): "both",
        (True, False): "mann_kendall_only",
        (False, True): "ols_only",
        (False, False): "neither",
    }[(mk_sig, ols_sig)]
    direction = "increasing" if slope > 0 else "decreasing" if slope < 0 else "no_change"
    return TrendStats(
        n=n,
        alpha=alpha,
        status="significant" if mk_sig else "not_significant",
        direction=direction,
        agreement=agreement,
        sen_per_year=slope,
        sen_intercept=intercept,
        tau=float(mk.Tau),
        mk_p=float(mk.p),
        ols_per_year=float(lr.slope),
        ols_intercept=float(lr.intercept),
        ols_ci_per_year=ci,
        ols_p=float(lr.pvalue),
        r_squared=float(lr.rvalue**2),
        excluded_years=excluded,
    )


# ---------------------------------------------------------------- formatting / interpretation


def sig2(v: float | None) -> float | None:
    """Round to 2 significant figures."""
    if v is None or not math.isfinite(v):
        return None
    if v == 0:
        return 0.0
    return round(v, 1 - int(math.floor(math.log10(abs(v)))))


def fmt_num(v: float) -> str:
    r = sig2(v)
    if r is None:
        return "n/a"
    s = f"{r:,.10f}".rstrip("0").rstrip(".")
    return s if s not in ("-0", "") else "0"


def fmt_p(p: float) -> str:
    return "p < 0.001" if p < 0.001 else f"p = {p:.2g}" if p < 0.01 else f"p = {p:.2f}"


ALWAYS_CAVEATS = [
    "Linear trend only: a straight-line trend can hide changes that speed up, slow down or "
    "reverse.",
    "Annual values can still be autocorrelated (one year influences the next), which can make "
    "p-values look smaller than they should.",
    "A trend is not a cause: this tool shows what changed, not why.",
]


def interpret(
    *,
    name: str,
    region_name: str,
    annual_unit: str,
    start: int,
    end: int,
    ts: TrendStats,
    cell_size: str,
    extra_caveats: list[str] | None = None,
) -> dict:
    caveats = []
    if ts.mk_p is not None and round(abs(ts.mk_p - ts.alpha), 9) <= NEAR_THRESHOLD:
        caveats.append(
            f"The Mann-Kendall p-value ({fmt_p(ts.mk_p)}) is close to the significance threshold "
            f"(α = {ts.alpha:g}), so the verdict is borderline and could change with a "
            "different area or grid."
        )
    caveats.extend(ALWAYS_CAVEATS)
    caveats.append(
        f"Grid cells are about {cell_size} (roughly 50 km or more across), so results describe "
        "the wider area, not a single field or town."
    )
    if ts.excluded_years:
        yrs = ", ".join(str(y) for y in ts.excluded_years)
        caveats.append(
            f"{len(ts.excluded_years)} year(s) had at least one missing month and were left "
            f"out: {yrs}."
        )
    caveats.extend(extra_caveats or [])
    lname = name[0].lower() + name[1:]

    if ts.status == "insufficient_data":
        return {
            "headline": f"Not enough data to test for a trend in {lname}",
            "summary": (
                f"Only {ts.n} complete year(s) of {lname} are available for {region_name} "
                f"between {start} and {end}. At least {MIN_YEARS} are needed for a trend test."
            ),
            "caveats": caveats,
        }

    per_dec = ts.sen_per_year * 10
    total = ts.sen_per_year * (end - start)
    if ts.status == "significant":
        verb = "increased" if ts.direction == "increasing" else "decreased"
        headline = f"{name} {verb}, and the trend is statistically significant"
        trend_sentence = f"This trend is statistically significant (Mann-Kendall {fmt_p(ts.mk_p)})."
    else:
        verb = "changed"
        headline = f"No clear change in {lname}: the trend is not statistically significant"
        trend_sentence = (
            f"This trend is not statistically significant (Mann-Kendall {fmt_p(ts.mk_p)}). "
            "A trend can become significant with a longer record."
        )
    if ts.status == "significant":
        change = (
            f"{name} in {region_name} {verb} by about {fmt_num(abs(per_dec))} {annual_unit} "
            f"per decade from {start} to {end}"
        )
    else:
        sign = "+" if per_dec > 0 else "−" if per_dec < 0 else ""
        change = (
            f"{name} in {region_name} {verb} by about {sign}{fmt_num(abs(per_dec))} "
            f"{annual_unit} per decade from {start} to {end}"
        )
    total_sentence = (
        f"Along the trend line that is about {'+' if total > 0 else '−' if total < 0 else ''}"
        f"{fmt_num(abs(total))} {annual_unit} over the whole period."
    )
    agree = {
        "both": "The straight-line (OLS) t-test agrees.",
        "mann_kendall_only": "The straight-line (OLS) t-test does not reach significance, so "
        "treat the trend with some caution.",
        "ols_only": "The straight-line (OLS) t-test is significant, but the more robust "
        "Mann-Kendall test is not, so the evidence is weak.",
        "neither": "The straight-line (OLS) t-test is not significant either.",
    }[ts.agreement]
    summary = f"{change} (Sen's slope). {total_sentence} {trend_sentence} {agree}"
    return {"headline": headline, "summary": summary, "caveats": caveats}
