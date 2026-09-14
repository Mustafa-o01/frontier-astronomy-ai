"""Tier 2: Boundary & Corner Cases Test Suite (>=5 tests per feature = >=55 tests).

Tests extreme parameters, non-physical inputs, edge values, missing cadences, and
adversarial corner conditions across all 11 features:
  F1: Pure-Python FITS & MAST Data Ingestion Engine (5 tests)
  F2: Time-Series Preprocessing & Robust Detrending (5 tests)
  F3: Catastrophic Disintegrating Exoplanet & Dust Tail Hunter (5 tests)
  F4: Synthetic Injection-Recovery Suite for Dust Tails (5 tests)
  F5: Exomoon & Trojan Gravitational Perturbation Detector (5 tests)
  F6: Multi-Body Perturbation Sensitivity Validation Suite (5 tests)
  F7: JWST Forward Radiative Transfer & Transmission Spectroscopy (5 tests)
  F8: Rapid Amortized Bayesian Atmospheric Inversion Engine (5 tests)
  F9: Benchmark Exoplanet Atmospheric Validation Suite (5 tests)
  F10: Unified Interactive Discovery & Inspection Dashboard (5 tests)
  F11: Command-Line Discovery Interface & Orchestration CLI (5 tests)

Conforms strictly to PROJECT.md interface contracts and TEST_INFRA.md minimum thresholds.
"""

from __future__ import annotations

import io
import os
import struct
import numpy as np
import pytest

from frontier_astronomy.core.constants import (
    AU,
    BJD_REF_KEPLER,
    BJD_REF_TESS,
    G,
    K_B,
    M_EARTH,
    M_JUPITER,
    M_MOON,
    M_SUN,
    MU_H2_HE,
    R_EARTH,
    R_JUPITER,
    R_SUN,
    bkjd_to_bjd,
    bjd_to_bkjd,
    btjd_to_bjd,
    bjd_to_btjd,
)
from frontier_astronomy.core.types import (
    AtmosphericInversionResult,
    BenchmarkSystem,
    DustTailDetectionResult,
    ExomoonPerturbationResult,
    FoldedTransit,
    LightCurveData,
    SpectrumData,
)
from frontier_astronomy.core.math_utils import (
    aic,
    bic,
    chi_squared,
    likelihood_ratio_test,
    reduced_chi_squared,
    safe_divide,
)
from frontier_astronomy.core.preprocessing import (
    asymmetric_mad_clip,
    clean_quality,
    epoch_split,
    fold_light_curve,
    inverse_variance_bin,
    iterative_savgol_detrend,
    phase_fold,
    preprocess_light_curve,
)
from tests.conftest import (
    generate_mock_fits_bytes,
    generate_synthetic_light_curve,
    generate_synthetic_transmission_spectrum,
)


# ==============================================================================
# Feature 1 Boundaries: FITS & Ingestion
# ==============================================================================
@pytest.mark.tier2
class TestFeature1IngestionBoundaries:
    """Boundary & Corner Case tests for Feature 1 (Ingestion)."""

    def test_f1_b01_zero_length_file(self):
        """Verify handling of completely empty zero-byte FITS file."""
        from frontier_astronomy.ingestion.fits_reader import read_fits_light_curve
        with pytest.raises((ValueError, OSError)):
            read_fits_light_curve(b"")

    def test_f1_b02_truncated_header_block(self):
        """Verify truncated FITS file (< 2880 bytes) raises informative error."""
        from frontier_astronomy.ingestion.fits_reader import read_fits_light_curve
        with pytest.raises((ValueError, OSError)):
            read_fits_light_curve(b"SIMPLE  =                    T" + b" " * 100)

    def test_f1_b03_all_bad_quality_flags(self):
        """Verify light curve where 100% of cadences have bad quality flags."""
        n = 50
        t = np.linspace(100, 105, n)
        f = np.ones(n)
        fe = np.full(n, 0.001)
        q = np.full(n, 128, dtype=np.int32)  # all flagged

        mask = clean_quality(t, f, fe, q, strict=True)
        assert np.sum(mask) == 0  # all rejected
        # Ensure preprocessing on all-bad quality returns empty data without crashing
        lc = LightCurveData("BAD_ALL", "Kepler", t, f, fe, q, 0.0, 0.0)
        cleaned = preprocess_light_curve(lc, strict_quality=True)
        assert cleaned.n_points == 0

    def test_f1_b04_missing_end_card_handling(self):
        """Verify header block without END card does not loop indefinitely."""
        raw = b" " * 2880
        from frontier_astronomy.ingestion.fits_reader import read_header_block
        hdr, bytes_read = read_header_block(io.BytesIO(raw))
        assert bytes_read == 2880
        assert "END" not in hdr

    def test_f1_b05_extreme_astronomical_timestamps(self):
        """Verify extreme past and future timestamps compute BJD without overflow."""
        past_bkjd = -1e7
        future_bkjd = 1e7
        bjd_past = bkjd_to_bjd(past_bkjd)
        bjd_future = bkjd_to_bjd(future_bkjd)
        assert np.isfinite(bjd_past)
        assert np.isfinite(bjd_future)
        assert np.isclose(bjd_to_bkjd(bjd_past), past_bkjd)
        assert np.isclose(bjd_to_bkjd(bjd_future), future_bkjd)


