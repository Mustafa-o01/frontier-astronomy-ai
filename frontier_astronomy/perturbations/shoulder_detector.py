"""Secondary transit shoulder anomaly detector during ingress and egress.

Isolates exomoon secondary transit dips and shoulder anomalies occurring
in the wings or flanks of primary planetary transits after decoupling the
symmetric planetary transit baseline.
"""

from __future__ import annotations

from dataclasses import dataclass
from typing import Optional, Tuple, Dict, Any, Union
import numpy as np

from frontier_astronomy.core.types import LightCurveData
from frontier_astronomy.core.math_utils import (
    symmetric_trapezoid_transit,
    median_absolute_deviation,
)
from frontier_astronomy.core.preprocessing import phase_fold


@dataclass(frozen=True)
class ShoulderDetectionResult:
    """Detection results for secondary transit ingress/egress shoulder anomalies."""
    has_shoulder: bool                  # True if shoulder detected at SNR >= 3.0
    snr: float                          # Signal-to-noise ratio of anomaly
    depth: float                        # Estimated secondary dip depth (fractional)
    phase_offset: float                 # Phase offset of shoulder relative to transit center
    shoulder_type: str                  # "ingress", "egress", "both", or "none"
    ingress_snr: float                  # SNR in ingress window
    egress_snr: float                   # SNR in egress window


def detect_transit_shoulders(
    time: np.ndarray,
    flux: np.ndarray,
    flux_err: np.ndarray,
    period: float,
    t0: float,
    duration_hours: Optional[float] = None,
    depth: Optional[float] = None,
    snr_threshold: float = 3.0,
) -> ShoulderDetectionResult:
    """Detect secondary transit shoulder anomalies during ingress and egress.

    Args:
        time: 1D cadence timestamps (days).
        flux: 1D normalized flux values.
        flux_err: 1D uncertainties.
        period: Planetary orbital period (days).
        t0: Transit epoch reference (days).
        duration_hours: Planetary transit duration in hours (defaults to 4.0).
        depth: Planetary transit depth (auto-estimated if None).
        snr_threshold: Minimum detection threshold (default 3.0).

    Returns:
        ShoulderDetectionResult with detection status and metrics.
    """
    t = np.asarray(time, dtype=np.float64)
    f = np.asarray(flux, dtype=np.float64)
    fe = np.asarray(flux_err, dtype=np.float64)

    if period <= 0:
        raise ValueError(f"Orbital period must be positive, got {period}")

    if duration_hours is None or duration_hours <= 0:
        duration_hours = 4.0
    dur_days = duration_hours / 24.0
    dur_phase = dur_days / period
    half_dur_phase = dur_phase / 2.0

    # Fold cadences into phase [-0.5, 0.5)
    phases = phase_fold(t, period, t0)
    sort_idx = np.argsort(phases)
    ph_sorted = phases[sort_idx]
    f_sorted = f[sort_idx]
    fe_sorted = fe[sort_idx]

    # Auto-estimate planetary depth if not provided
    if depth is None or depth <= 0:
        core_transit = np.abs(ph_sorted) < (half_dur_phase * 0.7)
        if np.sum(core_transit) >= 3:
            depth = float(max(0.001, 1.0 - np.percentile(f_sorted[core_transit], 15)))
        else:
            depth = 0.01

    # Subtract symmetric primary planet model
    model_primary = symmetric_trapezoid_transit(
        phase=ph_sorted,
        period=period,
        depth=depth,
        duration_phase=dur_phase,
        ingress_ratio=0.15,
    )
    residuals = f_sorted - model_primary

    # Continuum baseline noise out of transit
    out_of_transit = np.abs(ph_sorted) > (dur_phase * 1.5)
    if np.sum(out_of_transit) > 20:
        sigma_out = float(median_absolute_deviation(residuals[out_of_transit]))
        if sigma_out <= 0:
            sigma_out = float(np.std(residuals[out_of_transit]))
    else:
        sigma_out = float(np.median(fe_sorted))
    sigma_out = max(sigma_out, 1e-6)

    # Search windows for satellite transit shoulder
    # Ingress window: leading flank
    ing_mask = (ph_sorted >= -dur_phase * 1.3) & (ph_sorted <= -half_dur_phase * 0.5)
    # Egress window: trailing flank
    egr_mask = (ph_sorted >= half_dur_phase * 0.5) & (ph_sorted <= dur_phase * 1.3)

    # Filter window scan for secondary dips
    sub_dur_phase = dur_phase * 0.35

    def scan_window(mask: np.ndarray) -> Tuple[float, float, float]:
        if np.sum(mask) < 4:
            return 0.0, 0.0, 0.0

        ph_win = ph_sorted[mask]
        res_win = residuals[mask]

        best_snr = 0.0
        best_depth = 0.0
        best_phase = 0.0

        for center in np.linspace(np.min(ph_win), np.max(ph_win), 25):
            dip_mask = np.abs(ph_win - center) < (sub_dur_phase / 2.0)
            n_dip = np.sum(dip_mask)
            if n_dip < 3:
                continue

            # A secondary transit manifests as a negative residual (extra absorption)
            mean_dip = -float(np.mean(res_win[dip_mask]))
            if mean_dip > 0.0:
                se_dip = sigma_out / np.sqrt(n_dip)
                snr_val = mean_dip / se_dip
                if snr_val > best_snr:
                    best_snr = snr_val
                    best_depth = mean_dip
                    best_phase = float(center)

        return best_snr, best_depth, best_phase

    ing_snr, ing_depth, ing_ph = scan_window(ing_mask)
    egr_snr, egr_depth, egr_ph = scan_window(egr_mask)

    max_snr = max(ing_snr, egr_snr)
    if ing_snr >= snr_threshold and egr_snr >= snr_threshold:
        stype = "both"
        best_d = max(ing_depth, egr_depth)
        best_ph = ing_ph if ing_snr >= egr_snr else egr_ph
    elif ing_snr >= snr_threshold:
        stype = "ingress"
        best_d = ing_depth
        best_ph = ing_ph
    elif egr_snr >= snr_threshold:
        stype = "egress"
        best_d = egr_depth
        best_ph = egr_ph
    else:
        stype = "none"
        best_d = max(ing_depth, egr_depth)
        best_ph = ing_ph if ing_snr >= egr_snr else egr_ph

    has_shoulder = bool(max_snr >= snr_threshold and best_d > 0.0)

    return ShoulderDetectionResult(
        has_shoulder=has_shoulder,
        snr=float(max_snr),
        depth=float(best_d),
        phase_offset=float(best_ph),
        shoulder_type=stype,
        ingress_snr=float(ing_snr),
        egress_snr=float(egr_snr),
    )


def detect_transit_shoulders_from_light_curve(
    lc: LightCurveData,
    period: float,
    t0: float,
    duration_hours: Optional[float] = None,
    depth: Optional[float] = None,
    snr_threshold: float = 3.0,
) -> ShoulderDetectionResult:
    """Convenience wrapper for detecting shoulders from LightCurveData object."""
    return detect_transit_shoulders(
        time=lc.time,
        flux=lc.flux,
        flux_err=lc.flux_err,
        period=period,
        t0=t0,
        duration_hours=duration_hours,
        depth=depth,
        snr_threshold=snr_threshold,
    )
