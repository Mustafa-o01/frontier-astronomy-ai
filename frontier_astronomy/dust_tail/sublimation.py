"""Langmuir grain sublimation dynamics and dust lifetime modeling.

Sub-micron mineral dust grains (enstatite MgSiO3, forsterite Mg2SiO4, silica SiO2)
released from an evaporating rocky core sublimate under intense stellar irradiation.
The grain evaporation rate is governed by the Langmuir equation (Langmuir 1913; Kimura et al. 2002;
van Lieshout et al. 2014):

    da/dt = - (alpha_sub * P_vap(T)) / rho_grain * sqrt(mu * m_u / (2 * pi * k_B * T))

At T_sub ~ 1800 - 2100 K, the characteristic grain sublimation lifetime tau ~ 2 - 15 hours.
Because tau is comparable to the ultra-short planetary orbital period (P ~ 9 - 24 hours),
dust grains evaporate completely within roughly one orbit, explaining why cometary dust tails
terminate cleanly rather than forming continuous circumplanetary or circumsolar rings.
"""

from __future__ import annotations

from typing import Dict, Tuple
import numpy as np
from frontier_astronomy.core.constants import K_BOLTZMANN, AMU, M_SUN, L_SUN


# Mineral sublimation thermodynamic properties (van Lieshout et al. 2014, Kimura et al. 2002)
# A, B: Clausius-Clapeyron coefficients for ln(P_vap [dyn/cm^2]) = A - B / T
# rho: grain density in kg / m^3
# mu: molecular weight in g / mol
# alpha_sub: sticking/evaporation coefficient
MINERAL_PROPERTIES: Dict[str, Dict[str, float]] = {
    "enstatite": {
        "A": 38.9,
        "B": 68908.0,
        "rho": 3100.0,
        "mu": 100.39,
        "alpha_sub": 0.08,
    },
    "forsterite": {
        "A": 41.1,
        "B": 75520.0,
        "rho": 3270.0,
        "mu": 140.69,
        "alpha_sub": 0.05,
    },
    "silica": {
        "A": 35.8,
        "B": 66100.0,
        "rho": 2650.0,
        "mu": 60.08,
        "alpha_sub": 0.10,
    },
    "iron": {
        "A": 31.8,
        "B": 46200.0,
        "rho": 7874.0,
        "mu": 55.85,
        "alpha_sub": 0.50,
    },
}


def vapor_pressure(t_sub_k: float, mineral: str = "enstatite") -> float:
    """Calculate the equilibrium saturation vapor pressure in Pascals (Pa).

    ln(P_vap [dyn/cm^2]) = A - B / T
    1 Pa = 10 dyn/cm^2 => P_vap [Pa] = 0.1 * exp(A - B / T)

    Args:
        t_sub_k: Dust grain temperature in Kelvin.
        mineral: Mineral species ("enstatite", "forsterite", "silica", "iron").

    Returns:
        Vapor pressure in Pascals.
    """
    props = MINERAL_PROPERTIES.get(mineral.lower(), MINERAL_PROPERTIES["enstatite"])
    a_val = props["A"]
    b_val = props["B"]

    t_safe = max(float(t_sub_k), 100.0)
    # Clip exponent to prevent overflow
    exponent = np.clip(a_val - b_val / t_safe, -100.0, 50.0)
    p_dyn = np.exp(exponent)
    return float(0.1 * p_dyn)