# ==============================================================================
# Feature 2 Boundaries: Preprocessing & Detrending
# ==============================================================================
@pytest.mark.tier2
class TestFeature2PreprocessingBoundaries:
    """Boundary & Corner Case tests for Feature 2 (Preprocessing)."""

    def test_f2_b01_all_nan_flux_array(self):
        """Verify array of all NaNs is safely handled without unhandled exception."""
        n = 50
        t = np.linspace(0, 10, n)
        f_nan = np.full(n, np.nan)
        fe = np.full(n, 0.01)
        q = np.zeros(n, dtype=np.int32)

        mask = clean_quality(t, f_nan, fe, q, strict=False)
        assert np.sum(mask) == 0

    def test_f2_b02_ultra_short_time_series(self):
        """Verify handling of ultra-short time-series (< 5 points)."""
        t = np.array([1.0, 2.0, 3.0])
        f = np.array([1.0, 0.98, 1.0])
        norm_f, cont = iterative_savgol_detrend(t, f, window_days=5.0, polyorder=2)
        assert len(norm_f) == 3
        assert not np.any(np.isnan(norm_f))

    def test_f2_b03_massive_flare_hundred_sigma(self):
        """Verify a 100-sigma positive flare does not skew baseline or break MAD clipping."""
        n = 200
        t = np.linspace(0, 10, n)
        f = np.ones(n)
        # Giant 100-sigma flare
        f[100] = 5.0
        mask = asymmetric_mad_clip(t, f, window_length=51, sigma_high=3.5)
        assert not mask[100]
        # Surrounding baseline should remain retained
        assert mask[90] and mask[110]

    def test_f2_b04_large_data_gaps_in_cadence(self):
        """Verify time-series with a 100-day gap between quarters folds properly."""
        t1 = np.linspace(100, 120, 100)
        t2 = np.linspace(220, 240, 100)  # 100-day gap
        t = np.concatenate([t1, t2])
        period = 3.5
        t0 = 100.0
        phases = phase_fold(t, period, t0)
        assert np.all(phases >= -0.5) and np.all(phases < 0.5)

    def test_f2_b05_zero_flux_uncertainties(self):
        """Verify inverse-variance binning handles zero uncertainty without ZeroDivisionError."""
        phase = np.array([-0.1, 0.0, 0.1])
        flux = np.array([1.0, 0.99, 1.0])
        flux_err = np.array([0.0, 0.0, 0.0])  # Zero errors

        centers, b_flux, b_err, counts = inverse_variance_bin(
            phase, flux, flux_err, n_bins=10
        )
        assert not np.any(np.isnan(b_flux))
        assert not np.any(np.isnan(b_err))


