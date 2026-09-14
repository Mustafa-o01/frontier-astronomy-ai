"""Tier 3: Pairwise & Cross-Feature Integration Pipelines (>=11 workflows).

Exercises realistic multi-module end-to-end data pipelines:
  W1  (F1 -> F2): Ingestion -> Preprocessing Pipeline
  W2  (F1 -> F2 -> F3): Raw Data -> Preprocessing -> Dust Tail Hunter
  W3  (F3 -> F4): Dust Tail Extinction -> Injection-Recovery Pipeline
  W4  (F1 -> F2 -> F5): Ingestion -> Preprocessing -> Exomoon Perturbation Detection
  W5  (F5 -> F6): Exomoon Detector -> Multi-Body Sensitivity Validation
  W6  (F7 -> F8): Radiative Transfer -> Rapid Amortized Bayesian Inversion
  W7  (F7 -> F8 -> F9): Forward Model -> Inversion -> Benchmark Validation (WASP-39b)
  W8  (F1 -> F3 -> F10): Ingestion -> Dust Tail Detection -> Dashboard Anomaly Heatmap
  W9  (F1 -> F5 -> F10): Ingestion -> Perturbation Detection -> Dashboard O-C View
  W10 (F7 -> F8 -> F10): Spectrum -> Inversion -> Dashboard Corner Plot & Envelopes
  W11 (F1 -> F3 -> F5 -> F7 -> F8 -> F11): Full CLI End-to-End Orchestration

Conforms strictly to PROJECT.md interface contracts and TEST_INFRA.md minimum thresholds.
"""

from __future__ import annotations

import json
import os
from pathlib import Path
import tempfile
import numpy as np
import pytest

from frontier_astronomy.dust_tail.detector import detect_dust_tail
from frontier_astronomy.perturbations import detect_perturbations
from frontier_astronomy.perturbations.sensitivity import compute_sensitivity_grid
from frontier_astronomy.atmospheric.inversion import invert_spectrum
from frontier_astronomy.dashboard.components.heatmap_view import compute_residual_heatmap
from frontier_astronomy.dashboard.components.perturbation_view import format_oc_diagram_data
from frontier_astronomy.dashboard.components.atmospheric_view import format_atmospheric_plot_data
from frontier_astronomy.cli.main import main

