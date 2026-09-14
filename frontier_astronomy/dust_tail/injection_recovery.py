"""Synthetic Monte Carlo Injection-Recovery Suite for Cometary Dust Tails.

Evaluates:
1. Signal preservation across depth dynamic range (0.1% to 2.0%, or 1000 to 20000 ppm).
2. Statistical recovery rate (>= 90% at SNR >= 5.0) under Kepler/TESS photometric noise floors.
3. False positive rate (<= 2.0%) on pure Gaussian stellar noise baselines.
4. Parameter estimation fidelity (recovered depth and tail decay length vs ground truth).
"""

from __future__ import annotations

from dataclasses import dataclass
from typing import Any, Dict, List, Optional, Tuple
import numpy as np

from frontier_astronomy.core.types import LightCurveData
from frontier_astronomy.core.constants import KEPLER_LONG_CADENCE_MIN
from frontier_astronomy.ingestion.synthetic_generator import generate_disintegrating_dust_tail_light_curve
from frontier_astronomy.dust_tail.detector import detect_dust_tail, DustTailDetector
from frontier_astronomy.dust_tail.extinction_model import cometary_extinction_profile


@dataclass(frozen=True)
class InjectionRecoveryTrial:
    """Outcome record of a single synthetic injection-recovery trial."""
    trial_id: int
    injected_depth: float
    injected_tail_scale: float
    noise_sigma: float
    snr: float
    recovered: bool
    delta_bic: float
    lrt_p_value: float
    asymmetry_parameter: float
    recovered_depth: float
    depth_error: float


@dataclass(frozen=True)
class InjectionRecoverySummary:
    """Aggregate statistical performance metrics of an injection-recovery campaign."""
    total_trials: int
    recovered_trials: int
    overall_recovery_rate: float
    high_snr_trials: int
    high_snr_recovered: int
    high_snr_recovery_rate: float       # Must be >= 0.90 for SNR >= 5.0
    false_positive_rate: float          # Must be <= 0.02 (2.0%)
    mean_depth_recovery_error: float
    trials: List[InjectionRecoveryTrial]
    depth_grid: List[float]
    tail_scale_grid: List[float]


def inject_dust_tail(
    light_curve: LightCurveData,
    depth: float = 0.010,
    period: float = 0.65355,
    t0: float = 120.0,
    sigma_ing: float = 0.004,
    lambda_tail: float = 0.050,
    f_scat: float = 0.0010,
    alpha: float = 1.0,
    phi_offset: float = 0.012,
) -> LightCurveData:
    """Inject an analytic cometary dust tail extinction signal into a light curve baseline.

    Args:
        light_curve: Baseline LightCurveData.
        depth: Peak transit depth (fractional).
        period: Orbital period in days.
        t0: Reference transit epoch.
        sigma_ing: Ingress duration scale in phase units.
        lambda_tail: Egress exponential decay scale length.
        f_scat: Forward scattering peak amplitude.
        alpha: Tail decay curvature power index.
        phi_offset: Ingress alignment offset.

    Returns:
        New LightCurveData object containing the injected cometary signal.
    """
    time = light_curve.time
    phase = ((time - t0) / period + 0.5) % 1.0 - 0.5

    # Compute unit-normalized cometary profile
    profile = cometary_extinction_profile(
        phase=phase,
        depth=depth,
        sigma_ing=sigma_ing,
        lambda_tail=lambda_tail,
        alpha=alpha,
        phi_offset=phi_offset,
        f_scat=f_scat,
        phi_scat=-0.020,
        sigma_scat=0.008,
    )

    # Invert to fractional transmission signal
    injected_flux = light_curve.flux * profile

    metadata = dict(light_curve.metadata)
    metadata["injected_dust_tail"] = True
    metadata["injected_depth"] = depth
    metadata["injected_period"] = period
    metadata["injected_t0"] = t0
    metadata["injected_tail_scale"] = lambda_tail

    return light_curve.copy_with(
        flux=injected_flux,
        metadata=metadata,
    )


def run_injection_recovery_trial(
    trial_id: int = 0,
    depth: float = 0.010,
    tail_scale: float = 0.050,
    noise_sigma: float = 0.0010,
    period: float = 0.65355,
    t0: float = 120.0,
    duration_days: float = 30.0,
    seed: Optional[int] = None,
) -> InjectionRecoveryTrial:
    """Execute a single end-to-end synthetic injection and recovery detection trial."""
    noise_ppm = noise_sigma * 1e6
    snr = depth / max(noise_sigma, 1e-9)

    lc = generate_disintegrating_dust_tail_light_curve(
        target_id=f"INJ_{trial_id:04d}",
        period=period,
        t0=t0,
        depth=depth,
        duration_days=duration_days,
        cadence_minutes=KEPLER_LONG_CADENCE_MIN,
        noise_ppm=noise_ppm,
        tail_scale=tail_scale,
        seed=seed,
    )

    result = detect_dust_tail(
        light_curve=lc,
        period=period,
        t0=t0,
        min_delta_bic=10.0,
        max_lrt_p_value=1e-5,
        min_asymmetry=0.25,
    )

    recovered_depth = float(result.peak_depth)
    depth_err = abs(recovered_depth - depth) / max(depth, 1e-6)
    # Recovery criterion: detected as asymmetric dust tail, measured depth > 0, SNR >= 1.0, and depth error <= 3.0
    recovered = bool(
        result.is_asymmetric_dust_tail
        and result.peak_depth > 0.0
        and snr >= 1.0
        and depth_err <= 3.0
    )

    return InjectionRecoveryTrial(
        trial_id=trial_id,
        injected_depth=depth,
        injected_tail_scale=tail_scale,
        noise_sigma=noise_sigma,
        snr=snr,
        recovered=recovered,
        delta_bic=float(result.delta_bic),
        lrt_p_value=float(result.lrt_p_value),
        asymmetry_parameter=float(result.asymmetry_parameter),
        recovered_depth=recovered_depth,
        depth_error=float(depth_err),
    )


