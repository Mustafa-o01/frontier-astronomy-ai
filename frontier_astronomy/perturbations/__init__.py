"""Exomoon & Trojan World Gravitational Perturbation Detector (Features F5 & F6).

This module implements:
- 3-body photodynamic perturbation modeling (TTV, TDV-V, Hill sphere, mutual events)
- Template cross-correlation O-C timing residual extraction per epoch
- Transit duration variation extraction and pathognomonic orthogonal pi/2 phase invariant test
- Secondary transit shoulder anomaly detector during ingress/egress
- L4/L5 co-orbital Trojan companion dip hunter at +/- 60 deg phase offset
- Multi-body sensitivity validation and Bayesian posterior probability estimation
"""

from __future__ import annotations

from typing import Optional, Dict, Any
import numpy as np

from frontier_astronomy.core.types import ExomoonPerturbationResult, LightCurveData
from frontier_astronomy.perturbations.photodynamics import (
    barycentric_semi_major_axis,
    barycentric_orbital_velocity,
    satellite_semi_major_axis,
    hill_radius,
    critical_satellite_stability_radius,
    barycentric_ttv_amplitude,
    velocity_tdv_amplitude,
    PhotodynamicPerturbationModel,
)
from frontier_astronomy.perturbations.ttv_extractor import (
    TTVExtractionResult,
    extract_ttv,
    extract_ttv_from_light_curve,
)
from frontier_astronomy.perturbations.tdv_extractor import (
    TDVExtractionResult,
    extract_tdv,
    extract_tdv_from_light_curve,
    test_orthogonal_phase_invariant,
)
from frontier_astronomy.perturbations.shoulder_detector import (
    ShoulderDetectionResult,
    detect_transit_shoulders,
    detect_transit_shoulders_from_light_curve,
)
from frontier_astronomy.perturbations.trojan_detector import (
    TrojanDetectionResult,
    detect_trojan_companions,
    detect_trojan_companions_from_light_curve,
)
from frontier_astronomy.perturbations.sensitivity import (
    compute_minimum_detectable_moon_mass,
    compute_ttv_snr,
    compute_sensitivity_grid,
    compute_exomoon_posterior,
)


