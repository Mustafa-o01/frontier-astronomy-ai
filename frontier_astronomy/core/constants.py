"""Physical and astronomical constants for the Frontier Astronomy AI Discovery Suite.

All constants are specified in standard SI units unless explicitly noted with
unit suffixes (_CGS, _AU, _DAYS, _SOLAR, etc.).
"""

import numpy as np

# ==============================================================================
# Fundamental Physical Constants (CODATA 2018 / IAU 2015)
# ==============================================================================
C: float = 299792458.0                    # Speed of light in vacuum [m / s]
G: float = 6.67430e-11                    # Gravitational constant [m^3 / (kg * s^2)]
H_PLANCK: float = 6.62607015e-34          # Planck constant [J * s]
H_BAR: float = H_PLANCK / (2.0 * np.pi)   # Reduced Planck constant [J * s]
K_B: float = 1.380649e-23                 # Boltzmann constant [J / K]
K_BOLTZMANN: float = K_B                  # Boltzmann constant alias [J / K]
N_A: float = 6.02214076e23                # Avogadro constant [mol^-1]
M_U: float = 1.66053906660e-27            # Atomic mass unit [kg]
AMU: float = M_U                          # Atomic mass unit alias [kg]
SIGMA_SB: float = 5.670374419e-8          # Stefan-Boltzmann constant [W / (m^2 * K^4)]

# ==============================================================================
# Astronomical System of Units
# ==============================================================================
AU: float = 149597870700.0                # Astronomical Unit [m]
PARSEC: float = 3.085677581491367e16      # Parsec [m]
LIGHT_YEAR: float = 9.4607304725808e15    # Light year [m]

# Stellar Units (IAU Resolution B3)
M_SUN: float = 1.98847e30                 # Solar mass [kg]
R_SUN: float = 6.957e8                    # Nominal solar radius [m]
L_SUN: float = 3.828e26                   # Nominal solar luminosity [W]
T_SUN: float = 5772.0                     # Solar effective temperature [K]

# Planetary Units
M_EARTH: float = 5.9722e24                # Earth mass [kg]
R_EARTH: float = 6.371e6                  # Nominal Earth equatorial radius [m]
M_JUPITER: float = 1.89813e27             # Jupiter mass [kg]
R_JUPITER: float = 7.1492e7               # Nominal Jupiter equatorial radius [m]
M_MOON: float = 7.342e22                  # Moon mass [kg]
R_MOON: float = 1.7374e6                  # Moon mean radius [m]

# Atmospheric Constants
MU_H2_HE: float = 2.3 * M_U               # Mean molecular weight for solar H2/He [kg]
P_REF_BAR: float = 1.0e5                  # Reference 1 bar pressure [Pa]

# ==============================================================================
# Time System Standards and Epoch Offsets
# ==============================================================================
DAY_SECONDS: float = 86400.0              # Seconds in one standard day [s]
MINUTE_SECONDS: float = 60.0              # Seconds in one minute [s]
HOUR_SECONDS: float = 3600.0              # Seconds in one hour [s]

# Barycentric Julian Date Reference Epochs
BJD_REF_KEPLER: float = 2454833.0         # BKJD = BJD - 2454833.0 (2009-01-01 12:00:00 TDB)
BJD_REF_TESS: float = 2457000.0           # BTJD = BJD - 2457000.0 (2014-12-08 00:00:00 TDB)
BKJD_TO_BTJD_OFFSET: float = 2167.0       # BTJD = BKJD - 2167.0

# Mission Nominal Cadences (in minutes and days)
KEPLER_LONG_CADENCE_MIN: float = 29.4244  # Kepler Long Cadence [min]
KEPLER_SHORT_CADENCE_MIN: float = 0.9808  # Kepler Short Cadence [min] (~58.85 s)
TESS_STANDARD_CADENCE_MIN: float = 2.0    # TESS Standard Cadence [min]
TESS_FAST_CADENCE_MIN: float = 0.3333333  # TESS Fast Cadence (20 s) [min]
TESS_FFI_EARLY_MIN: float = 30.0          # TESS Sector 1-26 FFI cadence [min]
TESS_FFI_EXT1_MIN: float = 10.0           # TESS Sector 27-55 FFI cadence [min]
TESS_FFI_EXT2_MIN: float = 3.3333333      # TESS Sector 56+ FFI cadence (200 s) [min]


def bkjd_to_bjd(bkjd: np.ndarray | float) -> np.ndarray | float:
    """Convert Barycentric Kepler Julian Date (BKJD) to Barycentric Julian Date (BJD)."""
    return bkjd + BJD_REF_KEPLER


def bjd_to_bkjd(bjd: np.ndarray | float) -> np.ndarray | float:
    """Convert Barycentric Julian Date (BJD) to Barycentric Kepler Julian Date (BKJD)."""
    return bjd - BJD_REF_KEPLER


def btjd_to_bjd(btjd: np.ndarray | float) -> np.ndarray | float:
    """Convert Barycentric TESS Julian Date (BTJD) to Barycentric Julian Date (BJD)."""
    return btjd + BJD_REF_TESS


def bjd_to_btjd(bjd: np.ndarray | float) -> np.ndarray | float:
    """Convert Barycentric Julian Date (BJD) to Barycentric TESS Julian Date (BTJD)."""
    return bjd - BJD_REF_TESS


def bkjd_to_btjd(bkjd: np.ndarray | float) -> np.ndarray | float:
    """Convert Barycentric Kepler Julian Date (BKJD) to Barycentric TESS Julian Date (BTJD)."""
    return bkjd - BKJD_TO_BTJD_OFFSET


def btjd_to_bkjd(btjd: np.ndarray | float) -> np.ndarray | float:
    """Convert Barycentric TESS Julian Date (BTJD) to Barycentric Kepler Julian Date (BKJD)."""
    return btjd + BKJD_TO_BTJD_OFFSET
