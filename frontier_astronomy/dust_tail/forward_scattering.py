"""Henyey-Greenstein and Mie forward-scattering pre-ingress brightening model.

Dust grains ejected from catastrophically disintegrating planets have characteristic sizes
a_grain ~ 0.1 - 1.0 um, placing them in the Mie scattering regime for optical photons (Kepler/TESS).
Because scattering is strongly forward-peaked (g ~ 0.7 - 0.85), starlight is scattered into the
observer's line of sight as the dust cloud approaches the stellar limb, producing a distinct
pre-ingress flux brightening (F > 1.0) immediately prior to primary transit.
"""

from __future__ import annotations

from typing import Tuple, Union
import numpy as np


def forward_scattering_flux(
    phase: np.ndarray | float,
    f_scat: float = 0.0012,
    phi_scat: float = -0.020,
    sigma_scat: float = 0.008,
) -> np.ndarray:
    """Compute pre-ingress forward-scattering flux brightening across orbital phase.

    Formulation:
        F_scat(phi) = f_scat * exp(-0.5 * ((phi - phi_scat) / sigma_scat)^2)

    Args:
        phase: 1D array of orbital phases or single scalar phase.
        f_scat: Forward scattering peak amplitude (e.g. 0.001 = 1000 ppm).
        phi_scat: Phase of peak scattering excess (typically -0.015 to -0.035).
        sigma_scat: Angular width of the forward scattering peak in phase units.

    Returns:
        Array of forward-scattered flux excess values (non-negative).
    """
    ph = np.asarray(phase, dtype=np.float64)
    is_scalar = ph.ndim == 0
    if is_scalar:
        ph = np.atleast_1d(ph)

    if f_scat <= 0.0 or sigma_scat <= 0.0:
        zeros = np.zeros_like(ph)
        return float(zeros[0]) if is_scalar else zeros

    safe_sigma = max(float(sigma_scat), 1e-9)
    arg = (ph - float(phi_scat)) / safe_sigma
    scat_flux = float(f_scat) * np.exp(-0.5 * (arg ** 2))

    if is_scalar:
        return float(scat_flux[0])
    return scat_flux


def henyey_greenstein_scattering(
    theta_rad: Union[float, np.ndarray],
    g: float = 0.75,
) -> Union[float, np.ndarray]:
    """Evaluate the Henyey-Greenstein scattering phase function p(theta).

    p(theta) = (1 - g^2) / (4 * pi * (1 + g^2 - 2 * g * cos(theta))^(3/2))

    Args:
        theta_rad: Scattering angle in radians (0 = direct forward scattering).
        g: Scattering asymmetry parameter in (-1, 1). Typically 0.7 - 0.85 for silicate dust.

    Returns:
        Phase function value p(theta) normalized over the 4pi sphere.
    """
    g_val = float(np.clip(g, -0.999, 0.999))
    cos_t = np.cos(theta_rad)
    denom = (1.0 + g_val ** 2 - 2.0 * g_val * cos_t) ** 1.5
    denom = np.maximum(denom, 1e-12)
    return (1.0 - g_val ** 2) / (4.0 * np.pi * denom)


def phase_to_scattering_angle(
    phase: np.ndarray,
    inclination_deg: float = 90.0,
) -> np.ndarray:
    """Convert orbital phase to scattering angle theta between star, dust, and observer.

    cos(theta) = sin(i) * cos(2 * pi * phase)

    Args:
        phase: 1D array of orbital phases [-0.5, 0.5).
        inclination_deg: Orbital inclination in degrees (90.0 = edge-on transit).

    Returns:
        1D array of scattering angles in radians.
    """
    ph = np.asarray(phase, dtype=np.float64)
    i_rad = np.radians(inclination_deg)
    cos_theta = np.sin(i_rad) * np.cos(2.0 * np.pi * ph)
    cos_theta = np.clip(cos_theta, -1.0, 1.0)
    return np.arccos(cos_theta)


def estimate_forward_scattering_significance(
    phase: np.ndarray,
    flux: np.ndarray,
    flux_err: Optional[np.ndarray] = None,
    pre_ingress_window: Tuple[float, float] = (-0.05, -0.01),
    out_of_transit_window: Tuple[float, float] = (-0.25, -0.10),
) -> Tuple[float, float]:
    """Estimate the amplitude and statistical significance (Z-score) of pre-ingress brightening.

    Args:
        phase: 1D array of orbital phases.
        flux: 1D array of normalized flux values.
        flux_err: Optional 1D photometric uncertainties.
        pre_ingress_window: (min_phase, max_phase) where forward scattering is expected.
        out_of_transit_window: (min_phase, max_phase) representing unperturbed baseline.

    Returns:
        Tuple of (f_scat_amplitude, z_significance).
    """
    ph = np.asarray(phase, dtype=np.float64)
    fl = np.asarray(flux, dtype=np.float64)

    pre_mask = (ph >= pre_ingress_window[0]) & (ph <= pre_ingress_window[1])
    oot_mask = (ph >= out_of_transit_window[0]) & (ph <= out_of_transit_window[1])

    if np.sum(pre_mask) < 2 or np.sum(oot_mask) < 5:
        return 0.0, 0.0

    oot_mean = float(np.median(fl[oot_mask]))
    oot_std = float(np.std(fl[oot_mask]))
    if oot_std <= 0.0:
        oot_std = 0.0003

    pre_max = float(np.max(fl[pre_mask]))
    amp = max(0.0, pre_max - oot_mean)

    n_pre = float(np.sum(pre_mask))
    se = oot_std / np.sqrt(n_pre)
    z_score = amp / se if se > 0.0 else 0.0

    return amp, float(z_score)
