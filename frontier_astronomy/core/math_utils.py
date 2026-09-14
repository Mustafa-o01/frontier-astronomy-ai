"""Mathematical and statistical utilities for exoplanetary astrophysics.

Includes model selection metrics (BIC, AIC, LRT, Chi2), robust statistical estimators
(asymmetric MAD, running medians), transit geometric approximations, and numerical filters.
"""

from __future__ import annotations

from typing import Tuple, Union
import numpy as np
from scipy import stats, ndimage


def safe_divide(
    numerator: np.ndarray | float,
    denominator: np.ndarray | float,
    fill_value: float = 0.0,
) -> np.ndarray | float:
    """Perform element-wise division safely avoiding divide-by-zero or NaN."""
    with np.errstate(divide="ignore", invalid="ignore"):
        result = np.true_divide(numerator, denominator)
        if isinstance(result, np.ndarray):
            result[~np.isfinite(result)] = fill_value
        elif not np.isfinite(result):
            result = fill_value
    return result


def chi_squared(
    y_true: np.ndarray,
    y_pred: np.ndarray,
    y_err: np.ndarray,
) -> float:
    """Calculate standard chi-squared statistic.

    chi2 = sum(((y_true - y_pred) / y_err) ** 2)
    """
    y_t = np.asarray(y_true, dtype=np.float64)
    y_p = np.asarray(y_pred, dtype=np.float64)
    y_e = np.asarray(y_err, dtype=np.float64)

    valid = np.isfinite(y_t) & np.isfinite(y_p) & np.isfinite(y_e) & (y_e > 0)
    if not np.any(valid):
        return float("inf")

    residuals = (y_t[valid] - y_p[valid]) / y_e[valid]
    return float(np.sum(residuals ** 2))


def reduced_chi_squared(
    y_true: np.ndarray,
    y_pred: np.ndarray,
    y_err: np.ndarray,
    k: int,
) -> float:
    """Calculate reduced chi-squared statistic chi2 / dof.

    dof = N - k, where N is the number of valid observations and k is free parameters.
    """
    y_t = np.asarray(y_true, dtype=np.float64)
    y_p = np.asarray(y_pred, dtype=np.float64)
    y_e = np.asarray(y_err, dtype=np.float64)

    valid = np.isfinite(y_t) & np.isfinite(y_p) & np.isfinite(y_e) & (y_e > 0)
    n = int(np.sum(valid))
    dof = n - k
    if dof <= 0:
        return float("inf")

    chi2_val = chi_squared(y_t[valid], y_p[valid], y_e[valid])
    return chi2_val / dof


def bic(
    y_true: np.ndarray,
    y_pred: np.ndarray,
    y_err: np.ndarray,
    k: int,
) -> float:
    """Calculate Bayesian Information Criterion (BIC).

    BIC = k * ln(N) + chi2
    """
    y_t = np.asarray(y_true, dtype=np.float64)
    y_p = np.asarray(y_pred, dtype=np.float64)
    y_e = np.asarray(y_err, dtype=np.float64)

    valid = np.isfinite(y_t) & np.isfinite(y_p) & np.isfinite(y_e) & (y_e > 0)
    n = int(np.sum(valid))
    if n <= 0 or n <= k:
        return float("inf")

    chi2_val = chi_squared(y_t[valid], y_p[valid], y_e[valid])
    return float(k * np.log(n) + chi2_val)


def aic(
    y_true: np.ndarray,
    y_pred: np.ndarray,
    y_err: np.ndarray,
    k: int,
) -> float:
    """Calculate Akaike Information Criterion (AIC).

    AIC = 2*k + chi2
    """
    chi2_val = chi_squared(y_true, y_pred, y_err)
    return float(2 * k + chi2_val)


def delta_bic(bic_null: float, bic_alt: float) -> float:
    """Calculate Delta-BIC favoring alternative hypothesis.

    Delta-BIC = BIC(null) - BIC(alt).
    Values >= 10 indicate decisive statistical evidence for the alternative model.
    """
    return float(bic_null - bic_alt)


def likelihood_ratio_test(
    chi2_null: float,
    chi2_alt: float,
    delta_k: int,
) -> float:
    """Perform Likelihood Ratio Test (LRT) between nested or comparative models.

    Under the null hypothesis, Lambda = chi2_null - chi2_alt asymptotically follows
    a chi^2 distribution with delta_k degrees of freedom (Wilks' theorem).

    Returns:
        p-value (survival function of chi2 distribution).
    """
    if delta_k <= 0:
        raise ValueError(f"Degrees of freedom delta_k must be positive, got {delta_k}")

    delta_chi2 = float(chi2_null - chi2_alt)
    if delta_chi2 <= 0.0:
        return 1.0  # Null hypothesis cannot be rejected

    # Compute survival function sf = 1 - cdf
    p_val = float(stats.chi2.sf(delta_chi2, df=delta_k))
    return p_val