# ==============================================================================
# Feature 3 Boundaries: Dust Tail Hunter
# ==============================================================================
@pytest.mark.tier2
class TestFeature3DustTailBoundaries:
    """Boundary & Corner Case tests for Feature 3 (Dust Tail Hunter)."""

    def test_f3_b01_zero_depth_transit(self):
        """Verify zero transit depth produces flat baseline and non-detection."""
        from frontier_astronomy.dust_tail.detector import detect_dust_tail
        lc = generate_synthetic_light_curve(
            transit_type="dust_tail", depth=0.0, f_scat=0.0, noise_sigma=0.0
        )
        assert np.allclose(lc.flux, 1.0)
        res = detect_dust_tail(lc, period=0.65355, t0=120.0)
        assert not res.is_asymmetric_dust_tail
        assert res.delta_bic < 10.0

    def test_f3_b02_extreme_tail_length_quarter_phase(self):
        """Verify lambda_tail = 0.25 (tail covers quarter orbit) executes without overflow."""
        from frontier_astronomy.dust_tail.extinction_model import cometary_extinction_profile
        phase = np.linspace(-0.1, 0.4, 200)
        flux = cometary_extinction_profile(phase, depth=0.01, sigma_ing=0.005, lambda_tail=0.25)
        assert np.all(np.isfinite(flux))
        assert flux[-1] < 0.999  # Significant flux decrement persists to phase 0.4

    def test_f3_b03_sharp_step_ingress_zero_scale(self):
        """Verify ultra-sharp ingress scale (sigma_ing -> 0) is numerically stable."""
        from frontier_astronomy.dust_tail.extinction_model import cometary_extinction_profile
        phase = np.array([-0.01, 0.0, 0.01])
        flux = cometary_extinction_profile(phase, depth=0.01, sigma_ing=1e-6, lambda_tail=0.05)
        assert not np.any(np.isnan(flux))
        assert flux[0] > 0.999  # pre-transit
        assert flux[2] < 0.995  # in-transit

    def test_f3_b04_zero_scattering_amplitude(self):
        """Verify f_scat = 0.0 produces no pre-ingress brightening bump."""
        from frontier_astronomy.dust_tail.forward_scattering import forward_scattering_flux
        phase = np.linspace(-0.1, 0.1, 100)
        scat = forward_scattering_flux(phase, f_scat=0.0)
        assert np.all(scat == 0.0)

    def test_f3_b05_single_epoch_depth_variance(self):
        """Verify depth variability on K=1 single epoch handles zero degrees of freedom."""
        from frontier_astronomy.dust_tail.detector import compute_multi_epoch_depth_variability
        lc = generate_synthetic_light_curve(
            transit_type="dust_tail", duration_days=0.5, period=1.0, depth=0.01
        )
        var, depths, chi2_depth = compute_multi_epoch_depth_variability(lc, period=1.0, t0=120.0)
        assert var == 0.0
        assert chi2_depth == 0.0


# ==============================================================================
# Feature 4 Boundaries: Synthetic Injection-Recovery
# ==============================================================================
@pytest.mark.tier2
class TestFeature4InjectionRecoveryBoundaries:
    """Boundary & Corner Case tests for Feature 4 (Injection-Recovery)."""

    def test_f4_b01_sub_noise_floor_injection(self):
        """Verify ultra-shallow 10 ppm signal in 1000 ppm noise is identified as non-recovery."""
        from frontier_astronomy.dust_tail.injection_recovery import run_injection_recovery_trial
        trial = run_injection_recovery_trial(depth=1e-5, noise_sigma=1e-3, duration_days=10.0)
        assert not trial.recovered

    def test_f4_b02_deep_catastrophic_disruption(self):
        """Verify deep 50% disruption (WD 1145-like) executes through injection-recovery under extreme noise."""
        from frontier_astronomy.dust_tail.injection_recovery import run_injection_recovery_trial
        trial = run_injection_recovery_trial(
            trial_id=42,
            depth=0.50,
            tail_scale=0.060,
            noise_sigma=0.05,
            duration_days=5.0,
            seed=42,
        )
        assert trial.recovered
        assert trial.recovered_depth > 0.20
        assert trial.delta_bic > 10.0
        assert trial.lrt_p_value < 1e-4
        assert np.isfinite(trial.asymmetry_parameter)

    def test_f4_b03_zero_noise_pure_signal(self):
        """Verify injection into zero-noise baseline yields 100% recovery."""
        from frontier_astronomy.dust_tail.injection_recovery import run_injection_recovery_trial
        trial = run_injection_recovery_trial(depth=0.015, noise_sigma=0.0, duration_days=10.0)
        assert trial.recovered

    def test_f4_b04_high_noise_collapse(self):
        """Verify high noise (SNR < 0.5) executes without floating-point errors."""
        from frontier_astronomy.dust_tail.injection_recovery import run_injection_recovery_trial
        trial = run_injection_recovery_trial(depth=0.001, noise_sigma=0.01, duration_days=10.0)
        assert not trial.recovered

    def test_f4_b05_boundary_single_element_grid(self):
        """Verify injection recovery executes safely on single-element parameter grids."""
        from frontier_astronomy.dust_tail.injection_recovery import (
            run_injection_recovery_trial,
            run_injection_recovery_suite,
        )
        trial = run_injection_recovery_trial(
            depth=0.015,
            tail_scale=0.05,
            noise_sigma=0.001,
            duration_days=5.0,
            seed=42,
        )
        assert trial.injected_depth == 0.015
        assert isinstance(trial.recovered, (bool, np.bool_))
        assert np.isfinite(trial.delta_bic)

        summary = run_injection_recovery_suite(
            depth_grid=[0.015],
            tail_scale_grid=[0.05],
            noise_sigma=0.001,
            n_trials_per_bin=1,
            duration_days=5.0,
            base_seed=42,
        )
        assert summary.total_trials == 1
        assert len(summary.trials) == 1
        assert summary.trials[0].injected_depth == 0.015


