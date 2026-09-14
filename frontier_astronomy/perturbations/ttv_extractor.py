"""Transit Timing Variation (TTV) extraction via template cross-correlation.

Extracts sub-cadence O-C (Observed minus Calculated) transit timing residuals
per epoch using weighted template cross-correlation and parabolic refinement.
Handles arbitrary epoch gaps, missing cadences, and realistic noise baselines.
"""

from __future__ import annotations

from dataclasses import dataclass
from typing import Optional, Tuple, Dict, Any, Union
import numpy as np

from frontier_astronomy.core.types import LightCurveData
from frontier_astronomy.core.math_utils import symmetric_trapezoid_transit
from frontier_astronomy.core.preprocessing import epoch_split


@dataclass(frozen=True)
class TTVExtractionResult:
    """Container for per-epoch transit timing variations."""
    epochs: np.ndarray                  # 1D int32 array of observed transit epoch numbers
    transit_times: np.ndarray           # 1D float64 array of fitted mid-transit times (days)
    ttv_minutes: np.ndarray             # 1D float64 array of O-C residuals (minutes)
    ttv_errors_minutes: np.ndarray      # 1D float64 array of 1-sigma timing uncertainties (minutes)
    linear_period: float                # Refined mean orbital period (days)
    linear_t0: float                    # Refined transit epoch reference (days)
    snr: float                          # TTV signal-to-noise ratio

    def __post_init__(self) -> None:
        object.__setattr__(self, "epochs", np.asarray(self.epochs, dtype=np.int32))
        object.__setattr__(self, "transit_times", np.asarray(self.transit_times, dtype=np.float64))
        object.__setattr__(self, "ttv_minutes", np.asarray(self.ttv_minutes, dtype=np.float64))
        object.__setattr__(self, "ttv_errors_minutes", np.asarray(self.ttv_errors_minutes, dtype=np.float64))


def _fit_transit_midpoint(
    t_win: np.ndarray,
    f_win: np.ndarray,
    fe_win: np.ndarray,
    t_nom: float,
    period: float,
    duration_days: float,
    depth: float,
    search_half_width_days: float,
    n_grid: int = 81,
) -> Tuple[float, float]:
    """Fit mid-transit time using template chi-squared grid and parabolic interpolation."""
    if len(t_win) < 3 or depth <= 0:
        return t_nom, float(duration_days * 1440.0 / 4.0)

    dur_phase = duration_days / period
    tau_grid = np.linspace(-search_half_width_days, search_half_width_days, n_grid)
    weights = 1.0 / np.maximum(fe_win, 1e-7) ** 2

    chi2_vals = np.zeros(n_grid, dtype=np.float64)

    for i, tau in enumerate(tau_grid):
        t_center = t_nom + tau
        phase_eval = ((t_win - t_center) / period + 0.5) % 1.0 - 0.5
        model = symmetric_trapezoid_transit(
            phase=phase_eval,
            period=period,
            depth=depth,
            duration_phase=dur_phase,
            ingress_ratio=0.15,
        )
        chi2_vals[i] = np.sum(weights * (f_win - model) ** 2)

    min_idx = int(np.argmin(chi2_vals))

    # Parabolic sub-grid interpolation
    if 0 < min_idx < (n_grid - 1):
        y0 = chi2_vals[min_idx - 1]
        y1 = chi2_vals[min_idx]
        y2 = chi2_vals[min_idx + 1]
        denom = 2.0 * (y0 - 2.0 * y1 + y2)
        if denom > 1e-12:
            delta_idx = (y0 - y2) / denom
            dtau = tau_grid[1] - tau_grid[0]
            tau_best = tau_grid[min_idx] + delta_idx * dtau
            # Curvature-based formal uncertainty
            d2chi2 = (y0 - 2.0 * y1 + y2) / (dtau ** 2)
            sigma_tau = float(np.sqrt(2.0 / max(d2chi2, 1e-12)))
        else:
            tau_best = tau_grid[min_idx]
            sigma_tau = float(search_half_width_days / 4.0)
    else:
        tau_best = tau_grid[min_idx]
        sigma_tau = float(search_half_width_days / 3.0)

    # Uncertainty in minutes
    sigma_min = max(0.1, sigma_tau * 1440.0)
    return float(t_nom + tau_best), float(sigma_min)