def median_absolute_deviation(x: np.ndarray, scale: float = 1.4826) -> float:
    """Calculate the Median Absolute Deviation (MAD) of a 1D array.

    sigma_MAD = scale * median(|x - median(x)|)
    For a Gaussian distribution, scale = 1.4826 gives the standard deviation.
    """
    arr = np.asarray(x, dtype=np.float64)
    arr = arr[np.isfinite(arr)]
    if len(arr) == 0:
        return 0.0
    med = np.median(arr)
    mad = np.median(np.abs(arr - med))
    return float(scale * mad)


def running_median(x: np.ndarray, window_length: int) -> np.ndarray:
    """Calculate running median using SciPy's 1D median filter.

    Ensures window_length is odd and >= 3.
    """
    arr = np.asarray(x, dtype=np.float64)
    if len(arr) == 0:
        return np.array([], dtype=np.float64)
    if window_length < 3:
        return arr.copy()
    if window_length % 2 == 0:
        window_length += 1
    if window_length > len(arr):
        window_length = len(arr) if len(arr) % 2 != 0 else len(arr) - 1
        if window_length < 1:
            return arr.copy()

    return ndimage.median_filter(arr, size=window_length, mode="reflect")


def weighted_mean_and_std(
    values: np.ndarray,
    weights: np.ndarray,
) -> Tuple[float, float]:
    """Compute weighted mean and standard deviation from inverse-variance weights.

    w_i = 1 / sigma_i^2
    mean = sum(w_i * x_i) / sum(w_i)
    variance = 1 / sum(w_i)
    """
    val = np.asarray(values, dtype=np.float64)
    w = np.asarray(weights, dtype=np.float64)

    valid = np.isfinite(val) & np.isfinite(w) & (w > 0)
    if not np.any(valid):
        return float("nan"), float("nan")

    v_val = val[valid]
    v_w = w[valid]
    sum_w = np.sum(v_w)

    w_mean = float(np.sum(v_val * v_w) / sum_w)
    w_std = float(1.0 / np.sqrt(sum_w))
    return w_mean, w_std


def henyey_greenstein_phase_function(g: float, theta: np.ndarray | float) -> np.ndarray | float:
    """Compute Henyey-Greenstein scattering phase function.

    p(theta) = (1 - g^2) / (4 * pi * (1 + g^2 - 2 * g * cos(theta))^(3/2))
    where g is the asymmetry parameter in (-1, 1).
    """
    g = float(np.clip(g, -0.999, 0.999))
    denom = (1.0 + g ** 2 - 2.0 * g * np.cos(theta)) ** 1.5
    denom = np.maximum(denom, 1e-12)
    return (1.0 - g ** 2) / (4.0 * np.pi * denom)


def symmetric_trapezoid_transit(
    phase: np.ndarray,
    period: float,
    depth: float,
    duration_phase: float,
    ingress_ratio: float = 0.2,
) -> np.ndarray:
    """Generate a standard symmetric trapezoidal transit model across orbital phase [-0.5, 0.5].

    Args:
        phase: 1D array of orbital phases in [-0.5, 0.5)
        period: Orbital period (days)
        depth: Transit depth (fractional flux extinction)
        duration_phase: Transit duration in phase units
        ingress_ratio: Fraction of transit duration spent in ingress/egress (tau_ing / T_dur)

    Returns:
        1D array of model flux values (normalized to baseline 1.0)
    """
    p = np.asarray(phase, dtype=np.float64)
    phi = np.abs(p)  # Symmetric about phase 0

    half_dur = 0.5 * duration_phase
    t_ingress = ingress_ratio * duration_phase
    half_flat = max(0.0, half_dur - t_ingress)

    model = np.ones_like(phi)

    # Flat bottom
    flat_mask = phi <= half_flat
    model[flat_mask] = 1.0 - depth

    # Ingress / Egress slopes
    slope_mask = (phi > half_flat) & (phi < half_dur)
    if t_ingress > 0:
        frac = (half_dur - phi[slope_mask]) / t_ingress
        model[slope_mask] = 1.0 - depth * frac

    return model
