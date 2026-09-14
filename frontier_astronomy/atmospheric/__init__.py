"""Rapid Atmospheric Chemistry Inversion Module for NASA JWST (Features F7, F8, F9).

Provides:
- F7: Forward Radiative Transfer Model & Precomputed Opacity Grids (0.6 - 5.3 um).
- F8: Rapid Amortized Bayesian Parameter Estimation via Conditional RealNVP Flow (< 0.1s).
- F9: Benchmark Atmospheric Retrieval Validation on WASP-39b & WASP-96b within 1-sigma.
"""

from __future__ import annotations

from frontier_astronomy.atmospheric.opacities import (
    DEFAULT_N_CHANNELS,
    DEFAULT_WAVELENGTH_MAX,
    DEFAULT_WAVELENGTH_MIN,
    MOLECULAR_SPECIES,
    MolecularCrossSections,
    evaluate_molecular_cross_section,
    get_opacity_grid,
)
from frontier_astronomy.atmospheric.forward_model import (
    ATMOSPHERIC_PARAMETER_NAMES,
    AtmosphericForwardModel,
    PlanetarySystemParameters,
    compute_atmospheric_scale_height,
    generate_synthetic_transmission_spectrum,
)
from frontier_astronomy.atmospheric.normalizing_flow import (
    DEFAULT_PARAM_BOUNDS,
    RealNVPConditionalFlow,
)
from frontier_astronomy.atmospheric.trainer import (
    AmortizedFlowTrainer,
    generate_atmospheric_grid,
    train_amortized_retrieval_model,
)
from frontier_astronomy.atmospheric.inversion import (
    AtmosphericInversionEngine,
    invert_spectrum,
)
from frontier_astronomy.atmospheric.benchmarks import (
    run_all_atmospheric_benchmarks,
    run_wasp39b_retrieval_benchmark,
    run_wasp96b_retrieval_benchmark,
)

__all__ = [
    # Opacities
    "DEFAULT_WAVELENGTH_MIN",
    "DEFAULT_WAVELENGTH_MAX",
    "DEFAULT_N_CHANNELS",
    "MOLECULAR_SPECIES",
    "MolecularCrossSections",
    "get_opacity_grid",
    "evaluate_molecular_cross_section",
    # Forward Model
    "ATMOSPHERIC_PARAMETER_NAMES",
    "AtmosphericForwardModel",
    "PlanetarySystemParameters",
    "compute_atmospheric_scale_height",
    "generate_synthetic_transmission_spectrum",
    # Flow Network
    "DEFAULT_PARAM_BOUNDS",
    "RealNVPConditionalFlow",
    # Trainer
    "AmortizedFlowTrainer",
    "generate_atmospheric_grid",
    "train_amortized_retrieval_model",
    # Inversion Engine
    "AtmosphericInversionEngine",
    "invert_spectrum",
    # Benchmarks
    "run_wasp39b_retrieval_benchmark",
    "run_wasp96b_retrieval_benchmark",
    "run_all_atmospheric_benchmarks",
]
