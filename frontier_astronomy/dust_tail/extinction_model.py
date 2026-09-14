"""Rappaport/Brogi cometary dust tail forward model.

Models the asymmetric extinction profile of catastrophically disintegrating rocky exoplanets
(e.g., KIC 12557548 b, KOI-2700 b, K2-22 b):
1. Steep sigmoidal ingress occultation by the dense comet-like dust coma.
2. Extended exponentially decaying egress tail formed by radiation-pressure-driven dust dispersion.
3. Pronounced morphological transit asymmetry: alpha = (t_egress - t_ingress) / t_total > 0.3.
"""

from __future__ import annotations

from typing import Optional, Tuple, Union
import numpy as np
from scipy import special


def cometary_extinction_profile(
    phase: np.ndarray | float,
    depth: float = 0.010,
    sigma_ing: float = 0.004,
    lambda_tail: float = 0.050,
    alpha: float = 1.0,
    phi_offset: float = 0.0,
    f_scat: float = 0.0,
    phi_scat: float = -0.02,
    sigma_scat: float = 0.008,
) -> np.ndarray:
    """Compute normalized flux across orbital phase for a cometary dust tail.

    Formulation (Rappaport et al. 2012, 2014; Brogi et al. 2012):
        F(phi) = 1.0 - depth * S_ing(phi) * T_tail(phi) + F_scat(phi)

    where:
        S_ing(phi) = 1 / (1 + exp(-(phi + phi_offset) / sigma_ing))   (steep sigmoid ingress)
        T_tail(phi) = exp(-(max(0, phi + phi_offset) / lambda_tail)^alpha) (exponential egress tail)
        F_scat(phi) = f_scat * exp(-0.5 * ((phi - phi_scat) / sigma_scat)^2) (Mie forward scattering)

    Args:
        phase: 1D array of orbital phases (nominal range [-0.5, 0.5)).
        depth: Peak transit extinction depth (fractional, e.g. 0.01 = 1.0%).
        sigma_ing: Ingress duration scale in phase units (sharp leading edge).
        lambda_tail: Egress exponential decay scale length in phase units.
        alpha: Tail decay curvature power index (1.0 = exponential, >1.0 = sharp cutoff).
        phi_offset: Phase offset aligning transit minimum with desired phase.
        f_scat: Forward scattering peak amplitude prior to ingress.
        phi_scat: Phase location of forward scattering peak (typically -0.02).
        sigma_scat: Width of forward scattering peak in phase units.

    Returns:
        1D array of normalized flux values.
    """
    ph = np.asarray(phase, dtype=np.float64)
    is_scalar = ph.ndim == 0
    if is_scalar:
        ph = np.atleast_1d(ph)

    # Shifted phase for transit center alignment
    d_phi = ph + phi_offset

    # Ingress sigmoid transition: expit(x) = 1 / (1 + exp(-x)), stable against overflow
    safe_sigma_ing = max(float(sigma_ing), 1e-9)
    s_ing = special.expit(d_phi / safe_sigma_ing)

    # Egress exponential tail decay
    safe_lambda_tail = max(float(lambda_tail), 1e-9)
    safe_alpha = max(float(alpha), 1e-4)
    tail_arg = np.maximum(0.0, d_phi) / safe_lambda_tail
    t_tail = np.exp(-(tail_arg ** safe_alpha))

    # Total dust extinction
    extinction = max(0.0, float(depth)) * s_ing * t_tail

    # Mie forward-scattering brightening
    if f_scat > 0.0 and sigma_scat > 0.0:
        scat_arg = (ph - phi_scat) / sigma_scat
        f_scat_flux = float(f_scat) * np.exp(-0.5 * (scat_arg ** 2))
    else:
        f_scat_flux = 0.0

    flux = 1.0 - extinction + f_scat_flux

    # Zero depth and zero scattering guarantee exact 1.0
    if depth <= 0.0 and f_scat <= 0.0:
        flux = np.ones_like(flux)

    if is_scalar:
        return float(flux[0])
    return flux


def compute_asymmetry_parameter(
    phase: np.ndarray,
    flux: np.ndarray,
    baseline: float = 1.0,
    phase_window: Tuple[float, float] = (-0.08, 0.22),
    threshold_fraction: float = 0.10,
) -> float:
    """Calculate the morphological transit asymmetry parameter alpha.

    alpha = (t_egress - t_ingress) / (t_egress + t_ingress)

    where:
        t_ingress = abs(t_min - t_start)
        t_egress  = abs(t_end - t_min)
        t_total   = t_ingress + t_egress

    For symmetric exoplanetary transits, alpha ~ 0.0.
    For trailing cometary dust tails, alpha > 0.30 (typically 0.35 - 0.70).

    Args:
        phase: 1D array of orbital phases.
        flux: 1D array of normalized flux values.
        baseline: Out-of-transit continuum baseline (nominal = 1.0).
        phase_window: (min_phase, max_phase) bounding the transit search.
        threshold_fraction: Fractional depth defining transit ingress/egress boundaries.

    Returns:
        Asymmetry parameter alpha in [-1.0, 1.0].
    """
    ph = np.asarray(phase, dtype=np.float64)
    fl = np.asarray(flux, dtype=np.float64)

    # Restrict to transit phase window
    if isinstance(phase_window, (int, float)):
        phase_window = (-float(abs(phase_window)), float(abs(phase_window)))
    mask = (ph >= phase_window[0]) & (ph <= phase_window[1]) & np.isfinite(ph) & np.isfinite(fl)
    if np.sum(mask) < 4:
        return 0.0

    ph_sub = ph[mask]
    fl_sub = fl[mask]

    min_idx = int(np.argmin(fl_sub))
    t_min = float(ph_sub[min_idx])
    max_depth = float(baseline - fl_sub[min_idx])

    if max_depth <= 1e-5:
        return 0.0

    thresh = baseline - threshold_fraction * max_depth

    # Find ingress start (last point before t_min above threshold)
    before_min = ph_sub <= t_min
    in_transit_before = before_min & (fl_sub <= thresh)
    if np.any(in_transit_before):
        t_start = float(np.min(ph_sub[in_transit_before]))
    else:
        t_start = float(ph_sub[0])

    # Find egress end (last point after t_min above threshold)
    after_min = ph_sub >= t_min
    in_transit_after = after_min & (fl_sub <= thresh)
    if np.any(in_transit_after):
        t_end = float(np.max(ph_sub[in_transit_after]))
    else:
        t_end = float(ph_sub[-1])

    t_ing_len = abs(t_min - t_start)
    t_eg_len = abs(t_end - t_min)
    t_total = t_ing_len + t_eg_len

    if t_total <= 1e-9:
        return 0.0

    alpha_val = (t_eg_len - t_ing_len) / t_total
    return float(np.clip(alpha_val, -1.0, 1.0))
