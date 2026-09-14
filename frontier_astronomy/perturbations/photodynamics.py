"""Photodynamic 3-body transit perturbation modeling for exomoon and Trojan detection.

Implements:
- 3-body photodynamics for Star-Planet-Moon and Star-Planet-Trojan systems.
- Barycentric Transit Timing Variations (TTV) according to Sartoretti & Schneider (1999)
  and Kipping (2009a): A_TTV = a_p / v_B = (a_sp / a_B) * (P_B / 2pi) * (M_s / (M_p + M_s)).
- Velocity-induced Transit Duration Variations (TDV-V) according to Kipping (2009b):
  A_TDV_V = T_dur * (a_sp / a_B) * (P_B / P_s) * (M_s / (M_p + M_s)).
- Hill sphere stability and critical orbital separation calculations.
- Multi-body analytic light curve generation with mutual transit and shoulder geometry.
"""

from __future__ import annotations

from typing import Optional, Tuple, Dict, Any, Union
import numpy as np

from frontier_astronomy.core.constants import (
    G,
    M_SUN,
    R_SUN,
    M_JUPITER,
    R_JUPITER,
    M_EARTH,
    R_EARTH,
    AU,
    DAY_SECONDS,
    MINUTE_SECONDS,
    HOUR_SECONDS,
)
from frontier_astronomy.core.math_utils import symmetric_trapezoid_transit


def barycentric_semi_major_axis(
    m_star: float,
    period_seconds: float,
) -> float:
    """Calculate heliocentric orbital semi-major axis of the planet-moon barycenter.

    Args:
        m_star: Stellar mass in kg.
        period_seconds: Orbital period of the barycenter in seconds.

    Returns:
        Semi-major axis a_B in meters.
    """
    if m_star <= 0 or period_seconds <= 0:
        raise ValueError("Mass and orbital period must be strictly positive.")
    return float((G * m_star * (period_seconds ** 2) / (4.0 * (np.pi ** 2))) ** (1.0 / 3.0))


def barycentric_orbital_velocity(
    m_star: float,
    semi_major_axis_m: float,
) -> float:
    """Calculate circular orbital velocity of the planet-moon barycenter.

    Args:
        m_star: Stellar mass in kg.
        semi_major_axis_m: Semi-major axis in meters.

    Returns:
        Orbital velocity v_B in m/s.
    """
    if m_star <= 0 or semi_major_axis_m <= 0:
        raise ValueError("Mass and semi-major axis must be strictly positive.")
    return float(np.sqrt(G * m_star / semi_major_axis_m))


def satellite_semi_major_axis(
    m_planet: float,
    m_moon: float,
    period_seconds: float,
) -> float:
    """Calculate mutual semi-major axis a_sp of the satellite orbit around the planet.

    Args:
        m_planet: Planetary mass in kg.
        m_moon: Satellite mass in kg.
        period_seconds: Satellite orbital period around the planet in seconds.

    Returns:
        Semi-major axis a_sp in meters.
    """
    total_mass = m_planet + m_moon
    if total_mass <= 0 or period_seconds <= 0:
        raise ValueError("Total mass and period must be strictly positive.")
    return float((G * total_mass * (period_seconds ** 2) / (4.0 * (np.pi ** 2))) ** (1.0 / 3.0))


def hill_radius(
    m_star: float,
    m_planet: float,
    m_moon: float,
    semi_major_axis_barycenter: float,
) -> float:
    """Calculate planetary Hill sphere radius.

    R_H = a_B * ((M_p + M_s) / (3 * M_*))^(1/3)

    Args:
        m_star: Stellar mass in kg.
        m_planet: Planetary mass in kg.
        m_moon: Satellite mass in kg.
        semi_major_axis_barycenter: Semi-major axis of barycentric orbit in meters.

    Returns:
        Hill radius R_H in meters.
    """
    total_planet_mass = m_planet + m_moon
    if m_star <= 0 or total_planet_mass <= 0 or semi_major_axis_barycenter <= 0:
        raise ValueError("Masses and semi-major axis must be strictly positive.")
    return float(semi_major_axis_barycenter * ((total_planet_mass / (3.0 * m_star)) ** (1.0 / 3.0)))


