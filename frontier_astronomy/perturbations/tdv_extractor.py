"""Transit Duration Variation (TDV) extraction and orthogonal phase invariant test.

Implements:
- Transit duration variation extraction per epoch via template stretching.
- Pathognomonic pi/2 (90-degree) orthogonal TTV-TDV phase invariant test
  (the definitive smoking gun distinguishing exomoons from mean-motion resonance planets).
- Automatic identification and rejection of Mean Motion Resonance (MMR) false positives
  (which produce in-phase 0 deg or anti-phase 180 deg variations).
"""

from __future__ import annotations

from dataclasses import dataclass
from typing import Optional, Tuple, Dict, Any, Union
import numpy as np

from frontier_astronomy.core.types import LightCurveData
from frontier_astronomy.core.math_utils import symmetric_trapezoid_transit
from frontier_astronomy.core.preprocessing import epoch_split


@dataclass(frozen=True)
class TDVExtractionResult:
    """Container for per-epoch transit duration variations."""
    epochs: np.ndarray                  # 1D int32 array of observed transit epochs
    durations_hours: np.ndarray         # 1D float64 array of measured durations (hours)
    tdv_minutes: np.ndarray             # 1D float64 array of duration variations from mean (minutes)
    tdv_errors_minutes: np.ndarray      # 1D float64 array of 1-sigma uncertainties (minutes)
    mean_duration_hours: float          # Baseline unperturbed transit duration (hours)

    def __post_init__(self) -> None:
        object.__setattr__(self, "epochs", np.asarray(self.epochs, dtype=np.int32))
        object.__setattr__(self, "durations_hours", np.asarray(self.durations_hours, dtype=np.float64))
        object.__setattr__(self, "tdv_minutes", np.asarray(self.tdv_minutes, dtype=np.float64))
        object.__setattr__(self, "tdv_errors_minutes", np.asarray(self.tdv_errors_minutes, dtype=np.float64))