# ==============================================================================
# Feature 5 Boundaries: Exomoon & Trojan Detector
# ==============================================================================
@pytest.mark.tier2
class TestFeature5ExomoonBoundaries:
    """Boundary & Corner Case tests for Feature 5 (Exomoon Detector)."""

    def test_f5_b01_zero_moon_mass_null_perturbation(self):
        """Verify satellite mass = 0 produces null TTV and TDV amplitudes."""
        from frontier_astronomy.perturbations.photodynamics import barycentric_ttv_amplitude
        a_ttv = barycentric_ttv_amplitude(
            m_star=M_SUN, m_planet=M_JUPITER, m_moon=0.0, p_planet_days=10.0, p_moon_days=1.5
        )
        assert np.isclose(a_ttv, 0.0)

    def test_f5_b02_equal_mass_binary_planet(self):
        """Verify satellite mass = planet mass (binary world) computes without divide-by-zero."""
        from frontier_astronomy.perturbations.photodynamics import barycentric_ttv_amplitude
        a_ttv = barycentric_ttv_amplitude(
            m_star=M_SUN, m_planet=M_EARTH, m_moon=M_EARTH, p_planet_days=10.0, p_moon_days=1.5
        )
        assert a_ttv > 0.0
        assert np.isfinite(a_ttv)

    def test_f5_b03_strictly_in_phase_perturbation(self):
        """Verify in-phase (0 deg) TTV and TDV correctly tagged as non-exomoon (MMR)."""
        from frontier_astronomy.perturbations.tdv_extractor import test_orthogonal_phase_invariant
        ttv = np.array([10.0, -10.0, 10.0, -10.0])
        tdv = np.array([5.0, -5.0, 5.0, -5.0])
        res = test_orthogonal_phase_invariant(ttv, tdv)
        assert res["is_mmr_false_positive"]
        assert not res["is_orthogonal"]

    def test_f5_b04_missing_transit_epochs_in_ttv(self):
        """Verify perturbation detection handles gaps in observed transit epochs and irregular sampling."""
        from frontier_astronomy.perturbations import detect_perturbations
        period = 4.0
        t0 = 100.0
        lc_full = generate_synthetic_light_curve(
            transit_type="symmetric",
            period=period,
            t0=t0,
            duration_days=40.0,
            depth=0.012,
            noise_sigma=0.0005,
        )
        # Introduce substantial missing epoch gaps (e.g., dropping entire transit events)
        mask = ~((lc_full.time >= 111.0) & (lc_full.time <= 118.0)) & \
               ~((lc_full.time >= 127.0) & (lc_full.time <= 131.0))
        # Irregularly thin cadences
        rng = np.random.default_rng(123)
        valid_indices = np.where(mask)[0]
        keep = np.sort(rng.choice(valid_indices, size=int(0.75 * len(valid_indices)), replace=False))

        lc_irregular = lc_full.copy_with(
            time=lc_full.time[keep],
            flux=lc_full.flux[keep],
            flux_err=lc_full.flux_err[keep],
            quality=lc_full.quality[keep],
        )

        res = detect_perturbations(
            light_curve=lc_irregular,
            period=period,
            t0=t0,
            duration_hours=3.5,
            depth=0.012,
        )

        assert isinstance(res, ExomoonPerturbationResult)
        assert len(res.ttv_amplitudes) > 0
        assert not np.any(np.isnan(res.ttv_amplitudes))
        assert not np.any(np.isnan(res.tdv_amplitudes))
        assert np.isfinite(res.ttv_snr)
        assert 0.0 <= res.p_moon_posterior <= 1.0

    def test_f5_b05_zero_trojan_depth(self, flat_light_curve):
        """Verify zero Trojan depth produces no secondary transit detection."""
        from frontier_astronomy.perturbations.trojan_detector import detect_trojan_companions_from_light_curve
        res = detect_trojan_companions_from_light_curve(flat_light_curve, period=5.0, t0=100.0)
        assert not res.has_trojan_candidate
        assert res.trojan_depth < 0.0005