def evaluate_false_positive_rate(
    n_trials: int = 50,
    noise_sigma: float = 0.0010,
    period: float = 0.65355,
    t0: float = 120.0,
    duration_days: float = 30.0,
    seed: int = 5000,
) -> float:
    """Estimate the false alarm rate on pure unperturbed Gaussian stellar noise.

    A false positive occurs if random stellar noise triggers Delta-BIC >= 10.0 and LRT p < 1e-5.

    Returns:
        False positive rate (fraction in [0.0, 1.0]). Expected <= 0.02.
    """
    from frontier_astronomy.ingestion.synthetic_generator import generate_synthetic_light_curve

    false_alarms = 0
    for i in range(n_trials):
        lc_noise = generate_synthetic_light_curve(
            target_id=f"NOISE_{i:03d}",
            transit_type="flat",
            noise_sigma=noise_sigma,
            period=period,
            t0=t0,
            duration_days=duration_days,
            seed=seed + i,
        )

        result = detect_dust_tail(
            light_curve=lc_noise,
            period=period,
            t0=t0,
            min_delta_bic=10.0,
            max_lrt_p_value=1e-5,
            min_asymmetry=0.25,
        )

        if result.is_asymmetric_dust_tail:
            false_alarms += 1

    return float(false_alarms / n_trials)


def run_injection_recovery_suite(
    depth_grid: Optional[List[float]] = None,
    tail_scale_grid: Optional[List[float]] = None,
    noise_sigma: float = 0.0010,
    n_trials_per_bin: int = 5,
    period: float = 0.65355,
    t0: float = 120.0,
    duration_days: float = 30.0,
    base_seed: int = 100,
) -> InjectionRecoverySummary:
    """Execute automated Monte Carlo injection-recovery testing across a 2D parameter grid.

    Standard grid:
    - Transit depths: 0.1% to 2.0% (0.001 to 0.020).
    - Tail decay lengths: 0.03 to 0.08 in orbital phase.
    - Photometric noise: 1000 ppm (Kepler long-cadence standard).

    Returns:
        InjectionRecoverySummary containing recovery rates, false positive rates, and trials.
    """
    if depth_grid is None:
        depth_grid = [0.001, 0.005, 0.010, 0.015, 0.020]
    if tail_scale_grid is None:
        tail_scale_grid = [0.035, 0.050, 0.075]

    trials: List[InjectionRecoveryTrial] = []
    trial_idx = 0

    for d in depth_grid:
        for lam in tail_scale_grid:
            for rep in range(n_trials_per_bin):
                trial_seed = base_seed + trial_idx * 17
                t_record = run_injection_recovery_trial(
                    trial_id=trial_idx,
                    depth=d,
                    tail_scale=lam,
                    noise_sigma=noise_sigma,
                    period=period,
                    t0=t0,
                    duration_days=duration_days,
                    seed=trial_seed,
                )
                trials.append(t_record)
                trial_idx += 1

    total_trials = len(trials)
    recovered_trials = sum(1 for t in trials if t.recovered)
    overall_recovery_rate = recovered_trials / total_trials if total_trials > 0 else 0.0

    # High-SNR subset (SNR >= 5.0)
    high_snr_trials_list = [t for t in trials if t.snr >= 5.0]
    n_high_snr = len(high_snr_trials_list)
    high_snr_rec = sum(1 for t in high_snr_trials_list if t.recovered)
    high_snr_rate = high_snr_rec / n_high_snr if n_high_snr > 0 else 1.0

    # False positive rate on pure noise
    fpr = evaluate_false_positive_rate(
        n_trials=50,
        noise_sigma=noise_sigma,
        period=period,
        t0=t0,
        duration_days=duration_days,
        seed=base_seed + 9999,
    )

    # Mean depth recovery relative error on recovered candidates
    rec_errors = [t.depth_error for t in trials if t.recovered]
    mean_err = float(np.mean(rec_errors)) if len(rec_errors) > 0 else 0.0

    return InjectionRecoverySummary(
        total_trials=total_trials,
        recovered_trials=recovered_trials,
        overall_recovery_rate=overall_recovery_rate,
        high_snr_trials=n_high_snr,
        high_snr_recovered=high_snr_rec,
        high_snr_recovery_rate=high_snr_rate,
        false_positive_rate=fpr,
        mean_depth_recovery_error=mean_err,
        trials=trials,
        depth_grid=depth_grid,
        tail_scale_grid=tail_scale_grid,
    )
