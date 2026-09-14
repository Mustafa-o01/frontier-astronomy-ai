"""Automated detector for catastrophic disintegrating exoplanets and cometary dust tails.

Distinguishes cometary dust tails from ordinary symmetric exoplanet transits through:
1. Multi-parameter forward model fitting (Rappaport/Brogi cometary profile vs Mandel-Agol/trapezoid).
2. Bayesian Information Criterion (BIC) hypothesis testing: Delta-BIC = BIC_sym - BIC_tail >= 10.0.
3. Likelihood Ratio Test (LRT): p-value < 1e-5 (Wilks' theorem, delta_k = 3).
4. Morphological transit duration asymmetry: alpha = (t_egress - t_ingress) / t_total > 0.30.
5. Multi-epoch stochastic transit depth variability tracking across individual orbits.
"""

from __future__ import annotations

from typing import Dict, List, Optional, Tuple, Union
import numpy as np
from scipy import optimize

from frontier_astronomy.core.types import LightCurveData, FoldedTransit, DustTailDetectionResult
from frontier_astronomy.core.preprocessing import fold_light_curve, inverse_variance_bin, epoch_split
from frontier_astronomy.core.math_utils import (
    bic,
    chi_squared,
    likelihood_ratio_test,
    symmetric_trapezoid_transit,
)
from frontier_astronomy.dust_tail.extinction_model import (
    cometary_extinction_profile,
    compute_asymmetry_parameter,
)
from frontier_astronomy.dust_tail.forward_scattering import forward_scattering_flux


def compute_multi_epoch_depth_variability(
    folded_or_lc: Union[FoldedTransit, LightCurveData],
    period: float,
    t0: float,
    transit_window: Tuple[float, float] = (-0.05, 0.15),
) -> Tuple[float, np.ndarray, float]:
    """Calculate the transit depth variability and variance across observed epochs.

    Args:
        folded_or_lc: FoldedTransit or LightCurveData object.
        period: Orbital period in days.
        t0: Reference transit epoch.
        transit_window: Phase range defining the transit event.

    Returns:
        Tuple of (depth_variance, epoch_depths_array, chi2_depth_variability).
    """
    if isinstance(folded_or_lc, FoldedTransit):
        phase = folded_or_lc.phase
        flux = folded_or_lc.flux
        epochs = folded_or_lc.epoch_indices
        err = folded_or_lc.flux_err
    else:
        from frontier_astronomy.core.preprocessing import phase_fold
        phase = phase_fold(folded_or_lc.time, period, t0)
        flux = folded_or_lc.flux
        epochs = epoch_split(folded_or_lc.time, period, t0)
        err = folded_or_lc.flux_err

    unique_epochs = np.unique(epochs)
    if len(unique_epochs) <= 1:
        return 0.0, np.array([], dtype=np.float64), 0.0

    epoch_depths = []
    epoch_errors = []

    for ep in unique_epochs:
        mask = (epochs == ep) & (phase >= transit_window[0]) & (phase <= transit_window[1])
        if np.sum(mask) >= 2:
            f_in = flux[mask]
            min_fl = float(np.min(f_in))
            d_ep = max(0.0, 1.0 - min_fl)
            e_ep = float(np.median(err[mask])) if len(err[mask]) > 0 else 0.001
            epoch_depths.append(d_ep)
            epoch_errors.append(e_ep)

    epoch_depths_arr = np.asarray(epoch_depths, dtype=np.float64)
    epoch_errors_arr = np.asarray(epoch_errors, dtype=np.float64)

    k_epochs = len(epoch_depths_arr)
    if k_epochs <= 1:
        return 0.0, epoch_depths_arr, 0.0

    variance = float(np.var(epoch_depths_arr, ddof=0))

    # Compute chi2 of depth variability against mean depth
    w = 1.0 / np.maximum(epoch_errors_arr, 1e-6) ** 2
    mean_depth = np.sum(w * epoch_depths_arr) / np.sum(w)
    chi2_depth = float(np.sum(((epoch_depths_arr - mean_depth) / np.maximum(epoch_errors_arr, 1e-6)) ** 2))

    return variance, epoch_depths_arr, chi2_depth