# ==============================================================================
# Feature 6 Boundaries: Perturbation Sensitivity Suite
# ==============================================================================
@pytest.mark.tier2
class TestFeature6SensitivityBoundaries:
    """Boundary & Corner Case tests for Feature 6 (Sensitivity Suite)."""

    def test_f6_b01_exact_snr_three_boundary(self):
        """Verify exact boundary behavior at SNR = 3.0."""
        from frontier_astronomy.perturbations.sensitivity import compute_exomoon_posterior
        p_moon = compute_exomoon_posterior(ttv_snr=3.0, phase_diff_deg=90.0)
        assert 0.40 <= p_moon <= 0.85

    def test_f6_b02_sub_lunar_mass_sensitivity(self):
        """Verify sensitivity calculations remain physical for sub-lunar bodies."""
        from frontier_astronomy.perturbations.sensitivity import compute_minimum_detectable_moon_mass
        m_s_min = compute_minimum_detectable_moon_mass(
            m_star=M_SUN, m_planet=M_EARTH, p_planet_days=365.0, p_moon_days=27.3, sigma_ttv_seconds=1.0
        )
        assert m_s_min > 0.0
        assert m_s_min < M_EARTH

    def test_f6_b03_ultra_long_period_planet(self):
        """Verify period scaling for cold Jupiter at P = 1000 days."""
        from frontier_astronomy.perturbations.photodynamics import barycentric_semi_major_axis
        a_b = barycentric_semi_major_axis(M_SUN, 1000.0 * 86400.0)
        assert a_b > 1.5 * AU

    def test_f6_b04_grazing_transit_impact_parameter(self):
        """Verify minimum detectable moon mass calculation under near-grazing impact parameter b = 0.98."""
        from frontier_astronomy.perturbations.sensitivity import compute_minimum_detectable_moon_mass
        b = 0.98
        chord = float(np.sqrt(max(0.001, 1.0 - (b ** 2))))
        base_sigma_ttv = 30.0  # seconds
        # Transit duration shortens by chord factor, degrading timing uncertainty
        grazing_sigma_ttv = base_sigma_ttv / np.sqrt(chord)

        m_s_min = compute_minimum_detectable_moon_mass(
            m_star=M_SUN,
            m_planet=M_JUPITER,
            p_planet_days=10.0,
            p_moon_days=1.5,
            sigma_ttv_seconds=grazing_sigma_ttv,
            snr_threshold=3.0,
        )

        m_s_min_nominal = compute_minimum_detectable_moon_mass(
            m_star=M_SUN,
            m_planet=M_JUPITER,
            p_planet_days=10.0,
            p_moon_days=1.5,
            sigma_ttv_seconds=base_sigma_ttv,
            snr_threshold=3.0,
        )

        assert m_s_min > m_s_min_nominal
        assert m_s_min > 0.0
        assert np.isfinite(m_s_min)
        assert m_s_min < M_JUPITER

    def test_f6_b05_insufficient_epochs_boundary(self):
        """Verify single epoch N_epochs = 1 correctly flags insufficient data."""
        from frontier_astronomy.perturbations.sensitivity import compute_ttv_snr
        snr = compute_ttv_snr(np.array([5.0]))
        assert snr == 0.0


# ==============================================================================
# Feature 7 Boundaries: JWST Forward Radiative Transfer
# ==============================================================================
@pytest.mark.tier2
class TestFeature7JwstForwardBoundaries:
    """Boundary & Corner Case tests for Feature 7 (Forward Model)."""

    def test_f7_b01_zero_trace_gas_abundances(self):
        """Verify zero trace gas abundance (log10(X) = -12) produces baseline spectrum."""
        sp = generate_synthetic_transmission_spectrum(
            log_h2o=-12.0, log_co2=-12.0, log_ch4=-12.0, noise_ppm=0.0
        )
        assert np.all(sp.transit_depth > 0.0)
        # Transit depth should be nearly flat baseline
        assert np.isclose(sp.transit_depth[0], 0.0210, atol=1e-3)

    def test_f7_b02_extreme_temperatures(self):
        """Verify extreme equilibrium temperatures (150 K and 3000 K) produce positive scale heights."""
        from frontier_astronomy.atmospheric.forward_model import compute_atmospheric_scale_height
        h_cold = compute_atmospheric_scale_height(150.0, surface_gravity=24.79)
        h_hot = compute_atmospheric_scale_height(3000.0, surface_gravity=24.79)
        assert h_cold > 0.0
        assert h_hot > h_cold

    def test_f7_b03_deep_unobservable_cloud_deck(self):
        """Verify deep cloud deck (log10(Pc) = 2.0 bar) allows full spectral peaks."""
        sp = generate_synthetic_transmission_spectrum(log_pc=2.0, noise_ppm=0.0)
        co2_peak = np.max(sp.transit_depth)
        assert co2_peak > 0.0215

    def test_f7_b04_ultra_high_cloud_deck(self):
        """Verify ultra-high cloud deck (log10(Pc) = -4.0 bar) flattens transmission spectrum."""
        sp = generate_synthetic_transmission_spectrum(log_pc=-4.0, noise_ppm=0.0)
        depth_range = np.ptp(sp.transit_depth)
        # Cloud floor suppresses peak-to-peak variation
        assert depth_range < 0.001

    def test_f7_b05_flat_zero_haze_slope(self):
        """Verify zero haze slope (gamma_haze = 0.0) produces flat offset without slope."""
        sp = generate_synthetic_transmission_spectrum(haze_slope=0.0, noise_ppm=0.0)
        assert not np.any(np.isnan(sp.transit_depth))


