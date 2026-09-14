"""Co-orbital Trojan world detector for triangular Lagrangian points L4 and L5.

Searches for secondary transit dips at +/- 60 degree (+/- 0.1667) orbital phase
offsets relative to the primary planetary transit.
"""

from __future__ import annotations

from dataclasses import dataclass
from typing import Optional, Tuple, Dict, Any, Union
import numpy as np

from frontier_astronomy.core.types import LightCurveData
from frontier_astronomy.core.math_utils import median_absolute_deviation
from frontier_astronomy.core.preprocessing import phase_fold


@dataclass(frozen=True)
class TrojanDetectionResult:
    """Detection results for co-orbital Trojan companion dips."""
    has_trojan: bool                    # True if significant Trojan candidate detected
    lagrange_point: str                 # "L4", "L5", "both", or "none"
    depth: float                        # Peak detected Trojan dip depth (fractional)
    snr: float                          # Peak detection signal-to-noise ratio
    phase_offset: float                 # Phase offset where dip occurred (+0.1667 or -0.1667)
    l4_depth: float                     # Measured dip at L4 (+60 deg)
    l4_snr: float                       # Detection SNR at L4
    l5_depth: float                     # Measured dip at L5 (-60 deg)
    l5_snr: float                       # Detection SNR at L5

    @property
    def has_trojan_candidate(self) -> bool:
        """Alias for compatibility with ExomoonPerturbationResult interface."""
        return self.has_trojan

    @property
    def trojan_depth(self) -> float:
        """Alias for peak detected Trojan depth."""
        return self.depth


def detect_trojan_companions(
    time: np.ndarray,
    flux: np.ndarray,
    flux_err: np.ndarray,
    period: float,
    t0: float,
    duration_hours: Optional[float] = None,
    snr_threshold: float = 3.0,
    min_depth: float = 0.0003,
    libration_window_phase: float = 0.03,
) -> TrojanDetectionResult:
    """Search for co-orbital Trojan companion transit dips at L4 and L5.

    Args:
        time: 1D array of timestamps (days).
        flux: 1D array of normalized flux values.
        flux_err: 1D array of uncertainties.
        period: Primary planet orbital period (days).
        t0: Primary transit epoch (days).
        duration_hours: Expected transit duration in hours (defaults to 4.0).
        snr_threshold: Minimum SNR for valid detection (default 3.0).
        min_depth: Minimum detectable fractional depth (default 300 ppm).
        libration_window_phase: Phase search half-width around +/- 1/6 (default 0.03).

    Returns:
        TrojanDetectionResult object with candidate detection flags.
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

    phases = phase_fold(t, period, t0)

    # Continuum baseline noise (away from primary transit and L4/L5)
    clean_baseline_mask = (
        (np.abs(phases) > dur_phase * 1.5)
        & (np.abs(phases - (1.0 / 6.0)) > 0.06)
        & (np.abs(phases - (-1.0 / 6.0)) > 0.06)
    )
    if np.sum(clean_baseline_mask) > 30:
        sigma_out = float(median_absolute_deviation(f[clean_baseline_mask] - 1.0))
        if sigma_out <= 0:
            sigma_out = float(np.std(f[clean_baseline_mask]))
    else:
        sigma_out = float(np.median(fe))
    sigma_out = max(sigma_out, 1e-6)

    def scan_lagrange_point(nominal_phase: float) -> Tuple[float, float, float]:
        """Scan phase window around nominal Lagrange point for transit dip."""
        window_mask = np.abs(phases - nominal_phase) <= libration_window_phase
        n_win = np.sum(window_mask)
        if n_win < 4:
            return 0.0, 0.0, nominal_phase

        ph_win = phases[window_mask]
        f_win = f[window_mask]

        best_snr = 0.0
        best_depth = 0.0
        best_phase = nominal_phase

        # Scan trial dip centers within libration window
        search_centers = np.linspace(
            nominal_phase - libration_window_phase * 0.75,
            nominal_phase + libration_window_phase * 0.75,
            21,
        )
        half_box = max(0.005, dur_phase / 2.0)

        for c in search_centers:
            in_dip = np.abs(ph_win - c) < half_box
            n_in = np.sum(in_dip)
            if n_in < 3:
                continue

            mean_flux = float(np.mean(f_win[in_dip]))
            depth_val = 1.0 - mean_flux
            if depth_val > 0.0:
                se_dip = sigma_out / np.sqrt(n_in)
                snr_val = depth_val / se_dip
                if snr_val > best_snr:
                    best_snr = snr_val
                    best_depth = depth_val
                    best_phase = float(c)

        return best_depth, best_snr, best_phase

    # L4 point: +60 degrees (+0.1667 phase)
    l4_depth, l4_snr, l4_ph = scan_lagrange_point(1.0 / 6.0)
    # L5 point: -60 degrees (-0.1667 phase)
    l5_depth, l5_snr, l5_ph = scan_lagrange_point(-1.0 / 6.0)

    l4_detected = (l4_snr >= snr_threshold) and (l4_depth >= min_depth)
    l5_detected = (l5_snr >= snr_threshold) and (l5_depth >= min_depth)

    if l4_detected and l5_detected:
        lagrange_pt = "both"
        peak_depth = max(l4_depth, l5_depth)
        peak_snr = max(l4_snr, l5_snr)
        peak_ph = l4_ph if l4_snr >= l5_snr else l5_ph
        has_trojan = True
    elif l4_detected:
        lagrange_pt = "L4"
        peak_depth = l4_depth
        peak_snr = l4_snr
        peak_ph = l4_ph
        has_trojan = True
    elif l5_detected:
        lagrange_pt = "L5"
        peak_depth = l5_depth
        peak_snr = l5_snr
        peak_ph = l5_ph
        has_trojan = True
    else:
        lagrange_pt = "none"
        peak_depth = 0.0
        peak_snr = max(l4_snr, l5_snr)
        peak_ph = l4_ph if l4_snr >= l5_snr else l5_ph
        has_trojan = False

    return TrojanDetectionResult(
        has_trojan=has_trojan,
        lagrange_point=lagrange_pt,
        depth=float(peak_depth),
        snr=float(peak_snr),
        phase_offset=float(peak_ph),
        l4_depth=float(l4_depth),
        l4_snr=float(l4_snr),
        l5_depth=float(l5_depth),
        l5_snr=float(l5_snr),
    )


def detect_trojan_companions_from_light_curve(
    lc: LightCurveData,
    period: float,
    t0: float,
    duration_hours: Optional[float] = None,
    snr_threshold: float = 3.0,
    min_depth: float = 0.0003,
) -> TrojanDetectionResult:
    """Convenience wrapper to detect Trojans from LightCurveData object."""
    return detect_trojan_companions(
        time=lc.time,
        flux=lc.flux,
        flux_err=lc.flux_err,
        period=period,
        t0=t0,
        duration_hours=duration_hours,
        snr_threshold=snr_threshold,
        min_depth=min_depth,
    )