def critical_satellite_stability_radius(
    hill_rad_m: float,
    retrograde: bool = False,
) -> float:
    """Calculate the maximum stable orbital radius for a satellite (Domingos et al. 2006).

    a_crit approx 0.36 * R_H for prograde satellites, 0.49 * R_H for retrograde satellites.

    Args:
        hill_rad_m: Hill radius in meters.
        retrograde: If True, uses retrograde stability coefficient (0.49).

    Returns:
        Critical stability semi-major axis in meters.
    """
    coef = 0.49 if retrograde else 0.36
    return float(coef * hill_rad_m)


def barycentric_ttv_amplitude(
    m_star: float,
    m_planet: float,
    m_moon: float,
    p_planet_days: float,
    p_moon_days: float,
) -> float:
    """Calculate peak Transit Timing Variation (TTV) amplitude in minutes.

    Formulation (Sartoretti & Schneider 1999; Kipping 2009a):
        A_TTV = a_p / v_B = (a_sp / a_B) * (P_B / 2pi) * (M_s / (M_p + M_s))
    where:
        a_sp: mutual planet-satellite semi-major axis
        a_p = a_sp * (M_s / (M_p + M_s)): planet reflex displacement from barycenter
        v_B: barycenter orbital velocity around star

    Args:
        m_star: Stellar mass in kg.
        m_planet: Planetary mass in kg.
        m_moon: Moon mass in kg.
        p_planet_days: Planetary orbital period in days.
        p_moon_days: Satellite orbital period around planet in days.

    Returns:
        TTV amplitude A_TTV in minutes.
    """
    if m_moon <= 0.0:
        return 0.0

    p_b_sec = p_planet_days * DAY_SECONDS
    p_s_sec = p_moon_days * DAY_SECONDS

    a_b = barycentric_semi_major_axis(m_star, p_b_sec)
    v_b = barycentric_orbital_velocity(m_star, a_b)
    a_sp = satellite_semi_major_axis(m_planet, m_moon, p_s_sec)

    mass_factor = m_moon / (m_planet + m_moon)
    a_p = a_sp * mass_factor

    a_ttv_seconds = a_p / v_b
    return float(a_ttv_seconds / MINUTE_SECONDS)


def velocity_tdv_amplitude(
    m_star: float,
    m_planet: float,
    m_moon: float,
    p_planet_days: float,
    p_moon_days: float,
    t_dur_hours: float,
) -> float:
    """Calculate velocity-induced Transit Duration Variation (TDV-V) amplitude in minutes.

    Formulation (Kipping 2009b):
        A_TDV_V = T_dur * (a_sp / a_B) * (P_B / P_s) * (M_s / (M_p + M_s))
                = T_dur * (v_p/B / v_B)
    where:
        v_p/B = 2pi * a_p / P_s is planet orbital velocity relative to barycenter.

    Args:
        m_star: Stellar mass in kg.
        m_planet: Planetary mass in kg.
        m_moon: Moon mass in kg.
        p_planet_days: Planetary orbital period in days.
        p_moon_days: Satellite orbital period in days.
        t_dur_hours: Mean primary transit duration in hours.

    Returns:
        TDV-V amplitude in minutes.
    """
    if m_moon <= 0.0 or t_dur_hours <= 0.0:
        return 0.0

    p_b_sec = p_planet_days * DAY_SECONDS
    p_s_sec = p_moon_days * DAY_SECONDS

    a_b = barycentric_semi_major_axis(m_star, p_b_sec)
    a_sp = satellite_semi_major_axis(m_planet, m_moon, p_s_sec)

    mass_factor = m_moon / (m_planet + m_moon)
    a_sp_over_a_b = a_sp / a_b
    p_ratio = p_planet_days / p_moon_days

    a_tdv_hours = t_dur_hours * a_sp_over_a_b * p_ratio * mass_factor
    return float(a_tdv_hours * MINUTE_SECONDS)