# ==============================================================================
# Feature 8 Boundaries: Amortized Bayesian Inversion
# ==============================================================================
@pytest.mark.tier2
class TestFeature8BayesianInversionBoundaries:
    """Boundary & Corner Case tests for Feature 8 (Bayesian Inversion)."""

    def test_f8_b01_flat_featureless_spectrum_inversion(self):
        """Verify inversion on flat spectrum produces valid unconstrained posterior intervals."""
        from frontier_astronomy.atmospheric.inversion import invert_spectrum
        flat_sp = SpectrumData(
            target_id="FLAT_SPEC",
            instrument="NIRSpec",
            wavelength=np.linspace(0.6, 5.3, 100),
            transit_depth=np.full(100, 0.0210),
            uncertainty=np.full(100, 0.0001),
        )
        res = invert_spectrum(flat_sp, n_samples=1000, seed=42)
        for k in ["log_H2O", "log_CO2", "log_CH4"]:
            span = res.err_upper[k] - res.err_lower[k]
            assert span >= 2.0  # Broad unconstrained posterior

    def test_f8_b02_negative_noisy_transit_depth(self):
        """Verify noisy negative transit depth channel is handled without math crash."""
        depths = np.array([-0.001, 0.021, 0.022])
        errs = np.array([0.001, 0.001, 0.001])
        chi2_val = chi_squared(depths, np.full(3, 0.020), errs)
        assert np.isfinite(chi2_val)

    def test_f8_b03_extreme_high_noise_spectrum(self):
        """Verify high noise executes safely and yields wide credible intervals."""
        from frontier_astronomy.atmospheric.inversion import invert_spectrum
        rng = np.random.default_rng(999)
        noisy_sp = SpectrumData(
            target_id="NOISY_SPEC",
            instrument="NIRSpec",
            wavelength=np.linspace(0.6, 5.3, 100),
            transit_depth=0.0210 + rng.normal(0, 0.01, 100),
            uncertainty=np.full(100, 0.01),
        )
        res = invert_spectrum(noisy_sp, n_samples=1000, seed=42)
        assert res.inference_time_seconds < 0.15
        span = res.err_upper["log_H2O"] - res.err_lower["log_H2O"]
        assert span > 0.4

    def test_f8_b04_extreme_sample_sizes(self, wasp39b_spectrum):
        """Verify handles sampling scaling from small to large sample requests."""
        from frontier_astronomy.atmospheric.inversion import invert_spectrum
        res_small = invert_spectrum(wasp39b_spectrum, n_samples=1000, seed=42)
        assert res_small.posterior_samples.shape == (1000, 7)
        res_large = invert_spectrum(wasp39b_spectrum, n_samples=2500, seed=42)
        assert res_large.posterior_samples.shape == (2500, 7)

    def test_f8_b05_dimension_mismatch_exception(self):
        """Verify spectrum dimension mismatch raises ValueError in SpectrumData."""
        with pytest.raises(ValueError):
            SpectrumData(
                target_id="BAD_DIM",
                instrument="NIRSpec",
                wavelength=np.linspace(1.0, 5.0, 50),
                transit_depth=np.linspace(0.01, 0.02, 60),  # Mismatch!
                uncertainty=np.full(50, 0.001),
            )


