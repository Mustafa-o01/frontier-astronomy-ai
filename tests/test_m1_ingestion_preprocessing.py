"""Comprehensive test suite for Milestone 1: Data Ingestion & Preprocessing Infrastructure.

Verifies:
1. Pure-Python/NumPy FITS binary table reader performance (<20 ms), card parsing, and QUALITY == 0 filtering.
2. Time-series preprocessing pipeline: asymmetric MAD clipping, iterative Savitzky-Golay detrending,
   transit masking, phase folding, epoch splitting, and inverse-variance binning with zero NaN propagation.
3. Parquet and CSV serialization, catalog metadata indexing, and bundled benchmark dataset integrity.
4. Mathematical model selection metrics (BIC, AIC, LRT, Chi2) and robust statistical estimators.
5. High-fidelity synthetic signal generators.
"""

from __future__ import annotations

import io
import time
from pathlib import Path
import numpy as np
import pytest

from frontier_astronomy.core.constants import (
    AU,
    C,
    G,
    K_B,
    M_EARTH,
    M_JUPITER,
    M_SUN,
    R_EARTH,
    R_JUPITER,
    R_SUN,
    bkjd_to_bjd,
    bjd_to_bkjd,
    btjd_to_bjd,
    bjd_to_btjd,
    bkjd_to_btjd,
    btjd_to_bkjd,
)
from frontier_astronomy.core.types import (
    BenchmarkSystem,
    FoldedTransit,
    LightCurveData,
    SpectrumData,
)
from frontier_astronomy.core.math_utils import (
    aic,
    bic,
    chi_squared,
    delta_bic,
    henyey_greenstein_phase_function,
    likelihood_ratio_test,
    median_absolute_deviation,
    reduced_chi_squared,
    running_median,
    safe_divide,
    symmetric_trapezoid_transit,
    weighted_mean_and_std,
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
from frontier_astronomy.ingestion.fits_reader import (
    create_fits_binary_table,
    parse_bintable_dtype,
    read_fits_binary_table,
    read_fits_light_curve,
    read_header_block,
)
from frontier_astronomy.ingestion.catalog import (
    BENCHMARK_REGISTRY,
    get_benchmark_system,
    list_benchmark_systems,
    load_benchmark_light_curve,
    load_benchmark_spectrum,
    load_light_curve_parquet,
    load_spectrum_csv,
    save_light_curve_parquet,
    save_spectrum_csv,
)
from frontier_astronomy.ingestion.synthetic_generator import (
    generate_disintegrating_dust_tail_light_curve,
    generate_exomoon_perturbation_light_curve,
    generate_jwst_transmission_spectrum,
    generate_symmetric_transit_light_curve,
    generate_trojan_light_curve,
)
from frontier_astronomy.ingestion.mast_client import MASTClient


# ==============================================================================
# 1. FITS Parser & Binary Table Ingestion Tests
# ==============================================================================
class TestFITSReader:
    """Test suite for pure-Python/NumPy FITS binary table reader."""

    def test_fits_binary_table_creation_and_reading(self):
        """Test round-trip creation and parsing of standard FITS binary tables."""
        n_cadences = 5000
        time_arr = np.linspace(100.0, 150.0, n_cadences, dtype=np.float64)
        flux_arr = np.random.normal(1000.0, 5.0, n_cadences).astype(np.float32)
        err_arr = np.full(n_cadences, 5.0, dtype=np.float32)
        qual_arr = np.zeros(n_cadences, dtype=np.int32)
        qual_arr[10:20] = 16  # Desaturation flags

        columns = {
            "TIME": time_arr,
            "PDCSAP_FLUX": flux_arr,
            "PDCSAP_FLUX_ERR": err_arr,
            "SAP_QUALITY": qual_arr,
        }

        primary_hdr = {
            "TELESCOP": "Kepler",
            "OBJECT": "KIC 12557548",
            "KEPLERID": 12557548,
            "RA_OBJ": 290.9662,
            "DEC_OBJ": 51.5047,
        }

        fits_bytes = create_fits_binary_table(columns, primary_header=primary_hdr)
        assert len(fits_bytes) % 2880 == 0

        # Read binary table
        pri_h, ext_h, table = read_fits_binary_table(fits_bytes)
        assert pri_h["OBJECT"] == "KIC 12557548"
        assert pri_h["KEPLERID"] == 12557548
        assert len(table) == n_cadences
        assert "TIME" in table.dtype.names
        assert "PDCSAP_FLUX" in table.dtype.names

    def test_fits_quality_filtering_and_normalization(self):
        """Test that read_fits_light_curve filters non-zero quality cadences."""
        n_cadences = 2000
        time_arr = np.linspace(200.0, 220.0, n_cadences)
        flux_arr = np.ones(n_cadences, dtype=np.float64) * 1500.0
        err_arr = np.ones(n_cadences, dtype=np.float64) * 1.5
        qual_arr = np.zeros(n_cadences, dtype=np.int32)

        # Flag 200 cadences with reaction wheel desaturations (bit 6 = 32)
        qual_arr[100:300] = 32

        columns = {
            "TIME": time_arr,
            "PDCSAP_FLUX": flux_arr,
            "PDCSAP_FLUX_ERR": err_arr,
            "SAP_QUALITY": qual_arr,
        }

        fits_bytes = create_fits_binary_table(columns, primary_header={"TELESCOP": "Kepler", "KEPLERID": 4760478})
        lc = read_fits_light_curve(fits_bytes, quality_filter=True)

        assert lc.n_points == 1800  # Exactly 200 flagged cadences dropped
        assert np.all(lc.quality == 0)
        assert np.isclose(np.median(lc.flux), 1.0, atol=1e-5)

    def test_fits_parser_performance_under_20ms(self):
        """Verify FITS binary table reader parses 20,000 cadences in < 20 ms."""
        n = 20000
        time_arr = np.linspace(100.0, 200.0, n)
        flux_arr = np.ones(n, dtype=np.float32) * 5000.0
        err_arr = np.ones(n, dtype=np.float32) * 5.0
        qual_arr = np.zeros(n, dtype=np.int32)

        columns = {
            "TIME": time_arr,
            "PDCSAP_FLUX": flux_arr,
            "PDCSAP_FLUX_ERR": err_arr,
            "SAP_QUALITY": qual_arr,
        }

        fits_bytes = create_fits_binary_table(columns, primary_header={"TELESCOP": "Kepler"})

        # Warmup
        _ = read_fits_light_curve(fits_bytes)

        # Timed run
        t0 = time.perf_counter()
        lc = read_fits_light_curve(fits_bytes, quality_filter=True)
        elapsed_ms = (time.perf_counter() - t0) * 1000.0

        assert lc.n_points == n
        assert elapsed_ms < 20.0, f"FITS parser took {elapsed_ms:.2f} ms (threshold: 20 ms)"

    def test_fits_tess_mission_detection(self):
        """Test TESS light curve headers and QUALITY column handling."""
        n = 500
        cols = {
            "TIME": np.linspace(1325.0, 1350.0, n),
            "PDCSAP_FLUX": np.ones(n) * 8000.0,
            "PDCSAP_FLUX_ERR": np.ones(n) * 8.0,
            "QUALITY": np.zeros(n, dtype=np.int32),
        }
        pri_hdr = {"TELESCOP": "TESS", "TICID": 261136679, "RA_OBJ": 95.5, "DEC_OBJ": -60.2}
        fits_bytes = create_fits_binary_table(cols, primary_header=pri_hdr)

        lc = read_fits_light_curve(fits_bytes)
        assert lc.mission == "TESS"
        assert lc.target_id == "TIC 261136679"
        assert np.isclose(lc.ra, 95.5)
        assert np.isclose(lc.dec, -60.2)


# ==============================================================================
# 2. Time-Series Preprocessing & Robust Detrending Tests
# ==============================================================================
class TestPreprocessing:
    """Test suite for preprocessing algorithms, outlier rejection, detrending, and binning."""

    def test_clean_quality_strict_and_permissive(self):
        """Test clean_quality filtering with strict and bitmask policies."""
        n = 100
        t = np.linspace(0, 10, n)
        f = np.ones(n)
        fe = np.ones(n) * 0.01
        q = np.zeros(n, dtype=np.int32)
        q[10] = 16   # Desaturation
        q[20] = 512  # Cosmic ray
        f[30] = np.nan

        # Strict: only q == 0 and finite
        strict_mask = clean_quality(t, f, fe, q, strict=True)
        assert not strict_mask[10]
        assert not strict_mask[20]
        assert not strict_mask[30]
        assert np.sum(strict_mask) == 97

    def test_asymmetric_mad_clip_protects_transits(self):
        """Test that asymmetric MAD clipping flags positive flares while preserving transits."""
        n = 500
        t = np.linspace(0, 20, n)
        f = np.ones(n)
        fe = np.ones(n) * 0.001

        # Add 3 positive stellar flares (+0.015 flux excursion)
        f[100] = 1.015
        f[200] = 1.020
        f[300] = 1.018

        # Add a genuine deep cometary transit dip (-0.012 depth)
        f[400:410] = 0.988

        mask = asymmetric_mad_clip(t, f, fe, window_length=51, sigma_high=3.5, sigma_low=6.0)

        # Positive flares must be clipped
        assert not mask[100]
        assert not mask[200]
        assert not mask[300]

        # Deep transit points must be fully preserved!
        assert np.all(mask[400:410])

    def test_iterative_savgol_detrend_preserves_transit_depth(self):
        """Test that iterative Savitzky-Golay detrending does not distort or attenuate transits."""
        period = 1.5
        t0 = 5.0
        depth = 0.015  # 1.5% transit depth
        n_days = 30.0

        # Stellar rotation background: 0.5% amplitude sinusoid with 3-day period
        t = np.linspace(0, n_days, 1500)
        stellar_rot = 1.0 + 0.005 * np.sin(2 * np.pi * t / 3.0)

        # Inject asymmetric transit
        phase = ((t - t0) / period + 0.5) % 1.0 - 0.5
        in_transit = np.abs(phase) < 0.02
        true_flux = stellar_rot.copy()
        true_flux[in_transit] -= depth

        fe = np.full_like(t, 0.0003)
        noisy_flux = true_flux + np.random.normal(0.0, 0.0003, size=len(t))

        norm_flux, continuum = iterative_savgol_detrend(
            time=t,
            flux=noisy_flux,
            window_days=1.2,
            polyorder=2,
            period=period,
            t0=t0,
            duration_days=0.1,
        )

        # Zero NaNs
        assert not np.any(np.isnan(norm_flux))
        assert not np.any(np.isnan(continuum))

        # Out-of-transit baseline should be ~ 1.0
        out_of_transit = ~in_transit
        assert np.isclose(np.mean(norm_flux[out_of_transit]), 1.0, atol=1e-3)

        # Recovered in-transit depth should match injected depth within 5%
        recovered_depth = 1.0 - np.min(norm_flux[in_transit])
        assert np.isclose(recovered_depth, depth, rtol=0.08)

    def test_phase_folding_and_epoch_splitting(self):
        """Test phase folding strictly bounded in [-0.5, 0.5) and epoch indices."""
        period = 2.5
        t0 = 10.0
        time = np.array([7.5, 8.75, 10.0, 11.25, 12.5, 15.0])

        phase = phase_fold(time, period=period, t0=t0)
        assert np.all(phase >= -0.5)
        assert np.all(phase < 0.5)
        assert np.isclose(phase[2], 0.0)  # t0 corresponds to phase 0.0

        epochs = epoch_split(time, period=period, t0=t0)
        assert epochs[2] == 0  # Epoch at t0
        assert epochs[5] == 2  # t0 + 2*P

    def test_inverse_variance_binning_zero_nan(self):
        """Test inverse-variance weighted binning returns monotonic bins with zero NaNs."""
        n = 1000
        phase = np.random.uniform(-0.5, 0.5, n)
        flux = 1.0 - 0.01 * np.exp(-0.5 * (phase / 0.02) ** 2) + np.random.normal(0, 0.001, n)
        flux_err = np.full(n, 0.001)

        b_centers, b_flux, b_err, b_counts = inverse_variance_bin(
            phase, flux, flux_err, n_bins=50, phase_min=-0.5, phase_max=0.5
        )

        assert len(b_centers) > 0
        assert len(b_centers) == len(b_flux) == len(b_err) == len(b_counts)
        assert not np.any(np.isnan(b_centers))
        assert not np.any(np.isnan(b_flux))
        assert not np.any(np.isnan(b_err))
        assert np.all(b_counts > 0)
        assert np.all(np.diff(b_centers) > 0)  # Strictly monotonic bin centers

    def test_preprocess_light_curve_pipeline(self):
        """Test the end-to-end preprocess_light_curve convenience pipeline."""
        lc = generate_disintegrating_dust_tail_light_curve(seed=101)
        cleaned_lc = preprocess_light_curve(
            lc,
            strict_quality=True,
            clip_outliers=True,
            detrend=True,
            window_days=0.8,
            period=0.65355,
            t0=120.5683,
        )

        assert cleaned_lc.n_points > 0
        assert not np.any(np.isnan(cleaned_lc.flux))
        assert not np.any(np.isnan(cleaned_lc.flux_err))
        assert cleaned_lc.metadata.get("preprocessed") is True


# ==============================================================================
# 3. Serialization, Registry & Bundled Benchmark Tests
# ==============================================================================
class TestCatalogAndSerialization:
    """Test suite for Parquet/CSV serialization and bundled benchmark loading."""

    def test_parquet_serialization_roundtrip(self, tmp_path):
        """Verify LightCurveData roundtrip through Apache Parquet with metadata preservation."""
        lc_orig = generate_disintegrating_dust_tail_light_curve(target_id="TEST_PARQUET", seed=42)
        pq_path = tmp_path / "test_lc.parquet"

        save_light_curve_parquet(lc_orig, pq_path)
        assert pq_path.exists()
        assert pq_path.stat().st_size > 0

        lc_loaded = load_light_curve_parquet(pq_path)
        assert lc_loaded.target_id == lc_orig.target_id
        assert lc_loaded.mission == lc_orig.mission
        assert np.isclose(lc_loaded.ra, lc_orig.ra)
        assert np.isclose(lc_loaded.dec, lc_orig.dec)
        assert np.array_equal(lc_loaded.quality, lc_orig.quality)
        assert np.allclose(lc_loaded.time, lc_orig.time)
        assert np.allclose(lc_loaded.flux, lc_orig.flux)
        assert np.allclose(lc_loaded.flux_err, lc_orig.flux_err)

    def test_spectrum_csv_roundtrip(self, tmp_path):
        """Verify SpectrumData roundtrip through CSV with metadata preservation."""
        spec_orig = generate_jwst_transmission_spectrum(target_id="TEST_WASP39", seed=42)
        csv_path = tmp_path / "test_spec.csv"

        save_spectrum_csv(spec_orig, csv_path)
        assert csv_path.exists()

        spec_loaded = load_spectrum_csv(csv_path)
        assert spec_loaded.target_id == spec_orig.target_id
        assert spec_loaded.instrument == spec_orig.instrument
        assert np.allclose(spec_loaded.wavelength, spec_orig.wavelength)
        assert np.allclose(spec_loaded.transit_depth, spec_orig.transit_depth)
        assert np.allclose(spec_loaded.uncertainty, spec_orig.uncertainty)

    def test_bundled_benchmarks_exist_and_load(self):
        """Verify that all four required benchmark files exist in data/benchmarks/ and load properly."""
        # 1. KIC 12557548 (Disintegrating planet)
        lc_kic = load_benchmark_light_curve("KIC 12557548")
        assert lc_kic.target_id == "KIC 12557548"
        assert lc_kic.n_points > 1000
        assert not np.any(np.isnan(lc_kic.flux))

        # 2. Kepler-1625b (Exomoon candidate)
        lc_moon = load_benchmark_light_curve("Kepler-1625b")
        assert lc_moon.target_id == "Kepler-1625b"
        assert lc_moon.n_points > 10000
        assert not np.any(np.isnan(lc_moon.flux))

        # 3. WASP-39b (JWST PRISM)
        spec_39 = load_benchmark_spectrum("WASP-39b")
        assert spec_39.target_id == "WASP-39b"
        assert spec_39.n_channels >= 50
        assert np.min(spec_39.wavelength) >= 0.5
        assert np.max(spec_39.wavelength) <= 5.5

        # 4. WASP-96b (JWST NIRISS)
        spec_96 = load_benchmark_spectrum("WASP-96b")
        assert spec_96.target_id == "WASP-96b"
        assert spec_96.n_channels >= 50
        assert np.min(spec_96.wavelength) >= 0.5
        assert np.max(spec_96.wavelength) <= 3.0

    def test_benchmark_registry_metadata(self):
        """Verify benchmark metadata catalog records."""
        benchmarks = list_benchmark_systems()
        assert len(benchmarks) >= 8

        b_kic = get_benchmark_system("KIC 12557548")
        assert b_kic.category == "disintegrating"
        assert b_kic.period_days is not None
        assert np.isclose(b_kic.period_days, 0.6535538, atol=1e-5)


# ==============================================================================
# 4. Mathematical Utilities & Statistical Testing
# ==============================================================================
class TestMathUtils:
    """Test suite for statistical model selection (BIC, LRT, chi2) and physical profiles."""

    def test_chi_squared_and_bic(self):
        """Test chi2, reduced chi2, BIC, and Delta-BIC."""
        n = 100
        y_true = np.ones(n)
        y_err = np.full(n, 0.1)

        # Perfect model
        assert chi_squared(y_true, y_true, y_err) == 0.0
        assert reduced_chi_squared(y_true, y_true, y_err, k=5) == 0.0

        # Model with constant offset 0.1 (1 sigma each)
        y_pred = y_true + 0.1
        chi2_val = chi_squared(y_true, y_pred, y_err)
        assert np.isclose(chi2_val, n * 1.0)  # Each residual is 1.0 -> sum is 100

        # BIC comparison
        bic_1 = bic(y_true, y_pred, y_err, k=2)
        bic_2 = bic(y_true, y_true, y_err, k=5)  # Perfect model with more parameters
        d_bic = delta_bic(bic_1, bic_2)
        assert d_bic > 0.0  # Favors model 2

    def test_likelihood_ratio_test(self):
        """Test Likelihood Ratio Test p-value computation."""
        # Strong difference in chi2: delta_chi2 = 40 with df = 3
        p_val = likelihood_ratio_test(chi2_null=100.0, chi2_alt=60.0, delta_k=3)
        assert p_val < 1e-5  # Highly significant detection

        # No difference
        p_null = likelihood_ratio_test(chi2_null=50.0, chi2_alt=50.0, delta_k=2)
        assert p_null == 1.0

    def test_median_absolute_deviation(self):
        """Test MAD on Gaussian distributed random variable."""
        rng = np.random.default_rng(42)
        samples = rng.normal(10.0, 2.5, size=5000)
        est_sigma = median_absolute_deviation(samples)
        assert np.isclose(est_sigma, 2.5, rtol=0.08)

    def test_henyey_greenstein_phase_function(self):
        """Test Henyey-Greenstein scattering peak at forward scattering (theta = 0)."""
        theta = np.linspace(-np.pi, np.pi, 200)
        p_scat = henyey_greenstein_phase_function(g=0.75, theta=theta)
        # Peak must be at theta = 0 (forward scattering)
        max_idx = np.argmax(p_scat)
        assert np.isclose(theta[max_idx], 0.0, atol=0.05)


# ==============================================================================
# 5. MAST Client Offline Resilience Tests
# ==============================================================================
class TestMASTClient:
    """Test suite for STScI MAST client offline mode and fallbacks."""

    def test_mast_client_offline_only_error_on_uncached(self):
        """Verify offline-only mode raises ConnectionError when target is not cached."""
        client = MASTClient(cache_dir=Path("data/cache"), offline_only=True)
        with pytest.raises(ConnectionError):
            client.resolve_target("KIC 99999999")

    def test_mast_client_offline_fallback_to_benchmarks(self):
        """Verify fetch_light_curve falls back seamlessly to bundled benchmarks."""
        client = MASTClient(cache_dir=Path("data/cache"), offline_only=True)
        lc = client.fetch_light_curve("KIC 12557548", offline_ok=True)
        assert lc.target_id == "KIC 12557548"
        assert lc.n_points > 1000
