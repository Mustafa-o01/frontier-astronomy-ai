"""Multi-body perturbation sensitivity validation suite.

Computes detection sensitivity limits across satellite mass ratios (Ms/Mp)
and evaluates Bayesian posterior probability P(moon|data) based on:
- TTV signal-to-noise ratio
- Orthogonal pi/2 phase invariant consistency
- Secondary ingress/egress shoulder significance
- Rejection of Mean Motion Resonance (MMR) false positives
"""

from __future__ import annotations

from typing import Optional, Tuple, Dict, Any, List, Union
import numpy as np

from frontier_astronomy.core.constants import (
    G,
    M_SUN,
    M_JUPITER,
    M_EARTH,
    M_MOON,
    AU,
    DAY_SECONDS,
    MINUTE_SECONDS,
)
from frontier_astronomy.perturbations.photodynamics import (
    barycentric_semi_major_axis,
    barycentric_orbital_velocity,
    satellite_semi_major_axis,
    barycentric_ttv_amplitude,
)


def compute_minimum_detectable_moon_mass(
    m_star: float = M_SUN,
    m_planet: float = M_JUPITER,
    p_planet_days: float = 10.0,
    p_moon_days: Optional[float] = None,
    a_sp: Optional[float] = None,
    v_b: Optional[float] = None,
    sigma_ttv_seconds: float = 60.0,
    snr_threshold: float = 3.0,
) -> float:
    """Calculate minimum detectable satellite mass given photometric timing precision.

    Formulation (Sartoretti & Schneider 1999; Kipping 2009a):
        M_s,min = snr_threshold * sigma_ttv * (v_B * M_p / a_sp)

    Args:
        m_star: Stellar mass (kg).
        m_planet: Planet mass (kg).
        p_planet_days: Planet orbital period (days).
        p_moon_days: Satellite orbital period (days). Used if a_sp is None.
        a_sp: Satellite semi-major axis (meters). If None, calculated from p_moon_days.
        v_b: Barycentric orbital velocity (m/s). If None, calculated from Kepler's law.
        sigma_ttv_seconds: Photometric timing precision (seconds).
        snr_threshold: Minimum detection threshold (default 3.0).

    Returns:
        Minimum detectable satellite mass M_s,min in kg.
    """
    if m_star <= 0 or m_planet <= 0 or p_planet_days <= 0 or sigma_ttv_seconds <= 0:
        raise ValueError("Physical parameters must be strictly positive.")

    p_b_sec = p_planet_days * DAY_SECONDS

    if v_b is None or v_b <= 0:
        a_b = barycentric_semi_major_axis(m_star, p_b_sec)
        v_b = barycentric_orbital_velocity(m_star, a_b)

    if a_sp is None or a_sp <= 0:
        if p_moon_days is None or p_moon_days <= 0:
            p_moon_days = max(0.5, p_planet_days * 0.1)
        p_s_sec = p_moon_days * DAY_SECONDS
        # Approximate satellite separation assuming M_s << M_p
        a_sp = (G * m_planet * (p_s_sec ** 2) / (4.0 * (np.pi ** 2))) ** (1.0 / 3.0)

    # Minimum detectable moon mass: M_s,min = snr * sigma_ttv * v_B * M_p / a_sp
    m_s_min = snr_threshold * sigma_ttv_seconds * v_b * m_planet / a_sp
    return float(m_s_min)


def compute_ttv_snr(
    ttv_amplitudes: np.ndarray,
    ttv_errors: Optional[np.ndarray] = None,
) -> float:
    """Calculate signal-to-noise ratio of Transit Timing Variation oscillation.

    Args:
        ttv_amplitudes: 1D array of TTV measurements (minutes).
        ttv_errors: Optional 1D array of 1-sigma timing uncertainties (minutes).

    Returns:
        SNR of the TTV series.
    """
    ttv = np.asarray(ttv_amplitudes, dtype=np.float64)
    if len(ttv) < 2:
        return 0.0

    std_val = float(np.std(ttv))
    if std_val <= 1e-12:
        return 0.0

    if ttv_errors is not None and len(ttv_errors) == len(ttv):
        err = np.asarray(ttv_errors, dtype=np.float64)
        mean_err = float(np.median(err)) if np.median(err) > 0 else float(np.mean(err))
    else:
        # Default baseline noise estimation from differences
        diffs = np.diff(ttv)
        mean_err = float(np.std(diffs) / np.sqrt(2.0)) if len(diffs) > 0 else 1.0

    mean_err = max(mean_err, 1e-6)
    # Peak amplitude ~ sqrt(2) * std
    return float((std_val * np.sqrt(2.0)) / mean_err)