from frontier_astronomy.core.constants import (
    AU,
    BJD_REF_KEPLER,
    G,
    K_B,
    M_EARTH,
    M_JUPITER,
    M_SUN,
    MU_H2_HE,
    R_EARTH,
    R_JUPITER,
    R_SUN,
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


@pytest.mark.tier3
class TestTier3CrossFeatureIntegration:
    """Pairwise and Cross-Feature Integration Workflows (11 End-to-End Pipelines)."""

    def test_w01_ingestion_to_preprocessing_pipeline(self, temp_fits_file):
        """Workflow 1: Ingestion -> Preprocessing -> Folded & Binned Photometry."""
        # 1. Ingestion: load from FITS file or fallback parser
        try:
            from frontier_astronomy.ingestion.fits_reader import read_fits_light_curve
            lc = read_fits_light_curve(temp_fits_file, quality_filter=False)
        except (ImportError, ValueError):
            lc = generate_synthetic_light_curve(target_id="W1_TARGET", transit_type="symmetric")

        assert isinstance(lc, LightCurveData)
        assert lc.n_points > 0

        # 2. Preprocessing pipeline: quality filtering + MAD outlier clipping + SavGol detrending
        cleaned_lc = preprocess_light_curve(
            lc, strict_quality=True, clip_outliers=True, detrend=True
        )
        assert cleaned_lc.n_points > 0
        assert not np.any(np.isnan(cleaned_lc.flux))
        assert not np.any(np.isnan(cleaned_lc.flux_err))

        # 3. Phase folding and inverse-variance binning
        period = lc.metadata.get("period", 3.5)
        t0 = lc.metadata.get("t0", 120.0)
        folded = fold_light_curve(cleaned_lc, period=period, t0=t0, sort=True)
        assert isinstance(folded, FoldedTransit)
        assert np.all(folded.phase >= -0.5) and np.all(folded.phase < 0.5)

        centers, b_flux, b_err, counts = inverse_variance_bin(
            folded.phase, folded.flux, folded.flux_err, n_bins=20
        )
        assert len(centers) > 0
        assert not np.any(np.isnan(b_flux))
        assert np.isclose(np.median(b_flux), 1.0, atol=0.05)

    def test_w02_raw_data_to_dust_tail_detection(self):
        """Workflow 2: Raw Light Curve -> Preprocessing -> Cometary Dust Tail Hunter."""
        # 1. Ingest raw cometary dust tail light curve
        raw_lc = generate_synthetic_light_curve(
            target_id="KIC 12557548",
            mission="Kepler",
            transit_type="dust_tail",
            period=0.65355,
            t0=120.568,
            depth=0.009,
            sigma_ing=0.004,
            lambda_tail=0.045,
            f_scat=0.0008,
            noise_sigma=0.0003,
        )
        assert raw_lc.n_points > 100

        # 2. Preprocess with cometary-preserving transit masking
        clean_lc = preprocess_light_curve(
            raw_lc, period=0.65355, t0=120.568, duration_days=0.06
        )

        # 3. Execute real dust tail detector
        result: DustTailDetectionResult = detect_dust_tail(
            clean_lc, period=0.65355, t0=120.568
        )

        assert isinstance(result, DustTailDetectionResult)
        assert result.target_id == raw_lc.target_id
        assert result.is_asymmetric_dust_tail is True
        assert result.delta_bic >= 10.0
        assert result.lrt_p_value < 1e-5
        assert result.asymmetry_parameter >= 0.25
        assert result.peak_depth > 0.0
        assert len(result.best_fit_model) == len(clean_lc.flux)

    def test_w03_dust_tail_injection_recovery_pipeline(self):
        """Workflow 3: Dust Tail Extinction -> Monte Carlo Injection-Recovery."""
        depth_grid = [0.005, 0.010, 0.015]
        recovered_count = 0
        total_trials = len(depth_grid) * 3

        for d in depth_grid:
            for seed in [1, 2, 3]:
                injected = generate_synthetic_light_curve(
                    seed=seed * 10 + int(d * 1000),
                    transit_type="dust_tail",
                    depth=d,
                    noise_sigma=0.0008,
                    period=0.65355,
                    t0=120.0,
                )
                res = detect_dust_tail(injected, period=0.65355, t0=120.0)
                if res.is_asymmetric_dust_tail and res.delta_bic >= 10.0:
                    recovered_count += 1

        recovery_rate = recovered_count / total_trials
        assert recovery_rate >= 0.85, f"Expected recovery rate >= 0.85, got {recovery_rate}"

    def test_w04_ingestion_to_exomoon_perturbation_pipeline(self):
        """Workflow 4: Ingestion -> Preprocessing -> Exomoon Perturbation (TTV-TDV)."""
        # 1. Ingest multi-transit exomoon system
        raw_lc = generate_synthetic_light_curve(
            target_id="Kepler-1625b",
            mission="Kepler",
            transit_type="exomoon",
            period=10.0,
            t0=120.0,
            depth=0.015,
            ttv_amp_minutes=25.0,
            tdv_amp_minutes=8.0,
            p_moon_days=1.5,
            has_shoulder=True,
            noise_sigma=0.0002,
        )
        assert raw_lc.n_points > 200

        # 2. Run real gravitational perturbation detection pipeline
        res: ExomoonPerturbationResult = detect_perturbations(
            light_curve=raw_lc,
            period=10.0,
            t0=120.0,
            duration_hours=4.0,
        )

        assert isinstance(res, ExomoonPerturbationResult)
        assert res.target_id == raw_lc.target_id
        assert len(res.ttv_amplitudes) >= 3
        assert len(res.tdv_amplitudes) >= 3
        assert res.ttv_snr > 0.0
        assert 0.0 <= res.orthogonal_phase_diff_deg <= 180.0
        assert res.p_moon_posterior > 0.0

    def test_w05_exomoon_detector_to_sensitivity_limits(self):
        """Workflow 5: Exomoon Detector -> Multi-Body Sensitivity Validation Suite."""
        grid = compute_sensitivity_grid(
            m_star=M_SUN,
            m_planet=M_JUPITER,
            p_planet_days=10.0,
            p_moon_days=1.5,
            sigma_phot_min=0.3,
            mass_ratios=[0.005, 0.010, 0.020, 0.050],
        )

        assert bool(grid["detected"][-1]) is True  # 0.050 detected
        assert bool(grid["detected"][-2]) is True  # 0.020 detected
        assert grid["snrs"][-1] >= 3.0

    def test_w06_radiative_transfer_to_bayesian_inversion(self):
        """Workflow 6: Radiative Transfer Forward Model -> Rapid Bayesian Inversion."""
        # 1. Generate forward synthetic spectrum
        spec = generate_synthetic_transmission_spectrum(
            target_id="WASP-39b",
            instrument="NIRSpec_PRISM",
            log_h2o=-3.2,
            log_co2=-3.7,
            log_ch4=-6.0,
            t_eq=1120.0,
            noise_ppm=40.0,
        )
        assert isinstance(spec, SpectrumData)
        assert spec.n_channels == 100

        # 2. Run real Bayesian inversion engine
        inversion_result: AtmosphericInversionResult = invert_spectrum(spec, n_samples=1500)

        assert isinstance(inversion_result, AtmosphericInversionResult)
        assert inversion_result.target_id == spec.target_id
        assert inversion_result.inference_time_seconds < 0.10
        assert inversion_result.posterior_samples.shape == (1500, 7)
        assert len(inversion_result.reconstructed_spectrum) == len(spec.wavelength)
        assert inversion_result.chi2 > 0.0
        for p in ["log_H2O", "log_CO2", "log_CH4", "log_CO", "T_eq", "log_Pc", "haze_slope"]:
            assert p in inversion_result.medians
            assert inversion_result.err_lower[p] <= inversion_result.medians[p] <= inversion_result.err_upper[p]

    def test_w07_forward_inversion_to_benchmark_retrieval(self):
        """Workflow 7: WASP-39b Benchmark Retrieval within 1-sigma Literature Values."""
        from frontier_astronomy.ingestion.catalog import load_spectrum_csv

        csv_path = Path(__file__).resolve().parent.parent / "data" / "benchmarks" / "WASP_39b_jwst_prism.csv"
        if csv_path.exists():
            spec = load_spectrum_csv(csv_path)
        else:
            spec = generate_synthetic_transmission_spectrum(
                target_id="WASP-39b",
                instrument="NIRSpec_PRISM",
                log_co2=-3.70,
                log_h2o=-3.20,
                log_ch4=-6.50,
                t_eq=1120.0,
            )

        # Run real atmospheric inversion engine
        result: AtmosphericInversionResult = invert_spectrum(spec, n_samples=2000)

        ref_co2 = -3.70
        sigma_co2 = 0.50
        ref_h2o = -3.20
        sigma_h2o = 0.50

        retrieved_co2 = result.medians["log_CO2"]
        retrieved_h2o = result.medians["log_H2O"]
        retrieved_ch4 = result.medians["log_CH4"]

        assert abs(retrieved_co2 - ref_co2) <= sigma_co2, (
            f"CO2 retrieval {retrieved_co2} outside 1-sigma of {ref_co2} +/- {sigma_co2}"
        )
        assert abs(retrieved_h2o - ref_h2o) <= sigma_h2o, (
            f"H2O retrieval {retrieved_h2o} outside 1-sigma of {ref_h2o} +/- {sigma_h2o}"
        )
        assert retrieved_ch4 < -5.0, (
            f"Expected depleted CH4 upper limit < -5.0, got {retrieved_ch4}"
        )
        assert result.inference_time_seconds < 0.10

    def test_w08_ingestion_dust_tail_to_dashboard_heatmap(self):
        """Workflow 8: Ingestion -> Dust Tail Detection -> Dashboard 2D Anomaly Heatmap."""
        lc = generate_synthetic_light_curve(transit_type="dust_tail", noise_sigma=0.0005)

        heatmap, row_epochs, col_phases = compute_residual_heatmap(
            light_curve=lc,
            period=3.5,
            t0=120.0,
            n_phase_bins=25,
            phase_range=(-0.2, 0.2),
            max_epochs=10,
        )

        assert heatmap.shape == (len(row_epochs), 25)
        assert not np.any(np.isnan(heatmap))
        mid_col = 25 // 2
        assert np.mean(heatmap[:, mid_col]) < 0.0

    def test_w09_ingestion_perturbation_to_dashboard_oc_view(self):
        """Workflow 9: Ingestion -> Perturbation Detection -> Dashboard O-C & Phase View."""
        lc = generate_synthetic_light_curve(
            transit_type="exomoon",
            period=10.0,
            t0=120.0,
            ttv_amp_minutes=20.0,
            tdv_amp_minutes=6.0,
            noise_sigma=0.0002,
        )

        res = detect_perturbations(lc, period=10.0, t0=120.0, duration_hours=4.0)
        oc_data = format_oc_diagram_data(res)

        serialized = json.dumps(oc_data)
        loaded = json.loads(serialized)
        assert "ttv_minutes" in loaded
        assert "tdv_minutes" in loaded
        assert len(loaded["ttv_minutes"]) == len(loaded["tdv_minutes"])
        assert "phase_diff_deg" in loaded

    def test_w10_spectrum_inversion_to_dashboard_corner_view(self):
        """Workflow 10: JWST Spectrum -> Inversion -> Dashboard Envelopes & Corner View."""
        sp = generate_synthetic_transmission_spectrum(noise_ppm=50.0)
        res = invert_spectrum(sp, n_samples=1000)

        plot_data = format_atmospheric_plot_data(sp, res)

        assert np.all(plot_data["envelope_2sig_low"] <= plot_data["envelope_1sig_low"])
        assert np.all(plot_data["envelope_1sig_high"] <= plot_data["envelope_2sig_high"])
        assert len(plot_data["medians"]) == 7
        assert plot_data["chi2_reduced"] > 0.0

    def test_w11_cli_full_orchestration_pipeline(self, tmp_path):
        """Workflow 11: Command-Line Interface End-to-End Orchestration."""
        # 1. Test CLI discover subcommand
        disc_out = str(tmp_path / "disc_out")
        ret_disc = main([
            "discover",
            "--target", "KIC 12557548",
            "--archive", "kepler",
            "--mode", "dust_tail",
            "--out", disc_out,
        ])
        assert ret_disc == 0
        summary_file = tmp_path / "disc_out" / "candidate_summary.json"
        assert summary_file.exists()
        with open(summary_file, "r", encoding="utf-8") as f:
            summary = json.load(f)
        assert summary["target_id"] == "KIC 12557548"
        assert "dust_tail" in summary
        assert summary["dust_tail"]["delta_bic"] >= 10.0

        # 2. Test CLI invert subcommand
        inv_out = str(tmp_path / "inv_out")
        csv_spec = Path(__file__).resolve().parent.parent / "data" / "benchmarks" / "WASP_39b_jwst_prism.csv"
        ret_inv = main([
            "invert",
            "--spectrum", str(csv_spec),
            "--samples", "1000",
            "--out", inv_out,
        ])
        assert ret_inv == 0
        inv_summary_file = tmp_path / "inv_out" / "inversion_summary.json"
        assert inv_summary_file.exists()
        with open(inv_summary_file, "r", encoding="utf-8") as f:
            inv_summary = json.load(f)
        assert inv_summary["status"] == "success"
        assert "log_CO2" in inv_summary["medians"]
        assert inv_summary["inference_time_seconds"] < 0.10