def langmuir_sublimation_rate(
    t_sub_k: float,
    mineral: str = "enstatite",
) -> float:
    """Compute the Langmuir grain radius erosion rate |da/dt| in micrometers per hour.

    Formulation:
        |da/dt| = (alpha_sub * P_vap) / rho * sqrt(mu * m_u / (2 * pi * k_B * T))

    Args:
        t_sub_k: Dust grain temperature in Kelvin.
        mineral: Mineral species name.

    Returns:
        Grain radius loss rate |da/dt| in um / hour.
    """
    props = MINERAL_PROPERTIES.get(mineral.lower(), MINERAL_PROPERTIES["enstatite"])
    alpha_sub = props["alpha_sub"]
    rho = props["rho"]
    mu = props["mu"]

    p_vap = vapor_pressure(t_sub_k, mineral=mineral)

    t_safe = max(float(t_sub_k), 100.0)
    m_grain = mu * AMU
    thermal_factor = np.sqrt(m_grain / (2.0 * np.pi * K_BOLTZMANN * t_safe))

    # Rate in meters per second
    rate_m_s = (alpha_sub * p_vap / rho) * thermal_factor

    # Convert m / s to um / hour: 1 m/s = 1e6 um/s = 3.6e9 um/hr
    rate_um_hr = rate_m_s * 3.6e9
    return float(max(1e-12, rate_um_hr))


def compute_grain_lifetime_hours(
    t_sub_k: float = 1900.0,
    grain_radius_um: float = 0.2,
    stellar_lum_solar: float = 1.0,
    mineral: str = "enstatite",
) -> float:
    """Compute the grain sublimation lifetime tau in hours.

    Formulation:
        tau = a_grain / |da/dt|

    Args:
        t_sub_k: Dust equilibrium sublimation temperature in Kelvin (typically 1800 - 2100 K).
        grain_radius_um: Initial grain radius in micrometers (typically 0.1 - 1.0 um).
        stellar_lum_solar: Host stellar luminosity in solar units (L_sun).
        mineral: Mineral species ("enstatite", "forsterite", "silica", "iron").

    Returns:
        Sublimation lifetime tau in hours.
    """
    if t_sub_k <= 0.0 or grain_radius_um <= 0.0:
        raise ValueError("Temperature and grain radius must be strictly positive.")

    # Minor radiation field temperature adjustment if luminosity is varied
    lum_factor = max(float(stellar_lum_solar), 1e-4) ** 0.02
    effective_t = float(t_sub_k) * lum_factor

    rate_um_hr = langmuir_sublimation_rate(effective_t, mineral=mineral)
    tau_hr = float(grain_radius_um) / rate_um_hr

    # Physically reasonable bounds for numerical stability
    return float(np.clip(tau_hr, 1e-4, 1e5))


def equilibrium_grain_temperature(
    distance_au: float,
    stellar_teff_k: float = 5778.0,
    stellar_radius_solar: float = 1.0,
    albedo: float = 0.10,
) -> float:
    """Estimate thermal equilibrium temperature of a dust grain near a host star.

    T_eq = T_eff * sqrt(R_* / (2 * d)) * (1 - A)^(1/4)

    Args:
        distance_au: Orbital semi-major axis in Astronomical Units.
        stellar_teff_k: Stellar effective temperature in Kelvin.
        stellar_radius_solar: Stellar radius in solar radii (R_sun).
        albedo: Dust Bond albedo.

    Returns:
        Grain equilibrium temperature in Kelvin.
    """
    from frontier_astronomy.core.constants import R_SUN, AU
    r_star_m = stellar_radius_solar * R_SUN
    dist_m = distance_au * AU

    geom = np.sqrt(r_star_m / (2.0 * dist_m))
    t_eq = stellar_teff_k * geom * ((1.0 - albedo) ** 0.25)
    return float(t_eq)


def tail_truncation_phase(
    period_hours: float,
    tau_sub_hours: float,
) -> float:
    """Calculate the fractional orbital phase span traversed by dust grains before sublimation.

    Delta_phi = tau_sub / period

    Args:
        period_hours: Orbital period in hours.
        tau_sub_hours: Grain sublimation lifetime in hours.

    Returns:
        Tail length in orbital phase units.
    """
    if period_hours <= 0.0:
        raise ValueError("Period must be strictly positive.")
    return float(tau_sub_hours / period_hours)