def detect_perturbations(
    light_curve: LightCurveData,
    period: float,
    t0: float,
    duration_hours: Optional[float] = None,
    depth: Optional[float] = None,
    snr_threshold: float = 3.0,
    tolerance_deg: float = 15.0,
) -> ExomoonPerturbationResult:
    """Run end-to-end multi-body gravitational perturbation detection pipeline.

    Extracts:
    1. Per-epoch Transit Timing Variations (TTV) via template cross-correlation.
    2. Per-epoch Transit Duration Variations (TDV).
    3. Orthogonal pi/2 phase invariant test (evaluates exomoon vs MMR false positive).
    4. Ingress/egress secondary transit shoulder anomalies.
    5. Co-orbital Trojan companion dips at L4/L5 (+/- 60 deg).
    6. Bayesian posterior probability P(moon|data).

    Args:
        light_curve: Calibrated LightCurveData instance.
        period: Primary planet orbital period in days.
        t0: Reference mid-transit epoch in days.
        duration_hours: Optional primary transit duration in hours.
        depth: Optional primary transit depth.
        snr_threshold: Minimum SNR threshold for candidates (default 3.0).
        tolerance_deg: Orthogonal phase test tolerance around 90 deg (default 15.0).

    Returns:
        ExomoonPerturbationResult frozen dataclass instance matching PROJECT.md.
    """
    lc = light_curve

    # Automatically resolve duration and depth from benchmark registry if not provided
    if duration_hours is None:
        try:
            from frontier_astronomy.ingestion.catalog import BENCHMARK_REGISTRY
            tid_clean = lc.target_id.replace(" ", "").replace("-", "").lower()
            for bench in BENCHMARK_REGISTRY.values():
                bid_clean = bench.target_id.replace(" ", "").replace("-", "").lower()
                cname_clean = bench.common_name.replace(" ", "").replace("-", "").lower() if hasattr(bench, "common_name") else ""
                if tid_clean in (bid_clean, cname_clean):
                    duration_hours = bench.duration_hours
                    if depth is None:
                        depth = bench.depth_ppm * 1e-6
                    break
        except Exception:
            pass

    # 1. Extract TTVs across epochs
    ttv_res = extract_ttv_from_light_curve(
        lc=lc,
        period=period,
        t0=t0,
        duration_hours=duration_hours,
        depth=depth,
    )

    # 2. Extract TDVs across epochs
    tdv_res = extract_tdv_from_light_curve(
        lc=lc,
        period=period,
        t0=t0,
        duration_hours=duration_hours,
        depth=depth,
        transit_times=ttv_res.transit_times if len(ttv_res.transit_times) > 0 else None,
        observed_epochs=ttv_res.epochs if len(ttv_res.epochs) > 0 else None,
    )

    # 3. Test orthogonal pi/2 phase invariant
    phase_res = test_orthogonal_phase_invariant(
        ttv_amplitudes=ttv_res.ttv_minutes,
        tdv_amplitudes=tdv_res.tdv_minutes,
        tolerance_deg=tolerance_deg,
    )

    # 4. Ingress / egress shoulder anomaly detection
    shoulder_res = detect_transit_shoulders_from_light_curve(
        lc=lc,
        period=period,
        t0=t0,
        duration_hours=duration_hours,
        depth=depth,
        snr_threshold=snr_threshold,
    )

    # 5. Trojan companion dip hunter at L4/L5
    trojan_res = detect_trojan_companions_from_light_curve(
        lc=lc,
        period=period,
        t0=t0,
        duration_hours=duration_hours,
        snr_threshold=snr_threshold,
    )

    # 6. Bayesian posterior probability
    p_moon = compute_exomoon_posterior(
        ttv_snr=ttv_res.snr,
        phase_diff_deg=phase_res["phase_diff_deg"],
        shoulder_snr=shoulder_res.snr,
    )

    has_moon_cand = bool(
        ttv_res.snr >= snr_threshold
        and (
            phase_res["is_orthogonal"]
            or (shoulder_res.has_shoulder and p_moon > 0.5)
            or (p_moon >= 0.80)
        )
        and not phase_res["is_mmr_false_positive"]
    )

    return ExomoonPerturbationResult(
        target_id=lc.target_id,
        period=float(period),
        ttv_amplitudes=ttv_res.ttv_minutes,
        tdv_amplitudes=tdv_res.tdv_minutes,
        has_exomoon_candidate=has_moon_cand,
        ttv_snr=float(ttv_res.snr),
        orthogonal_phase_diff_deg=float(phase_res["phase_diff_deg"]),
        has_secondary_shoulder=bool(shoulder_res.has_shoulder),
        shoulder_snr=float(shoulder_res.snr),
        has_trojan_candidate=bool(trojan_res.has_trojan),
        trojan_lag_depth=float(trojan_res.depth),
        p_moon_posterior=float(p_moon),
    )


class ExomoonPerturbationDetector:
    """Class-based pipeline wrapper for gravitational perturbation detection."""

    def __init__(
        self,
        snr_threshold: float = 3.0,
        orthogonal_tolerance_deg: float = 15.0,
    ) -> None:
        self.snr_threshold = float(snr_threshold)
        self.orthogonal_tolerance_deg = float(orthogonal_tolerance_deg)

    def analyze(
        self,
        light_curve: LightCurveData,
        period: float,
        t0: float,
        duration_hours: Optional[float] = None,
        depth: Optional[float] = None,
    ) -> ExomoonPerturbationResult:
        """Run perturbation analysis on light curve."""
        return detect_perturbations(
            light_curve=light_curve,
            period=period,
            t0=t0,
            duration_hours=duration_hours,
            depth=depth,
            snr_threshold=self.snr_threshold,
            tolerance_deg=self.orthogonal_tolerance_deg,
        )


__all__ = [
    "barycentric_semi_major_axis",
    "barycentric_orbital_velocity",
    "satellite_semi_major_axis",
    "hill_radius",
    "critical_satellite_stability_radius",
    "barycentric_ttv_amplitude",
    "velocity_tdv_amplitude",
    "PhotodynamicPerturbationModel",
    "TTVExtractionResult",
    "extract_ttv",
    "extract_ttv_from_light_curve",
    "TDVExtractionResult",
    "extract_tdv",
    "extract_tdv_from_light_curve",
    "test_orthogonal_phase_invariant",
    "ShoulderDetectionResult",
    "detect_transit_shoulders",
    "detect_transit_shoulders_from_light_curve",
    "TrojanDetectionResult",
    "detect_trojan_companions",
    "detect_trojan_companions_from_light_curve",
    "compute_minimum_detectable_moon_mass",
    "compute_ttv_snr",
    "compute_sensitivity_grid",
    "compute_exomoon_posterior",
    "detect_perturbations",
    "ExomoonPerturbationDetector",
    "ExomoonPerturbationResult",
]