def fit_symmetric_transit(
    phase: np.ndarray,
    flux: np.ndarray,
    flux_err: np.ndarray,
    period: float,
    initial_depth: float = 0.010,
    initial_duration_phase: float = 0.040,
) -> Tuple[np.ndarray, Dict[str, float], float, float]:
    """Fit a standard symmetric trapezoidal transit model to phase-folded photometry.

    Model parameters: [depth, duration_phase, ingress_ratio, t_offset] (k = 5 free parameters).

    Returns:
        Tuple of (best_fit_flux, fit_params_dict, bic_value, chi2_value).
    """
    ph = np.asarray(phase, dtype=np.float64)
    fl = np.asarray(flux, dtype=np.float64)
    fe = np.asarray(flux_err, dtype=np.float64)
    fe = np.where(fe > 1e-8, fe, 1e-6)

    # Coarse grid search for initial guess
    d0 = float(np.clip(initial_depth, 0.0, 0.5))
    dur0 = float(np.clip(initial_duration_phase, 0.01, 0.20))

    def residuals(params: np.ndarray) -> np.ndarray:
        depth_val, dur_val, ing_val, offset_val = params
        shifted_ph = ph - offset_val
        model = symmetric_trapezoid_transit(
            phase=shifted_ph,
            period=period,
            depth=depth_val,
            duration_phase=dur_val,
            ingress_ratio=ing_val,
        )
        return (fl - model) / fe

    p0 = [max(1e-4, d0), dur0, 0.20, 0.0]
    bounds = (
        [0.0, 0.005, 0.05, -0.05],
        [0.8, 0.350, 0.45,  0.05],
    )

    try:
        res = optimize.least_squares(
            residuals,
            p0,
            bounds=bounds,
            ftol=1e-5,
            xtol=1e-5,
            max_nfev=150,
        )
        best_p = res.x
    except Exception:
        best_p = p0

    shifted_ph = ph - best_p[3]
    best_model = symmetric_trapezoid_transit(
        phase=shifted_ph,
        period=period,
        depth=best_p[0],
        duration_phase=best_p[1],
        ingress_ratio=best_p[2],
    )

    k_sym = 5
    bic_val = bic(fl, best_model, fe, k=k_sym)
    chi2_val = chi_squared(fl, best_model, fe)

    fit_params = {
        "depth": float(best_p[0]),
        "duration_phase": float(best_p[1]),
        "ingress_ratio": float(best_p[2]),
        "t_offset": float(best_p[3]),
    }
    return best_model, fit_params, bic_val, chi2_val