def test_orthogonal_phase_invariant(
    ttv_amplitudes: np.ndarray,
    tdv_amplitudes: np.ndarray,
    tolerance_deg: float = 15.0,
) -> Dict[str, Any]:
    """Test the pathognomonic orthogonal pi/2 (90 degree) phase invariant between TTV and TDV.

    Astrophysical Principle:
    In exomoon systems, planet orbital reflex motion causes:
        TTV(n) ~ sin(Psi_n)
        TDV-V(n) ~ -cos(Psi_n) = sin(Psi_n - pi/2)
    producing an exact 90-degree orthogonal phase shift.
    In contrast, planet-planet Mean Motion Resonances (MMR) accelerate the planet along
    its orbital path, producing strictly in-phase (0 deg) or anti-phase (180 deg) perturbations.

    Args:
        ttv_amplitudes: 1D array of TTV timing variations (minutes).
        tdv_amplitudes: 1D array of TDV duration variations (minutes).
        tolerance_deg: Permissible tolerance around 90 deg (default 15.0 deg).

    Returns:
        Dictionary with:
            - phase_diff_deg: Estimated phase difference in degrees [0, 180].
            - is_orthogonal: True if within tolerance of 90 degrees.
            - is_mmr_false_positive: True if within tolerance of 0 or 180 degrees.
            - is_exomoon_candidate: True if orthogonal and not MMR.
            - dot_product_normalized: Normalized zero-lag correlation metric.
    """
    ttv = np.asarray(ttv_amplitudes, dtype=np.float64)
    tdv = np.asarray(tdv_amplitudes, dtype=np.float64)

    if len(ttv) != len(tdv) or len(ttv) < 2:
        return {
            "phase_diff_deg": 0.0,
            "is_orthogonal": False,
            "is_mmr_false_positive": False,
            "is_exomoon_candidate": False,
            "dot_product_normalized": 0.0,
        }

    # Center both series
    u = ttv - np.mean(ttv)
    v = tdv - np.mean(tdv)

    std_u = float(np.std(u))
    std_v = float(np.std(v))

    if std_u < 1e-9 or std_v < 1e-9:
        return {
            "phase_diff_deg": 0.0,
            "is_orthogonal": False,
            "is_mmr_false_positive": False,
            "is_exomoon_candidate": False,
            "dot_product_normalized": 0.0,
        }

    u_norm = u / std_u
    v_norm = v / std_v

    # Normalized zero-lag inner product:
    # dot_norm = sum(u_norm * v_norm) / N
    # For sin and cos: dot_norm ~ 0.0 -> arccos(0.0) = 90 deg
    # For in-phase: dot_norm ~ 1.0 -> arccos(1.0) = 0 deg
    # For anti-phase: dot_norm ~ -1.0 -> arccos(-1.0) = 180 deg
    dot_norm = float(np.mean(u_norm * v_norm))
    clipped_dot = float(np.clip(dot_norm, -1.0, 1.0))
    phase_from_dot = float(np.arccos(clipped_dot) * (180.0 / np.pi))

    # Also compute via harmonic decomposition if sufficient epochs exist
    n_pts = len(u)
    phase_diff_deg = phase_from_dot

    if n_pts >= 4:
        # Search over harmonic trial periods to isolate dominant orbital modulation
        best_r2 = -1.0
        best_phase_diff = phase_from_dot

        t_idx = np.arange(n_pts, dtype=np.float64)
        for trial_period in np.linspace(2.0, max(2.5, n_pts * 1.5), 30):
            omega = 2.0 * np.pi / trial_period
            c_basis = np.cos(omega * t_idx)
            s_basis = np.sin(omega * t_idx)
            X = np.column_stack([c_basis, s_basis])

            # Least-squares fit for u
            coeff_u, res_u, _, _ = np.linalg.lstsq(X, u_norm, rcond=None)
            phi_u = np.arctan2(coeff_u[1], coeff_u[0])

            # Least-squares fit for v
            coeff_v, res_v, _, _ = np.linalg.lstsq(X, v_norm, rcond=None)
            phi_v = np.arctan2(coeff_v[1], coeff_v[0])

            # Residual variance
            pred_u = X @ coeff_u
            pred_v = X @ coeff_v
            r2_combined = 1.0 - (np.mean((u_norm - pred_u) ** 2) + np.mean((v_norm - pred_v) ** 2)) / 2.0

            if r2_combined > best_r2:
                best_r2 = r2_combined
                dphi = abs(phi_u - phi_v) % (2.0 * np.pi)
                if dphi > np.pi:
                    dphi = 2.0 * np.pi - dphi
                best_phase_diff = float(dphi * (180.0 / np.pi))

        if best_r2 > 0.75 and abs(best_phase_diff - 90.0) <= tolerance_deg:
            phase_diff_deg = best_phase_diff
        elif abs(phase_from_dot - 90.0) <= tolerance_deg:
            phase_diff_deg = phase_from_dot
        elif best_r2 > 0.5:
            phase_diff_deg = best_phase_diff
        else:
            phase_diff_deg = phase_from_dot

    is_orthogonal = bool(abs(phase_diff_deg - 90.0) <= tolerance_deg)
    is_mmr_false_positive = bool(
        (abs(phase_diff_deg - 0.0) < tolerance_deg)
        or (abs(phase_diff_deg - 180.0) < tolerance_deg)
    )
    is_exomoon_candidate = bool(is_orthogonal and not is_mmr_false_positive)

    return {
        "phase_diff_deg": float(phase_diff_deg),
        "is_orthogonal": is_orthogonal,
        "is_mmr_false_positive": is_mmr_false_positive,
        "is_exomoon_candidate": is_exomoon_candidate,
        "dot_product_normalized": float(dot_norm),
    }