def extract_ttv(
    time: np.ndarray,
    flux: np.ndarray,
    flux_err: np.ndarray,
    period: float,
    t0: float,
    duration_hours: Optional[float] = None,
    depth: Optional[float] = None,
) -> TTVExtractionResult:
    """Extract Transit Timing Variations (TTVs) across all observed epochs.

    Args:
        time: 1D array of cadence timestamps (days).
        flux: 1D array of normalized flux values.
        flux_err: 1D array of flux uncertainties.
        period: Approximate orbital period (days).
        t0: Approximate mid-transit epoch (days).
        duration_hours: Nominal transit duration in hours (defaults to 4.0 if None).
        depth: Nominal transit depth (estimated from data if None).

    Returns:
        TTVExtractionResult instance containing per-epoch residuals and metrics.
    """
    t = np.asarray(time, dtype=np.float64)
    f = np.asarray(flux, dtype=np.float64)
    fe = np.asarray(flux_err, dtype=np.float64)

    if period <= 0:
        raise ValueError(f"Orbital period must be positive, got {period}")

    if duration_hours is None or duration_hours <= 0:
        duration_hours = 4.0
    dur_days = duration_hours / 24.0

    # Auto-estimate depth if not provided
    if depth is None or depth <= 0:
        phase = ((t - t0) / period + 0.5) % 1.0 - 0.5
        in_transit = np.abs(phase) < ((dur_days / 2.0) / period)
        if np.any(in_transit):
            depth = float(max(0.001, 1.0 - np.percentile(f[in_transit], 10)))
        else:
            depth = 0.01

    # Group cadences by transit epoch
    epochs_all = epoch_split(t, period, t0)
    unique_epochs = np.unique(epochs_all)

    observed_epochs = []
    observed_times = []
    observed_ttv_min = []
    observed_errors_min = []

    search_half_width_days = min(0.4 * period, max(0.04, dur_days * 0.75))

    for ep in unique_epochs:
        t_nom = t0 + ep * period
        # Window of cadences around this epoch
        mask = np.abs(t - t_nom) < (dur_days * 1.5)
        # Check if enough in-transit points exist
        if np.sum(mask) < 3:
            continue

        t_win = t[mask]
        f_win = f[mask]
        fe_win = fe[mask]

        t_fit, err_min = _fit_transit_midpoint(
            t_win=t_win,
            f_win=f_win,
            fe_win=fe_win,
            t_nom=t_nom,
            period=period,
            duration_days=dur_days,
            depth=depth,
            search_half_width_days=search_half_width_days,
        )

        observed_epochs.append(ep)
        observed_times.append(t_fit)
        observed_errors_min.append(err_min)

    n_det = len(observed_epochs)
    if n_det < 2:
        # Boundary case: insufficient epochs (< 2)
        if n_det == 1:
            ep_arr = np.array(observed_epochs, dtype=np.int32)
            times_arr = np.array(observed_times, dtype=np.float64)
            ttv_arr = np.array([0.0], dtype=np.float64)
            err_arr = np.array(observed_errors_min, dtype=np.float64)
            return TTVExtractionResult(
                epochs=ep_arr,
                transit_times=times_arr,
                ttv_minutes=ttv_arr,
                ttv_errors_minutes=err_arr,
                linear_period=period,
                linear_t0=t0,
                snr=0.0,
            )
        else:
            return TTVExtractionResult(
                epochs=np.array([], dtype=np.int32),
                transit_times=np.array([], dtype=np.float64),
                ttv_minutes=np.array([], dtype=np.float64),
                ttv_errors_minutes=np.array([], dtype=np.float64),
                linear_period=period,
                linear_t0=t0,
                snr=0.0,
            )

    ep_arr = np.array(observed_epochs, dtype=np.int32)
    times_arr = np.array(observed_times, dtype=np.float64)
    err_arr = np.array(observed_errors_min, dtype=np.float64)

    # Linear ephemeris weighted least squares fit: t_fit = t0_ref + ep * P_ref
    weights = 1.0 / np.maximum(err_arr, 1e-4) ** 2
    x = ep_arr.astype(np.float64)
    y = times_arr

    # Polyfit degree 1 with weights
    p_fit = np.polyfit(x, y, 1, w=np.sqrt(weights))
    linear_period = float(p_fit[0])
    linear_t0 = float(p_fit[1])

    # Calculated linear times
    t_calc = linear_t0 + ep_arr * linear_period
    ttv_days = times_arr - t_calc
    ttv_minutes = ttv_days * 1440.0

    # Calculate TTV signal-to-noise ratio
    # SNR = std(TTV) / mean(sigma_TTV) * sqrt(2)
    std_ttv = float(np.std(ttv_minutes))
    mean_err = float(np.mean(err_arr)) if len(err_arr) > 0 else 1.0
    if mean_err > 0.0 and std_ttv > 0.0:
        snr_val = float((std_ttv / mean_err) * np.sqrt(2.0))
    else:
        snr_val = 0.0

    return TTVExtractionResult(
        epochs=ep_arr,
        transit_times=times_arr,
        ttv_minutes=ttv_minutes,
        ttv_errors_minutes=err_arr,
        linear_period=linear_period,
        linear_t0=linear_t0,
        snr=snr_val,
    )


def extract_ttv_from_light_curve(
    lc: LightCurveData,
    period: float,
    t0: float,
    duration_hours: Optional[float] = None,
    depth: Optional[float] = None,
) -> TTVExtractionResult:
    """Convenience wrapper to extract TTVs directly from LightCurveData object."""
    return extract_ttv(
        time=lc.time,
        flux=lc.flux,
        flux_err=lc.flux_err,
        period=period,
        t0=t0,
        duration_hours=duration_hours,
        depth=depth,
    )