def fit_cometary_dust_tail(
    phase: np.ndarray,
    flux: np.ndarray,
    flux_err: np.ndarray,
    initial_depth: float = 0.010,
    initial_tail_scale: float = 0.050,
) -> Tuple[np.ndarray, Dict[str, float], float, float]:
    """Fit a cometary dust tail extinction and forward scattering model to phase-folded photometry.

    Model parameters: [depth, sigma_ing, lambda_tail, alpha, phi_offset, f_scat] (k = 8 free parameters).

    Returns:
        Tuple of (best_fit_flux, fit_params_dict, bic_value, chi2_value).
    """
    ph = np.asarray(phase, dtype=np.float64)
    fl = np.asarray(flux, dtype=np.float64)
    fe = np.asarray(flux_err, dtype=np.float64)
    fe = np.where(fe > 1e-8, fe, 1e-6)

    d0 = float(np.clip(initial_depth, 0.0, 0.5))
    tail0 = float(np.clip(initial_tail_scale, 0.01, 0.20))

    def residuals(params: np.ndarray) -> np.ndarray:
        depth_val, sig_ing_val, lam_tail_val, alpha_val, offset_val, f_scat_val = params
        model = cometary_extinction_profile(
            phase=ph,
            depth=depth_val,
            sigma_ing=sig_ing_val,
            lambda_tail=lam_tail_val,
            alpha=alpha_val,
            phi_offset=offset_val,
            f_scat=f_scat_val,
            phi_scat=-0.020,
            sigma_scat=0.008,
        )
        return (fl - model) / fe

    p0 = [max(1e-4, d0), 0.004, tail0, 1.0, 0.012, 0.0005]
    bounds = (
        [0.0, 0.0005, 0.005, 0.4, -0.06, 0.000],
        [0.8, 0.0250, 0.300, 2.5,  0.06, 0.015],
    )

    try:
        res = optimize.least_squares(
            residuals,
            p0,
            bounds=bounds,
            ftol=1e-5,
            xtol=1e-5,
            max_nfev=200,
        )
        best_p = res.x
    except Exception:
        best_p = p0

    best_model = cometary_extinction_profile(
        phase=ph,
        depth=best_p[0],
        sigma_ing=best_p[1],
        lambda_tail=best_p[2],
        alpha=best_p[3],
        phi_offset=best_p[4],
        f_scat=best_p[5],
        phi_scat=-0.020,
        sigma_scat=0.008,
    )

    k_tail = 8
    bic_val = bic(fl, best_model, fe, k=k_tail)
    chi2_val = chi_squared(fl, best_model, fe)

    fit_params = {
        "depth": float(best_p[0]),
        "sigma_ing": float(best_p[1]),
        "lambda_tail": float(best_p[2]),
        "alpha": float(best_p[3]),
        "phi_offset": float(best_p[4]),
        "f_scat": float(best_p[5]),
    }
    return best_model, fit_params, bic_val, chi2_val


class DustTailDetector:
    """Detection engine for catastrophic disintegrating exoplanets and dust tails."""

    def __init__(
        self,
        min_delta_bic: float = 10.0,
        max_lrt_p_value: float = 1e-5,
        min_asymmetry: float = 0.25,
        n_phase_bins: int = 120,
    ) -> None:
        self.min_delta_bic = min_delta_bic
        self.max_lrt_p_value = max_lrt_p_value
        self.min_asymmetry = min_asymmetry
        self.n_phase_bins = n_phase_bins

    def detect(
        self,
        light_curve: Union[LightCurveData, FoldedTransit],
        period: Optional[float] = None,
        t0: Optional[float] = None,
    ) -> DustTailDetectionResult:
        """Run full detection pipeline on light curve or folded transit data."""
        return detect_dust_tail(
            light_curve=light_curve,
            period=period,
            t0=t0,
            min_delta_bic=self.min_delta_bic,
            max_lrt_p_value=self.max_lrt_p_value,
            min_asymmetry=self.min_asymmetry,
            n_phase_bins=self.n_phase_bins,
        )