def compute_sensitivity_grid(
    m_star: float = M_SUN,
    m_planet: float = M_JUPITER,
    p_planet_days: float = 10.0,
    p_moon_days: float = 1.5,
    sigma_phot_min: float = 0.30,
    mass_ratios: Optional[List[float]] = None,
    n_epochs: int = 16,
) -> Dict[str, Any]:
    """Evaluate exomoon detection sensitivity across a grid of satellite mass ratios.

    Args:
        m_star: Stellar mass in kg.
        m_planet: Planetary mass in kg.
        p_planet_days: Planet orbital period in days.
        p_moon_days: Moon orbital period in days.
        sigma_phot_min: Photometric timing precision in minutes.
        mass_ratios: Optional list of satellite-to-planet mass ratios q = M_s / M_p.
        n_epochs: Number of observed transit epochs (SNR scales as sqrt(n_epochs/16)).

    Returns:
        Dictionary containing mass ratios, TTV amplitudes, SNRs, and detection flags.
    """
    if mass_ratios is None:
        mass_ratios = [0.001, 0.003, 0.005, 0.01, 0.02, 0.03, 0.05, 0.10]

    p_b_sec = p_planet_days * DAY_SECONDS
    a_b = barycentric_semi_major_axis(m_star, p_b_sec)
    v_b = barycentric_orbital_velocity(m_star, a_b)

    epoch_scale = np.sqrt(max(1, n_epochs) / 16.0)

    ttv_amps = []
    snrs = []
    detected = []

    for q in mass_ratios:
        m_s = q * m_planet
        p_s_sec = p_moon_days * DAY_SECONDS
        a_sp = (G * (m_planet + m_s) * (p_s_sec ** 2) / (4.0 * (np.pi ** 2))) ** (1.0 / 3.0)
        a_p = a_sp * (m_s / (m_planet + m_s))
        a_ttv_min = (a_p / v_b) / MINUTE_SECONDS

        snr = (a_ttv_min / sigma_phot_min) * epoch_scale
        ttv_amps.append(float(a_ttv_min))
        snrs.append(float(snr))
        detected.append(bool(snr >= 3.0))

    # Identify mass ratio where SNR reaches 3.0
    det_limit = None
    for q, is_det in zip(mass_ratios, detected):
        if is_det:
            det_limit = q
            break

    return {
        "mass_ratios": np.array(mass_ratios, dtype=np.float64),
        "ttv_amplitudes_min": np.array(ttv_amps, dtype=np.float64),
        "snrs": np.array(snrs, dtype=np.float64),
        "detected": np.array(detected, dtype=bool),
        "detection_limit_mass_ratio": det_limit,
    }


def compute_exomoon_posterior(
    ttv_snr: float,
    phase_diff_deg: float,
    shoulder_snr: float = 0.0,
    prior_prob: float = 0.5,
) -> float:
    """Calculate Bayesian posterior probability P(moon|data) for an exomoon candidate.

    Combines:
    1. TTV SNR evidence: Strong statistical oscillation favoring genuine multi-body perturbation.
    2. Phase invariant alignment: Gaussian likelihood centered at 90 deg (orthogonal),
       with severe penalties for MMR resonances at 0 deg and 180 deg.
    3. Secondary transit shoulder: Auxiliary photometric evidence of satellite occultation.

    Args:
        ttv_snr: Signal-to-noise ratio of TTV oscillation.
        phase_diff_deg: Phase difference between TTV and TDV in degrees [0, 180].
        shoulder_snr: Significance of ingress/egress shoulder anomaly.
        prior_prob: Prior probability of satellite existence (default 0.5).

    Returns:
        Posterior probability in [0.0, 1.0].
    """
    if ttv_snr <= 0.0:
        return 0.01

    # 1. TTV evidence term
    ln_b_ttv = 0.8 * (ttv_snr - 3.0)

    # 2. Phase invariant alignment term
    d_phase = abs(phase_diff_deg - 90.0)
    # Gaussian likelihood around 90 degrees with 15 deg width
    ln_b_phase = - (d_phase ** 2) / (2.0 * (15.0 ** 2))

    # MMR penalty: if in-phase (0 deg) or anti-phase (180 deg), strongly penalize exomoon hypothesis
    is_mmr = (abs(phase_diff_deg - 0.0) < 15.0) or (abs(phase_diff_deg - 180.0) < 15.0)
    if is_mmr:
        ln_b_phase -= 5.0

    # 3. Shoulder anomaly evidence
    ln_b_shoulder = 0.5 * max(0.0, shoulder_snr - 2.0)

    # Combined log Bayes factor
    log_bayes_factor = ln_b_ttv + ln_b_phase + ln_b_shoulder

    # Prior odds
    prior_odds = prior_prob / (1.0 - prior_prob) if prior_prob < 1.0 else 1.0
    posterior_odds = prior_odds * np.exp(np.clip(log_bayes_factor, -30.0, 30.0))

    p_moon = posterior_odds / (1.0 + posterior_odds)
    return float(np.clip(p_moon, 0.001, 0.999))
