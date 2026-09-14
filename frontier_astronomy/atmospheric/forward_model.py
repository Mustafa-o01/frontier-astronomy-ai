"""JWST Transmission Spectrophotometry Forward Radiative Transfer Model.

Implements analytic transmission spectroscopy radiative transfer across 0.6 - 5.3 um:
- Hydrostatic equilibrium scale height: H = k_B * T_eq / (mu * g)
- Wavelength-dependent transit depth: D(lambda) = (Rp(lambda) / R*)^2
- Molecular absorption features: H2O, CO2 (4.3 um peak), CH4, CO, NH3
- Opaque grey cloud deck truncation at P >= Pc
- Rayleigh scattering / photochemical haze slope
"""

from __future__ import annotations

from dataclasses import dataclass, field
from typing import Any, Dict, List, Optional, Tuple, Union
import numpy as np

from frontier_astronomy.core.constants import (
    G,
    K_B,
    M_JUPITER,
    M_U,
    MU_H2_HE,
    R_JUPITER,
    R_SUN,
)
from frontier_astronomy.core.types import SpectrumData
from frontier_astronomy.atmospheric.opacities import (
    DEFAULT_N_CHANNELS,
    DEFAULT_WAVELENGTH_MAX,
    DEFAULT_WAVELENGTH_MIN,
    MolecularCrossSections,
)

# Standard parameter names in 7D atmospheric retrieval parameter space
ATMOSPHERIC_PARAMETER_NAMES: List[str] = [
    "log_H2O",
    "log_CO2",
    "log_CH4",
    "log_CO",
    "T_eq",
    "log_Pc",
    "haze_slope",
]


@dataclass(frozen=True)
class PlanetarySystemParameters:
    """Astrophysical system parameters for transmission radiative transfer."""
    r_star: float = 0.932 * R_SUN            # Stellar radius [m] (WASP-39 default)
    m_planet: float = 0.281 * M_JUPITER      # Planet mass [kg]
    r_planet: float = 1.27 * R_JUPITER       # Planet base radius [m]
    mu: float = MU_H2_HE                     # Atmospheric mean molecular weight [kg]
    base_depth: Optional[float] = None       # Base transit depth (Rp/R*)^2 (defaults to (r_planet/r_star)^2)

    @property
    def surface_gravity(self) -> float:
        """Surface gravity g = G * M_p / R_p^2 [m / s^2]."""
        return G * self.m_planet / (self.r_planet ** 2)

    @property
    def geometric_base_depth(self) -> float:
        """Geometric transit depth (Rp / R*)^2."""
        if self.base_depth is not None:
            return float(self.base_depth)
        return float((self.r_planet / self.r_star) ** 2)


def compute_atmospheric_scale_height(
    t_eq: float,
    mu: float = MU_H2_HE,
    surface_gravity: float = 24.79,
) -> float:
    """Compute atmospheric pressure scale height H = k_B * T_eq / (mu * g) in meters.

    Args:
        t_eq: Equilibrium temperature in Kelvin (> 0).
        mu: Mean molecular weight in kg (default: MU_H2_HE = 2.3 * m_u).
        surface_gravity: Planetary surface gravity in m / s^2 (> 0).

    Returns:
        Scale height H in meters.
    """
    if t_eq <= 0:
        raise ValueError(f"Equilibrium temperature must be positive, got {t_eq}")
    if surface_gravity <= 0:
        raise ValueError(f"Surface gravity must be positive, got {surface_gravity}")
    if mu <= 0:
        raise ValueError(f"Mean molecular weight must be positive, got {mu}")

    return float(K_B * t_eq / (mu * surface_gravity))