def detect_dust_tail(
    light_curve: Union[LightCurveData, FoldedTransit],
    period: Optional[float] = None,
    t0: Optional[float] = None,
    min_delta_bic: float = 10.0,
    max_lrt_p_value: float = 1e-5,
    min_asymmetry: float = 0.25,
    n_phase_bins: int = 120,
) -> DustTailDetectionResult:
    """Analyze light curve photometry to detect cometary dust tail morphology.

    Executes:
    1. Phase folding and epoch indexing.
    2. Symmetric transit model optimization (k=5).
    3. Cometary dust tail model optimization (k=8).
    4. Model selection: Delta-BIC = BIC_sym - BIC_tail.
    5. Likelihood Ratio Test: LRT p-value (delta_k = 3).
    6. Transit duration asymmetry parameter alpha.
    7. Multi-epoch transit depth variability.

    Args:
        light_curve: Input LightCurveData or FoldedTransit.
        period: Orbital period in days (required if LightCurveData lacks metadata).
        t0: Reference transit epoch (BKJD/BTJD).
        min_delta_bic: Threshold Delta-BIC for positive detection (nominal = 10.0).
        max_lrt_p_value: Maximum LRT p-value (nominal = 1e-5).
        min_asymmetry: Minimum asymmetry parameter alpha (nominal = 0.25).
        n_phase_bins: Number of bins for coarse phase analysis.

    Returns:
        DustTailDetectionResult matching PROJECT.md interface contract.
    """
    if isinstance(light_curve, FoldedTransit):
        folded = light_curve
        target_id = getattr(folded, "target_id", "TARGET")
        p_days = float(period if period is not None else folded.period)
        t0_val = float(t0 if t0 is not None else folded.t0)
        source_lc = None
    elif isinstance(light_curve, LightCurveData):
        source_lc = light_curve
        target_id = light_curve.target_id
        meta = light_curve.metadata
        p_days = float(period if period is not None else meta.get("period_days", meta.get("period", 0.65355)))
        t0_val = float(t0 if t0 is not None else meta.get("t0_days", meta.get("t0", 120.0)))
        folded = fold_light_curve(light_curve, p_days, t0_val, sort=True)
    else:
        raise TypeError(f"Unsupported light curve type: {type(light_curve)}")

    n_pts = folded.n_points
    if n_pts < 10:
        return DustTailDetectionResult(
            target_id=target_id,
            period=p_days,
            t0=t0_val,
            is_asymmetric_dust_tail=False,
            delta_bic=0.0,
            lrt_p_value=1.0,
            asymmetry_parameter=0.0,
            peak_depth=0.0,
            tail_decay_length=0.0,
            forward_scattering_amp=0.0,
            depth_variance=0.0,
            best_fit_model=np.ones(max(1, n_pts), dtype=np.float64),
        )

    # Initial dip estimation from transit region [-0.05, 0.05]
    tr_mask = (folded.phase >= -0.05) & (folded.phase <= 0.05)
    if np.any(tr_mask):
        dip_est = max(0.0, float(1.0 - np.min(folded.flux[tr_mask])))
    else:
        dip_est = max(0.0, float(1.0 - np.min(folded.flux)))

    # Fit symmetric model (k=5)
    y_sym, p_sym, bic_sym, chi2_sym = fit_symmetric_transit(
        phase=folded.phase,
        flux=folded.flux,
        flux_err=folded.flux_err,
        period=p_days,
        initial_depth=max(dip_est, 0.005),
    )

    # Fit cometary dust tail model (k=8)
    y_tail, p_tail, bic_tail, chi2_tail = fit_cometary_dust_tail(
        phase=folded.phase,
        flux=folded.flux,
        flux_err=folded.flux_err,
        initial_depth=max(dip_est, 0.005),
    )

    # Delta-BIC = BIC(sym) - BIC(tail)
    db = float(bic_sym - bic_tail)

    # Likelihood Ratio Test: delta_k = 8 - 5 = 3
    p_lrt = likelihood_ratio_test(chi2_sym, chi2_tail, delta_k=3)

    # Asymmetry parameter alpha = (t_egress - t_ingress) / t_total
    asym_param = compute_asymmetry_parameter(folded.phase, y_tail)

    # Depth variance across epochs
    if source_lc is not None:
        depth_var, _, _ = compute_multi_epoch_depth_variability(source_lc, p_days, t0_val)
    else:
        depth_var, _, _ = compute_multi_epoch_depth_variability(folded, p_days, t0_val)

    # Detection decision:
    # True if Delta-BIC >= 10, LRT p < 1e-5, and asym_param >= min_asymmetry
    is_dust_tail = bool(
        (db >= min_delta_bic)
        and (p_lrt < max_lrt_p_value)
        and (min_asymmetry is None or asym_param >= min_asymmetry)
    )

    return DustTailDetectionResult(
        target_id=target_id,
        period=p_days,
        t0=t0_val,
        is_asymmetric_dust_tail=is_dust_tail,
        delta_bic=db,
        lrt_p_value=p_lrt,
        asymmetry_parameter=asym_param,
        peak_depth=float(p_tail["depth"]),
        tail_decay_length=float(p_tail["lambda_tail"]),
        forward_scattering_amp=float(p_tail["f_scat"]),
        depth_variance=float(depth_var),
        best_fit_model=y_tail,
    )