class PhotodynamicPerturbationModel:
    """Comprehensive 3-body photodynamic transit perturbation model.

    Models:
    - Primary planet Keplerian motion around star.
    - Exomoon Keplerian reflex perturbation of planet center-of-mass (TTV).
    - Exomoon tangential velocity modulation of transit chord duration (TDV-V).
    - Secondary transit dips (satellite transits across stellar disk).
    - Co-orbital Trojan bodies at L4 (+60 deg) and L5 (-60 deg).
    """

    def __init__(
        self,
        m_star: float = M_SUN,
        m_planet: float = M_JUPITER,
        p_planet: float = 10.0,
        m_moon: float = 0.0,
        p_moon: float = 1.5,
        t0_planet: float = 0.0,
        r_star: float = R_SUN,
        r_planet: float = R_JUPITER,
        r_moon: float = 0.0,
        duration_hours: float = 4.0,
        impact_parameter: float = 0.0,
        phi_moon_0: float = 0.0,
        trojan_mass: float = 0.0,
        trojan_lagrange: str = "L4",
        trojan_depth: float = 0.0,
        trojan_duration_hours: Optional[float] = None,
    ) -> None:
        """Initialize photodynamic perturbation model.

        Args:
            m_star: Stellar mass (kg).
            m_planet: Planet mass (kg).
            p_planet: Planet orbital period (days).
            m_moon: Moon mass (kg).
            p_moon: Moon orbital period around planet (days).
            t0_planet: Primary transit epoch (days).
            r_star: Stellar radius (m).
            r_planet: Planetary radius (m).
            r_moon: Satellite radius (m).
            duration_hours: Unperturbed transit duration (hours).
            impact_parameter: Orbital impact parameter b in [0, 1).
            phi_moon_0: Initial satellite orbital phase at t0 (radians).
            trojan_mass: Trojan companion mass (kg).
            trojan_lagrange: Trojan Lagrange point ("L4" or "L5").
            trojan_depth: Trojan secondary transit depth (fractional).
            trojan_duration_hours: Trojan transit duration (defaults to planet duration).
        """
        self.m_star = float(m_star)
        self.m_planet = float(m_planet)
        self.p_planet = float(p_planet)
        self.m_moon = float(m_moon)
        self.p_moon = float(p_moon)
        self.t0_planet = float(t0_planet)
        self.r_star = float(r_star)
        self.r_planet = float(r_planet)
        self.r_moon = float(r_moon)
        self.duration_hours = float(duration_hours)
        self.impact_parameter = float(impact_parameter)
        self.phi_moon_0 = float(phi_moon_0)
        self.trojan_mass = float(trojan_mass)
        self.trojan_lagrange = str(trojan_lagrange).upper()
        self.trojan_depth = float(trojan_depth)
        self.trojan_duration_hours = (
            float(trojan_duration_hours) if trojan_duration_hours is not None else float(duration_hours)
        )

        # Precompute fundamental orbital scales
        p_b_sec = self.p_planet * DAY_SECONDS
        self.a_b = barycentric_semi_major_axis(self.m_star, p_b_sec)
        self.v_b = barycentric_orbital_velocity(self.m_star, self.a_b)
        self.hill_r = hill_radius(self.m_star, self.m_planet, self.m_moon, self.a_b)
        self.crit_a = critical_satellite_stability_radius(self.hill_r)

        if self.m_moon > 0.0:
            p_s_sec = self.p_moon * DAY_SECONDS
            self.a_sp = satellite_semi_major_axis(self.m_planet, self.m_moon, p_s_sec)
            self.mass_ratio_moon = self.m_moon / (self.m_planet + self.m_moon)
            self.a_p = self.a_sp * self.mass_ratio_moon
            self.a_s = self.a_sp * (self.m_planet / (self.m_planet + self.m_moon))
            self.v_pb = (2.0 * np.pi * self.a_p) / p_s_sec
            self.ttv_amp_minutes = barycentric_ttv_amplitude(
                self.m_star, self.m_planet, self.m_moon, self.p_planet, self.p_moon
            )
            self.tdv_amp_minutes = velocity_tdv_amplitude(
                self.m_star, self.m_planet, self.m_moon, self.p_planet, self.p_moon, self.duration_hours
            )
        else:
            self.a_sp = 0.0
            self.mass_ratio_moon = 0.0
            self.a_p = 0.0
            self.a_s = 0.0
            self.v_pb = 0.0
            self.ttv_amp_minutes = 0.0
            self.tdv_amp_minutes = 0.0

        # Physical transit depths
        self.planet_depth = (self.r_planet / self.r_star) ** 2 if self.r_star > 0 else 0.01
        self.moon_depth = (self.r_moon / self.r_star) ** 2 if (self.r_star > 0 and self.r_moon > 0) else 0.0

    def compute_ttv(self, epoch_indices: np.ndarray) -> np.ndarray:
        """Calculate Transit Timing Variation (TTV) in minutes for specified epochs.

        delta t_TTV(n) = A_TTV * sin(2pi * n * (P_B / P_s) + phi_0)

        Args:
            epoch_indices: 1D array of integer transit epoch numbers.

        Returns:
            1D array of timing offsets in minutes.
        """
        epochs = np.asarray(epoch_indices, dtype=np.float64)
        if self.m_moon <= 0.0 or self.ttv_amp_minutes <= 0.0:
            return np.zeros_like(epochs)

        psi = 2.0 * np.pi * (self.p_planet / self.p_moon) * epochs + self.phi_moon_0
        return self.ttv_amp_minutes * np.sin(psi)

    def compute_tdv(self, epoch_indices: np.ndarray) -> np.ndarray:
        """Calculate Transit Duration Variation (TDV-V) in minutes for specified epochs.

        delta T_TDV(n) = - A_TDV * cos(2pi * n * (P_B / P_s) + phi_0)
                       = A_TDV * sin(2pi * n * (P_B / P_s) + phi_0 - pi/2)
        demonstrating the exact pi/2 (90 deg) orthogonal phase invariant.

        Args:
            epoch_indices: 1D array of integer transit epoch numbers.

        Returns:
            1D array of duration variations in minutes.
        """
        epochs = np.asarray(epoch_indices, dtype=np.float64)
        if self.m_moon <= 0.0 or self.tdv_amp_minutes <= 0.0:
            return np.zeros_like(epochs)

        psi = 2.0 * np.pi * (self.p_planet / self.p_moon) * epochs + self.phi_moon_0
        # Exactly 90 degrees out of phase with TTV (-cos = sin(psi - pi/2))
        return -self.tdv_amp_minutes * np.cos(psi)

    def evaluate_transit_lightcurve(
        self,
        times: np.ndarray,
        limb_darkening: Tuple[float, float] = (0.3, 0.2),
    ) -> np.ndarray:
        """Evaluate synthetic normalized multi-body light curve at input timestamps.

        Includes primary transit with TTV & TDV, secondary moon dip, and Trojan dip.

        Args:
            times: 1D array of timestamps in days.
            limb_darkening: (u1, u2) quadratic limb darkening coefficients (unused in trapezoid).

        Returns:
            1D array of normalized flux values.
        """
        t = np.asarray(times, dtype=np.float64)
        flux = np.ones_like(t)

        epochs = np.round((t - self.t0_planet) / self.p_planet).astype(np.int32)
        unique_epochs = np.unique(epochs)

        dur_days_planet = self.duration_hours / 24.0

        for ep in unique_epochs:
            t_linear = self.t0_planet + ep * self.p_planet

            # Barycentric perturbation
            if self.m_moon > 0.0:
                psi_ep = 2.0 * np.pi * (self.p_planet / self.p_moon) * ep + self.phi_moon_0
                ttv_days = (self.ttv_amp_minutes / 1440.0) * np.sin(psi_ep)
                tdv_days = (self.tdv_amp_minutes / 1440.0) * (-np.cos(psi_ep))
            else:
                ttv_days = 0.0
                tdv_days = 0.0

            actual_t0 = t_linear + ttv_days
            actual_dur_days = max(0.01, dur_days_planet + tdv_days)

            # Restrict calculation to transit vicinity
            win_mask = np.abs(t - actual_t0) < (actual_dur_days * 2.0)
            if not np.any(win_mask):
                continue

            t_win = t[win_mask]
            dt_planet = t_win - actual_t0
            phi_planet = dt_planet / self.p_planet
            dur_phase = actual_dur_days / self.p_planet

            # Primary planet transit
            tr_planet = symmetric_trapezoid_transit(
                phase=phi_planet,
                period=self.p_planet,
                depth=self.planet_depth,
                duration_phase=dur_phase,
                ingress_ratio=0.15,
            )

            # Secondary moon transit (if moon radius/depth > 0)
            tr_moon_dip = np.zeros_like(tr_planet)
            if self.m_moon > 0.0 and self.moon_depth > 0.0:
                # Moon projected displacement along orbit
                psi_t = 2.0 * np.pi * (self.p_planet / self.p_moon) * ep + self.phi_moon_0
                # Displacement in time units: moon leads or lags
                dt_moon_center = (self.p_moon / 4.0) * np.cos(psi_t)
                t_moon_mid = actual_t0 + dt_moon_center
                phi_moon = (t_win - t_moon_mid) / self.p_planet
                dur_moon_phase = (self.duration_hours * 0.4 / 24.0) / self.p_planet

                tr_moon = symmetric_trapezoid_transit(
                    phase=phi_moon,
                    period=self.p_planet,
                    depth=self.moon_depth,
                    duration_phase=dur_moon_phase,
                    ingress_ratio=0.25,
                )
                tr_moon_dip = 1.0 - tr_moon

            combined_dip = (1.0 - tr_planet) + tr_moon_dip
            flux[win_mask] -= combined_dip

        # Trojan dip (L4 at +60 deg, L5 at -60 deg)
        if self.trojan_depth > 0.0:
            phase_offset = (1.0 / 6.0) if self.trojan_lagrange == "L4" else (-1.0 / 6.0)
            dur_phase_trojan = (self.trojan_duration_hours / 24.0) / self.p_planet
            t_trojan_ref = self.t0_planet + phase_offset * self.p_planet

            phase_trojan = ((t - t_trojan_ref) / self.p_planet + 0.5) % 1.0 - 0.5
            tr_trojan = symmetric_trapezoid_transit(
                phase=phase_trojan,
                period=self.p_planet,
                depth=self.trojan_depth,
                duration_phase=dur_phase_trojan,
                ingress_ratio=0.20,
            )
            flux -= (1.0 - tr_trojan)

        return flux

    def detect_exomoon_signature(
        self,
        measured_ttvs: np.ndarray,
        measured_tdvs: np.ndarray,
        tolerance_deg: float = 15.0,
    ) -> Dict[str, Any]:
        """Evaluate whether measured TTV and TDV series satisfy the orthogonal exomoon signature.

        Args:
            measured_ttvs: 1D array of measured TTVs (minutes).
            measured_tdvs: 1D array of measured TDVs (minutes).
            tolerance_deg: Maximum permissible deviation from 90 degrees.

        Returns:
            Dictionary containing phase offset, exomoon candidate boolean, and metrics.
        """
        from frontier_astronomy.perturbations.tdv_extractor import test_orthogonal_phase_invariant

        return test_orthogonal_phase_invariant(
            ttv_amplitudes=measured_ttvs,
            tdv_amplitudes=measured_tdvs,
            tolerance_deg=tolerance_deg,
        )