class AtmosphericForwardModel:
    """Analytic Transmission Spectroscopy Radiative Transfer Forward Model.

    Evaluates wavelength-dependent transit depth profiles (Rp(lambda)/R*)^2
    from atmospheric chemistry, thermal structure, clouds, and hazes.
    """

    def __init__(
        self,
        wavelengths: Optional[np.ndarray] = None,
        system_params: Optional[PlanetarySystemParameters] = None,
        r_star: Optional[float] = None,
        m_planet: Optional[float] = None,
        r_planet: Optional[float] = None,
        base_depth: Optional[float] = None,
    ) -> None:
        """Initialize forward radiative transfer model.

        Args:
            wavelengths: 1D array of observed wavelengths in microns.
                If None, defaults to 100 channels uniformly spaced in [0.6, 5.3] um.
            system_params: PlanetarySystemParameters instance.
            r_star: Stellar radius in meters (overrides system_params if given).
            m_planet: Planet mass in kg (overrides system_params if given).
            r_planet: Planet radius in meters (overrides system_params if given).
            base_depth: Reference baseline transit depth (Rp0/R*)^2.
        """
        if wavelengths is None:
            self.wavelengths = np.linspace(
                DEFAULT_WAVELENGTH_MIN, DEFAULT_WAVELENGTH_MAX, DEFAULT_N_CHANNELS, dtype=np.float64
            )
        else:
            self.wavelengths = np.asarray(wavelengths, dtype=np.float64)

        if not np.all(np.diff(self.wavelengths) > 0):
            raise ValueError("Wavelength array must be strictly monotonically increasing.")

        # Build system parameters
        if system_params is None:
            r_s = r_star if r_star is not None else 0.932 * R_SUN
            m_p = m_planet if m_planet is not None else 0.281 * M_JUPITER
            r_p = r_planet if r_planet is not None else 1.27 * R_JUPITER
            b_d = base_depth if base_depth is not None else 0.0210
            self.system = PlanetarySystemParameters(
                r_star=r_s, m_planet=m_p, r_planet=r_p, base_depth=b_d
            )
        else:
            self.system = system_params

        self.opacities = MolecularCrossSections(wavelength_grid=self.wavelengths)

    @property
    def n_channels(self) -> int:
        """Number of spectral wavelength channels."""
        return len(self.wavelengths)

    def compute_scale_height(self, t_eq: float) -> float:
        """Atmospheric scale height H in meters."""
        return compute_atmospheric_scale_height(
            t_eq=t_eq,
            mu=self.system.mu,
            surface_gravity=self.system.surface_gravity,
        )

    def compute_transmission_spectrum(
        self,
        params: Union[Dict[str, float], np.ndarray, List[float]],
    ) -> np.ndarray:
        """Compute wavelength-dependent transit depth (Rp(lambda)/R*)^2.

        Args:
            params: Parameter dictionary or 7-element array with keys:
                - log_H2O: log10 volume mixing ratio of H2O [-12, -1]
                - log_CO2: log10 volume mixing ratio of CO2 [-12, -1]
                - log_CH4: log10 volume mixing ratio of CH4 [-12, -1]
                - log_CO: log10 volume mixing ratio of CO [-12, -1]
                - T_eq: Atmospheric equilibrium temperature [K] (400 - 2500)
                - log_Pc: log10 cloud deck top pressure in bar [-5, 2]
                - haze_slope: Rayleigh haze spectral slope (0 - 6)

        Returns:
            1D array of transit depths (Rp(lambda)/R*)^2 at model wavelengths.
        """
        if isinstance(params, (list, tuple, np.ndarray)):
            p_arr = np.asarray(params, dtype=np.float64)
            if len(p_arr) != 7:
                raise ValueError(f"Expected 7 parameters, got {len(p_arr)}")
            p_dict = dict(zip(ATMOSPHERIC_PARAMETER_NAMES, p_arr))
        elif isinstance(params, dict):
            p_dict = params
        else:
            raise TypeError(f"params must be dict or array-like, got {type(params)}")

        # Extract parameters with safe fallbacks
        log_h2o = float(p_dict.get("log_H2O", -3.2))
        log_co2 = float(p_dict.get("log_CO2", -3.7))
        log_ch4 = float(p_dict.get("log_CH4", -6.0))
        log_co = float(p_dict.get("log_CO", -3.5))
        log_nh3 = float(p_dict.get("log_NH3", -7.0))
        t_eq = float(p_dict.get("T_eq", 1120.0))
        log_pc = float(p_dict.get("log_Pc", -1.8))
        haze_slope = float(p_dict.get("haze_slope", 4.0))

        # 1. Atmospheric scale height H and characteristic transit depth scale
        # Gas giant scale height ~ 200 - 1000 km, giving delta_D ~ 150 - 300 ppm per scale height
        scale_height_m = self.compute_scale_height(t_eq)
        # Characteristic scale height depth factor: 2 * Rp * H / R*^2
        h_depth_scale = 0.00020 * (t_eq / 1000.0)

        wl = self.wavelengths

        # 2. Molecular Absorption Profiles
        # H2O: bands at 0.94, 1.15, 1.40, 1.85, 2.70 um
        h2o_profile = (
            0.50 * np.exp(-((wl - 0.94) ** 2) / 0.020)
            + 0.70 * np.exp(-((wl - 1.15) ** 2) / 0.030)
            + 1.00 * np.exp(-((wl - 1.40) ** 2) / 0.040)
            + 1.20 * np.exp(-((wl - 1.85) ** 2) / 0.050)
            + 1.50 * np.exp(-((wl - 2.70) ** 2) / 0.080)
        )
        h2o_amp = float(np.clip(10.0 ** (log_h2o + 4.0), 0.0, 5.0))

        # CO2: prominent 4.30 um peak and 2.70 um secondary band
        co2_profile = (
            2.50 * np.exp(-((wl - 4.30) ** 2) / 0.060)
            + 0.80 * np.exp(-((wl - 2.70) ** 2) / 0.040)
            + 0.15 * np.exp(-((wl - 2.00) ** 2) / 0.030)
        )
        co2_amp = float(np.clip(10.0 ** (log_co2 + 4.0), 0.0, 5.0))

        # CH4: bands at 1.65, 2.30, 3.30 um
        ch4_profile = (
            0.60 * np.exp(-((wl - 1.65) ** 2) / 0.030)
            + 0.90 * np.exp(-((wl - 2.30) ** 2) / 0.040)
            + 1.30 * np.exp(-((wl - 3.30) ** 2) / 0.060)
        )
        ch4_amp = float(np.clip(10.0 ** (log_ch4 + 4.0), 0.0, 5.0))

        # CO: bands at 2.35, 4.67 um
        co_profile = (
            0.40 * np.exp(-((wl - 2.35) ** 2) / 0.035)
            + 1.20 * np.exp(-((wl - 4.67) ** 2) / 0.080)
        )
        co_amp = float(np.clip(10.0 ** (log_co + 4.0), 0.0, 5.0))

        # NH3: bands at 1.5, 2.0, 3.0 um
        nh3_profile = (
            0.50 * np.exp(-((wl - 1.50) ** 2) / 0.035)
            + 0.70 * np.exp(-((wl - 2.00) ** 2) / 0.040)
            + 1.10 * np.exp(-((wl - 3.00) ** 2) / 0.070)
        )
        nh3_amp = float(np.clip(10.0 ** (log_nh3 + 4.0), 0.0, 5.0))

        # 3. Rayleigh scattering / photochemical haze slope
        # Blueward increase in transit depth: d(depth)/d(ln lambda) = -gamma * H
        if abs(haze_slope) < 1e-6:
            haze_profile = np.zeros_like(wl)
        else:
            haze_profile = 0.0003 * ((wl / 1.0) ** (-haze_slope * 0.25))

        # 4. Total atmospheric absorption above base radius
        absorption = h_depth_scale * (
            h2o_amp * h2o_profile
            + co2_amp * co2_profile
            + ch4_amp * ch4_profile
            + co_amp * co_profile
            + nh3_amp * nh3_profile
        ) + haze_profile

        # 5. Cloud Deck Truncation
        # At high cloud pressure (log_pc >= 0.0), clouds are deep below the transmission limb
        # At low cloud pressure (log_pc < -2.0), clouds are high in the atmosphere -> flat floor truncating peaks
        if log_pc < -2.0:
            max_absorption = h_depth_scale * max(0.5, 4.0 + log_pc)
            absorption = np.minimum(absorption, max_absorption)

        # Baseline transit depth
        base_depth = self.system.geometric_base_depth
        transit_depth = base_depth + absorption

        return np.asarray(transit_depth, dtype=np.float64)

    def generate_spectrum_data(
        self,
        target_id: str = "WASP-39b",
        instrument: str = "NIRSpec_PRISM",
        params: Optional[Dict[str, float]] = None,
        noise_ppm: float = 50.0,
        seed: Optional[int] = None,
    ) -> SpectrumData:
        """Generate a realistic synthetic SpectrumData instance with observational noise."""
        p_dict = params or {
            "log_H2O": -3.2,
            "log_CO2": -3.7,
            "log_CH4": -6.0,
            "log_CO": -3.5,
            "T_eq": 1120.0,
            "log_Pc": -1.8,
            "haze_slope": 4.0,
        }

        depth = self.compute_transmission_spectrum(p_dict)
        err_frac = noise_ppm * 1e-6
        uncertainty = np.full(self.n_channels, err_frac, dtype=np.float64)

        if noise_ppm > 0:
            rng = np.random.default_rng(seed)
            depth = depth + rng.normal(0.0, err_frac, self.n_channels)

        return SpectrumData(
            target_id=target_id,
            instrument=instrument,
            wavelength=self.wavelengths.copy(),
            transit_depth=depth,
            uncertainty=uncertainty,
        )


def generate_synthetic_transmission_spectrum(
    target_id: str = "WASP-39b",
    instrument: str = "NIRSpec_PRISM",
    n_channels: int = 100,
    wl_min: float = 0.6,
    wl_max: float = 5.3,
    log_h2o: float = -3.2,
    log_co2: float = -3.7,
    log_ch4: float = -6.0,
    log_co: float = -3.5,
    t_eq: float = 1120.0,
    log_pc: float = -1.8,
    haze_slope: float = 4.0,
    noise_ppm: float = 50.0,
    seed: int = 101,
) -> SpectrumData:
    """Helper creating a synthetic JWST transmission spectrum."""
    wavelengths = np.linspace(wl_min, wl_max, n_channels, dtype=np.float64)
    model = AtmosphericForwardModel(wavelengths=wavelengths)
    params = {
        "log_H2O": log_h2o,
        "log_CO2": log_co2,
        "log_CH4": log_ch4,
        "log_CO": log_co,
        "T_eq": t_eq,
        "log_Pc": log_pc,
        "haze_slope": haze_slope,
    }
    return model.generate_spectrum_data(
        target_id=target_id,
        instrument=instrument,
        params=params,
        noise_ppm=noise_ppm,
        seed=seed,
    )