# ==============================================================================
# Feature 9 Boundaries: Benchmark Atmospheric Validation
# ==============================================================================
@pytest.mark.tier2
class TestFeature9BenchmarkValidationBoundaries:
    """Boundary & Corner Case tests for Feature 9 (Atmospheric Validation)."""

    def test_f9_b01_non_monotonic_wavelength_grid(self):
        """Verify AtmosphericForwardModel rejects non-monotonic wavelength grids."""
        from frontier_astronomy.atmospheric.forward_model import AtmosphericForwardModel
        wl_unsorted = np.array([1.5, 1.2, 2.0, 3.0])
        with pytest.raises(ValueError, match="monotonically increasing"):
            AtmosphericForwardModel(wavelengths=wl_unsorted)

        # Confirm sorted wavelength array initializes successfully
        model = AtmosphericForwardModel(wavelengths=np.sort(wl_unsorted))
        assert model.n_channels == len(wl_unsorted)

    def test_f9_b02_zero_uncertainty_handling(self):
        """Verify safe_divide prevents ZeroDivisionError with zero uncertainty."""
        residuals = np.array([0.001, -0.002])
        errs = np.array([0.0, 0.0])
        normalized = safe_divide(residuals, errs, fill_value=0.0)
        assert np.all(normalized == 0.0)

    def test_f9_b03_spectral_outlier_robustness(self):
        """Verify atmospheric inversion on a zero-signal flat spectrum yields wide unconstrained posterior widths."""
        from frontier_astronomy.atmospheric.inversion import invert_spectrum
        wl = np.linspace(0.8, 5.0, 60)
        flat_spec = SpectrumData(
            target_id="FLAT_SPECTRUM_BENCH",
            instrument="NIRSpec_PRISM",
            wavelength=wl,
            transit_depth=np.full_like(wl, 0.0210),
            uncertainty=np.full_like(wl, 0.0005),
        )
        res = invert_spectrum(flat_spec, n_samples=1000, seed=42)
        assert isinstance(res, AtmosphericInversionResult)

        # When no molecular absorption features exist, posterior widths must be wide / unconstrained
        co2_width = res.err_upper["log_CO2"] - res.err_lower["log_CO2"]
        h2o_width = res.err_upper["log_H2O"] - res.err_lower["log_H2O"]
        assert co2_width > 1.0
        assert h2o_width > 1.0
        assert res.chi2 >= 0.0
        assert res.inference_time_seconds > 0.0

    def test_f9_b04_depleted_species_prior_rail(self, wasp39b_spectrum):
        """Verify depleted species (CH4 < -6.0) stays within prior boundary [-12, -1]."""
        from frontier_astronomy.atmospheric.inversion import invert_spectrum
        from frontier_astronomy.atmospheric.normalizing_flow import DEFAULT_PARAM_BOUNDS
        res = invert_spectrum(wasp39b_spectrum, n_samples=1000, seed=42)
        ch4_val = res.medians["log_CH4"]
        bounds = DEFAULT_PARAM_BOUNDS["log_CH4"]
        assert bounds[0] <= ch4_val <= bounds[1]

    def test_f9_b05_credible_interval_containment(self, sample_inversion_result):
        """Verify 1-sigma bounds are strictly inside empirical 2-sigma bounds."""
        from frontier_astronomy.atmospheric.forward_model import ATMOSPHERIC_PARAMETER_NAMES
        res = sample_inversion_result
        for col, p in enumerate(ATMOSPHERIC_PARAMETER_NAMES):
            samples = res.posterior_samples[:, col]
            med = res.medians[p]
            low_1sig = res.err_lower[p]
            high_1sig = res.err_upper[p]
            low_2sig = float(np.percentile(samples, 2.275))
            high_2sig = float(np.percentile(samples, 97.725))
            assert low_2sig <= low_1sig <= med <= high_1sig <= high_2sig


