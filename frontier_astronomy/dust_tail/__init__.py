"""Catastrophic Disintegrating Exoplanet & Dust Tail Hunter (Features F3 & F4).

Provides:
- Rappaport/Brogi cometary extinction forward model with steep sigmoid ingress and exponential egress tail.
- Henyey-Greenstein and Mie pre-ingress forward-scattering brightening model.
- Langmuir grain sublimation dynamics and dust lifetime computation.
- Automated cometary dust tail detector using Delta-BIC >= 10 and LRT p < 1e-5 hypothesis testing.
- Monte Carlo injection-recovery testing suite evaluating recovery rate >= 90% at SNR >= 5.0 and FPR <= 2.0%.
"""

from __future__ import annotations

from frontier_astronomy.dust_tail.extinction_model import (
    cometary_extinction_profile,
    compute_asymmetry_parameter,
)
from frontier_astronomy.dust_tail.forward_scattering import (
    forward_scattering_flux,
    henyey_greenstein_scattering,
    phase_to_scattering_angle,
    estimate_forward_scattering_significance,
)
from frontier_astronomy.dust_tail.sublimation import (
    compute_grain_lifetime_hours,
    langmuir_sublimation_rate,
    vapor_pressure,
    equilibrium_grain_temperature,
    tail_truncation_phase,
)
from frontier_astronomy.dust_tail.detector import (
    DustTailDetector,
    detect_dust_tail,
    fit_symmetric_transit,
    fit_cometary_dust_tail,
    compute_multi_epoch_depth_variability,
)
from frontier_astronomy.dust_tail.injection_recovery import (
    InjectionRecoveryTrial,
    InjectionRecoverySummary,
    inject_dust_tail,
    run_injection_recovery_trial,
    run_injection_recovery_suite,
    evaluate_false_positive_rate,
)

__all__ = [
    "cometary_extinction_profile",
    "compute_asymmetry_parameter",
    "forward_scattering_flux",
    "henyey_greenstein_scattering",
    "phase_to_scattering_angle",
    "estimate_forward_scattering_significance",
    "compute_grain_lifetime_hours",
    "langmuir_sublimation_rate",
    "vapor_pressure",
    "equilibrium_grain_temperature",
    "tail_truncation_phase",
    "DustTailDetector",
    "detect_dust_tail",
    "fit_symmetric_transit",
    "fit_cometary_dust_tail",
    "compute_multi_epoch_depth_variability",
    "InjectionRecoveryTrial",
    "InjectionRecoverySummary",
    "inject_dust_tail",
    "run_injection_recovery_trial",
    "run_injection_recovery_suite",
    "evaluate_false_positive_rate",
]
