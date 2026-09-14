"""Core astronomical primitives, mathematical utilities, and preprocessing algorithms."""

from frontier_astronomy.core.types import (
    LightCurveData,
    FoldedTransit,
    DustTailDetectionResult,
    ExomoonPerturbationResult,
    SpectrumData,
    AtmosphericInversionResult,
    BenchmarkSystem,
)
from frontier_astronomy.core import constants
from frontier_astronomy.core.constants import (
    bkjd_to_bjd,
    bjd_to_bkjd,
    btjd_to_bjd,
    bjd_to_btjd,
    bkjd_to_btjd,
    btjd_to_bkjd,
)
from frontier_astronomy.core.math_utils import (
    chi_squared,
    reduced_chi_squared,
    bic,
    aic,
    delta_bic,
    likelihood_ratio_test,
    median_absolute_deviation,
    running_median,
    weighted_mean_and_std,
    henyey_greenstein_phase_function,
    symmetric_trapezoid_transit,
)
from frontier_astronomy.core.preprocessing import (
    clean_quality,
    asymmetric_mad_clip,
    iterative_savgol_detrend,
    phase_fold,
    epoch_split,
    fold_light_curve,
    inverse_variance_bin,
    preprocess_light_curve,
)

__all__ = [
    # Types
    "LightCurveData",
    "FoldedTransit",
    "DustTailDetectionResult",
    "ExomoonPerturbationResult",
    "SpectrumData",
    "AtmosphericInversionResult",
    "BenchmarkSystem",
    # Constants
    "constants",
    "bkjd_to_bjd",
    "bjd_to_bkjd",
    "btjd_to_bjd",
    "bjd_to_btjd",
    "bkjd_to_btjd",
    "btjd_to_bkjd",
    # Math Utils
    "chi_squared",
    "reduced_chi_squared",
    "bic",
    "aic",
    "delta_bic",
    "likelihood_ratio_test",
    "median_absolute_deviation",
    "running_median",
    "weighted_mean_and_std",
    "henyey_greenstein_phase_function",
    "symmetric_trapezoid_transit",
    # Preprocessing
    "clean_quality",
    "asymmetric_mad_clip",
    "iterative_savgol_detrend",
    "phase_fold",
    "epoch_split",
    "fold_light_curve",
    "inverse_variance_bin",
    "preprocess_light_curve",
]