def extract_tdv(
    time: np.ndarray,
    flux: np.ndarray,
    flux_err: np.ndarray,
    period: float,
    t0: float,
    duration_hours: Optional[float] = None,
    depth: Optional[float] = None,
    transit_times: Optional[np.ndarray] = None,
    observed_epochs: Optional[np.ndarray] = None,
) -> TDVExtractionResult:
    """Extract Transit Duration Variations (TDVs) across observed transit epochs.

    Args:
        time: 1D array of cadence timestamps (days).
        flux: 1D array of normalized flux values.
        flux_err: 1D array of uncertainties.
        period: Orbital period (days).
        t0: Mid-transit epoch (days).
        duration_hours: Nominal transit duration in hours (defaults to 4.0).
        depth: Nominal transit depth.
        transit_times: Optional pre-fitted mid-transit times per epoch.
        observed_epochs: Optional array of epoch numbers corresponding to transit_times.

    Returns:
        TDVExtractionResult with per-epoch durations and variations in minutes.
    """
    t = np.asarray(time, dtype=np.float64)
    f = np.asarray(flux, dtype=np.float64)
    fe = np.asarray(flux_err, dtype=np.float64)

    if period <= 0:
        raise ValueError(f"Orbital period must be positive, got {period}")

    if duration_hours is None or duration_hours <= 0:
        duration_hours = 4.0
    dur_days = duration_hours / 24.0

    if depth is None or depth <= 0:
        phase = ((t - t0) / period + 0.5) % 1.0 - 0.5
        in_transit = np.abs(phase) < ((dur_days / 2.0) / period)
        if np.any(in_transit):
            depth = float(max(0.001, 1.0 - np.percentile(f[in_transit], 10)))
        else:
            depth = 0.01

    if observed_epochs is not None and transit_times is not None:
        epochs_to_eval = np.asarray(observed_epochs, dtype=np.int32)
        midpoints = np.asarray(transit_times, dtype=np.float64)
    else:
        epochs_all = epoch_split(t, period, t0)
        epochs_to_eval = np.unique(epochs_all)
        midpoints = t0 + epochs_to_eval * period

    fit_epochs = []
    fit_durations = []
    fit_errors = []

    # Grid of duration stretching factors
    stretch_grid = np.linspace(0.6, 1.4, 41)

    for i, ep in enumerate(epochs_to_eval):
        t_center = midpoints[i]
        mask = np.abs(t - t_center) < (dur_days * 1.5)
        if np.sum(mask) < 3:
            continue

        t_win = t[mask]
        f_win = f[mask]
        fe_win = fe[mask]
        weights = 1.0 / np.maximum(fe_win, 1e-7) ** 2

        chi2_vals = np.zeros(len(stretch_grid), dtype=np.float64)

        for j, s in enumerate(stretch_grid):
            curr_dur_days = dur_days * s
            dur_phase = curr_dur_days / period
            phase_eval = ((t_win - t_center) / period + 0.5) % 1.0 - 0.5
            model = symmetric_trapezoid_transit(
                phase=phase_eval,
                period=period,
                depth=depth,
                duration_phase=dur_phase,
                ingress_ratio=0.15,
            )
            chi2_vals[j] = np.sum(weights * (f_win - model) ** 2)

        min_idx = int(np.argmin(chi2_vals))
        best_stretch = stretch_grid[min_idx]
        fitted_dur_hours = duration_hours * best_stretch
        # Approximate uncertainty
        err_hours = duration_hours * 0.05

        fit_epochs.append(ep)
        fit_durations.append(fitted_dur_hours)
        fit_errors.append(err_hours)

    if len(fit_epochs) == 0:
        return TDVExtractionResult(
            epochs=np.array([], dtype=np.int32),
            durations_hours=np.array([], dtype=np.float64),
            tdv_minutes=np.array([], dtype=np.float64),
            tdv_errors_minutes=np.array([], dtype=np.float64),
            mean_duration_hours=duration_hours,
        )

    ep_arr = np.array(fit_epochs, dtype=np.int32)
    dur_arr = np.array(fit_durations, dtype=np.float64)
    err_arr = np.array(fit_errors, dtype=np.float64)

    mean_dur = float(np.mean(dur_arr))
    tdv_hours = dur_arr - mean_dur
    tdv_minutes = tdv_hours * 60.0
    tdv_errors_minutes = err_arr * 60.0

    return TDVExtractionResult(
        epochs=ep_arr,
        durations_hours=dur_arr,
        tdv_minutes=tdv_minutes,
        tdv_errors_minutes=tdv_errors_minutes,
        mean_duration_hours=mean_dur,
    )


def extract_tdv_from_light_curve(
    lc: LightCurveData,
    period: float,
    t0: float,
    duration_hours: Optional[float] = None,
    depth: Optional[float] = None,
    transit_times: Optional[np.ndarray] = None,
    observed_epochs: Optional[np.ndarray] = None,
) -> TDVExtractionResult:
    """Convenience wrapper to extract TDVs directly from LightCurveData object."""
    return extract_tdv(
        time=lc.time,
        flux=lc.flux,
        flux_err=lc.flux_err,
        period=period,
        t0=t0,
        duration_hours=duration_hours,
        depth=depth,
        transit_times=transit_times,
        observed_epochs=observed_epochs,
    )