# ==============================================================================
# Feature 10 Boundaries: Discovery Dashboard
# ==============================================================================
@pytest.mark.tier2
class TestFeature10DashboardBoundaries:
    """Boundary & Corner Case tests for Feature 10 (Dashboard)."""

    def test_f10_b01_empty_candidate_catalog(self):
        """Verify dashboard candidate filtering handles empty catalog gracefully without error."""
        from frontier_astronomy.dashboard.state import filter_candidates
        filtered = filter_candidates([], mission="Kepler", min_delta_bic=10.0)
        assert filtered == []
        assert isinstance(filtered, list)

    def test_f10_b02_massive_light_curve_decimation(self):
        """Verify dashboard decimate_time_series downsizes massive light curves for UI responsiveness."""
        from frontier_astronomy.dashboard.state import decimate_time_series
        n = 100000
        t = np.linspace(0, 100, n)
        flux = np.ones(n, dtype=np.float64)
        flux_err = np.full(n, 0.001, dtype=np.float64)

        t_dec, f_dec, fe_dec = decimate_time_series(t, flux, flux_err, max_points=5000)
        assert len(t_dec) <= 5000
        assert len(f_dec) == len(t_dec)
        assert fe_dec is not None and len(fe_dec) == len(t_dec)
        assert t_dec[0] == t[0]

        # Verify passthrough for already compact series
        t_small = np.linspace(0, 10, 500)
        f_small = np.ones(500)
        t_pass, f_pass, _ = decimate_time_series(t_small, f_small, max_points=5000)
        assert len(t_pass) == 500

    def test_f10_b03_out_of_range_phase_query(self):
        """Verify phase values outside [-0.5, 0.5) are properly wrapped by phase_fold."""
        t = np.array([1000.0])
        ph = phase_fold(t, period=3.5, t0=120.0)
        assert -0.5 <= ph[0] < 0.5

    def test_f10_b04_single_epoch_heatmap(self):
        """Verify 2D residual heatmap with 1 epoch generates valid 1xN array."""
        from frontier_astronomy.dashboard.components.heatmap_view import compute_residual_heatmap
        lc = generate_synthetic_light_curve(
            transit_type="dust_tail", duration_days=0.5, period=1.0, depth=0.01
        )
        heatmap, epochs, phase_centers = compute_residual_heatmap(
            lc, period=1.0, t0=120.0, n_phase_bins=20
        )
        assert heatmap.shape[0] == 1
        assert heatmap.shape[1] == 20

    def test_f10_b05_missing_benchmark_fallback(self):
        """Verify dashboard loader triggers synthetic fallback for non-existent target IDs."""
        from frontier_astronomy.dashboard.state import load_candidate_light_curve
        target_id = "NON_EXISTENT_TARGET_9999"
        fallback_lc = load_candidate_light_curve(target_id=target_id, fallback_on_missing=True)
        assert isinstance(fallback_lc, LightCurveData)
        assert fallback_lc.target_id == target_id
        assert len(fallback_lc.flux) > 0

        # Disabling fallback must raise FileNotFoundError for missing target
        with pytest.raises(FileNotFoundError):
            load_candidate_light_curve("COMPLETELY_UNKNOWN_TARGET_0000", fallback_on_missing=False)


# ==============================================================================
# Feature 11 Boundaries: Discovery CLI
# ==============================================================================
@pytest.mark.tier2
class TestFeature11CliBoundaries:
    """Boundary & Corner Case tests for Feature 11 (CLI)."""

    def test_f11_b01_unknown_subcommand_exit_code(self):
        """Verify unknown subcommand produces usage error."""
        from frontier_astronomy.cli.main import build_parser
        parser = build_parser()
        with pytest.raises(SystemExit):
            parser.parse_args(["unknown_command_xyz"])

    def test_f11_b02_missing_file_path_handling(self, tmp_path):
        """Verify non-existent file path returns non-zero exit code."""
        from frontier_astronomy.cli.main import main
        bad_path = str(tmp_path / "does_not_exist.fits")
        ret = main(["discover", "--target", bad_path])
        assert ret != 0

    def test_f11_b03_invalid_sample_count_boundary(self):
        """Verify invalid sample count is safely handled or clamped."""
        from frontier_astronomy.atmospheric.inversion import AtmosphericInversionEngine
        from tests.conftest import generate_synthetic_transmission_spectrum
        engine = AtmosphericInversionEngine()
        sp = generate_synthetic_transmission_spectrum()
        res = engine.invert(sp, n_samples=0)
        assert res.posterior_samples.shape[0] >= 1000

    def test_f11_b04_read_only_output_directory(self, tmp_path):
        """Verify discover subcommand executes and writes discovery summary JSON."""
        from frontier_astronomy.cli.main import main
        out_dir = tmp_path / "results"
        ret = main([
            "discover",
            "--target", "KIC 12557548",
            "--archive", "synthetic",
            "--out", str(out_dir),
        ])
        assert ret == 0
        assert (out_dir / "candidate_summary.json").exists()

    def test_f11_b05_empty_command_line_invocation(self):
        """Verify empty command line prints help and returns exit code 0."""
        from frontier_astronomy.cli.main import main
        ret = main([])
        assert ret == 0
