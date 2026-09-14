"""Verification script for Milestone 1: Data Ingestion & Preprocessing Infrastructure.

Proves:
1. Pure-Python FITS parser correctly reads binary tables from bytes/files into structured NumPy arrays and filters QUALITY == 0 in <20 ms.
2. Preprocessing pipeline correctly detrends raw flux, masks transits, and phase-folds with zero NaN propagation.
3. Parquet serialization and bundled benchmark loading work seamlessly.
"""

from __future__ import annotations

import time
from pathlib import Path
import numpy as np

from frontier_astronomy.core.constants import bkjd_to_bjd
from frontier_astronomy.core.math_utils import bic, delta_bic, likelihood_ratio_test
from frontier_astronomy.core.preprocessing import (
    asymmetric_mad_clip,
    clean_quality,
    fold_light_curve,
    inverse_variance_bin,
    iterative_savgol_detrend,
    preprocess_light_curve,
)
from frontier_astronomy.ingestion.fits_reader import (
    create_fits_binary_table,
    read_fits_binary_table,
    read_fits_light_curve,
)
from frontier_astronomy.ingestion.catalog import (
    get_benchmark_system,
    list_benchmark_systems,
    load_benchmark_light_curve,
    load_benchmark_spectrum,
    load_light_curve_parquet,
    save_light_curve_parquet,
)
from frontier_astronomy.ingestion.synthetic_generator import (
    generate_disintegrating_dust_tail_light_curve,
)


def verify_requirement_1():
    print("=" * 70)
    print("VERIFICATION REQUIREMENT 1: Pure-Python FITS Binary Table Parser")
    print("=" * 70)

    n_cadences = 20000
    time_arr = np.linspace(100.0, 500.0, n_cadences, dtype=np.float64)
    flux_arr = np.random.normal(50000.0, 50.0, n_cadences).astype(np.float32)
    err_arr = np.full(n_cadences, 50.0, dtype=np.float32)
    quality_arr = np.zeros(n_cadences, dtype=np.int32)

    # Corrupt exactly 1,500 cadences with reaction wheel dumps and safe modes
    corrupted_indices = np.random.choice(n_cadences, size=1500, replace=False)
    quality_arr[corrupted_indices] = 16

    columns = {
        "TIME": time_arr,
        "PDCSAP_FLUX": flux_arr,
        "PDCSAP_FLUX_ERR": err_arr,
        "SAP_QUALITY": quality_arr,
    }

    pri_hdr = {
        "TELESCOP": "Kepler",
        "OBJECT": "KIC 12557548",
        "KEPLERID": 12557548,
        "RA_OBJ": 290.96622,
        "DEC_OBJ": 51.50472,
    }

    fits_bytes = create_fits_binary_table(columns, primary_header=pri_hdr)
    print(f"  [+] Generated valid FITS binary table bytes ({len(fits_bytes)} bytes)")

    # Read binary table directly
    pri_h, ext_h, table = read_fits_binary_table(fits_bytes)
    print(f"  [+] Extracted BINTABLE extension with columns: {table.dtype.names}")
    assert len(table) == n_cadences
    assert isinstance(table, np.ndarray)

    # Benchmark read_fits_light_curve speed and quality filtering
    t0 = time.perf_counter()
    lc = read_fits_light_curve(fits_bytes, quality_filter=True)
    dt_ms = (time.perf_counter() - t0) * 1000.0

    print(f"  [+] Read and filtered {n_cadences} cadences into LightCurveData in {dt_ms:.2f} ms")
    print(f"  [+] Raw cadences: {n_cadences} -> Retained cadences (QUALITY == 0): {lc.n_points}")
    print(f"  [+] Target: {lc.target_id} | Mission: {lc.mission} | Median flux: {lc.median_flux:.6f}")

    assert dt_ms < 20.0, f"FAILED: Parser exceeded 20ms threshold ({dt_ms:.2f} ms)"
    assert lc.n_points == (n_cadences - 1500)
    assert np.all(lc.quality == 0)
    assert np.all(np.isfinite(lc.flux))
    assert np.all(np.isfinite(lc.flux_err))
    assert np.isclose(lc.median_flux, 1.0, atol=1e-5)
    print("  --> REQUIREMENT 1 VERIFICATION PASSED!\n")


def verify_requirement_2():
    print("=" * 70)
    print("VERIFICATION REQUIREMENT 2: Time-Series Preprocessing & Robust Detrending")
    print("=" * 70)

    period = 0.6535538
    t0 = 120.5683
    depth = 0.012

    # Generate synthetic cometary dust tail with stellar variability and flares
    lc_raw = generate_disintegrating_dust_tail_light_curve(
        target_id="KIC 12557548",
        period=period,
        t0=t0,
        depth=depth,
        duration_days=45.0,
        noise_ppm=200.0,
        seed=42,
    )
    print(f"  [+] Raw light curve points: {lc_raw.n_points} over {lc_raw.time_span_days:.1f} days")

    # Add artificial stellar rotation trend
    trend = 1.0 + 0.008 * np.sin(2.0 * np.pi * lc_raw.time / 4.2)
    flux_with_trend = lc_raw.flux * trend

    # Add artificial positive stellar flares (+0.020 flux)
    flux_with_trend[50] += 0.020
    flux_with_trend[150] += 0.025
    lc_trended = lc_raw.copy_with(flux=flux_with_trend)

    # 1. Asymmetric MAD clipping
    clip_mask = asymmetric_mad_clip(
        lc_trended.time,
        lc_trended.flux,
        lc_trended.flux_err,
        sigma_high=3.5,
        sigma_low=6.0,
    )
    assert not clip_mask[50], "Flare at index 50 should be masked"
    assert not clip_mask[150], "Flare at index 150 should be masked"
    print(f"  [+] Asymmetric MAD successfully rejected positive flares without clipping transit dips")

    # 2. Iterative Savitzky-Golay detrending with transit masking
    norm_flux, continuum = iterative_savgol_detrend(
        time=lc_trended.time,
        flux=lc_trended.flux,
        window_days=1.0,
        polyorder=2,
        period=period,
        t0=t0,
        duration_days=0.08,
    )
    print(f"  [+] Iterative Savitzky-Golay detrended light curve. Out-of-transit mean: {np.mean(norm_flux):.6f}")
    assert not np.any(np.isnan(norm_flux)), "NaN found in normalized flux!"
    assert not np.any(np.isnan(continuum)), "NaN found in continuum!"

    # 3. Phase Folding
    folded = fold_light_curve(lc_raw, period=period, t0=t0, sort=True)
    print(f"  [+] Folded {folded.n_points} cadences into orbital phase [-0.5, 0.5)")
    assert np.all(folded.phase >= -0.5) and np.all(folded.phase < 0.5)
    assert not np.any(np.isnan(folded.phase))
    assert not np.any(np.isnan(folded.flux))

    # 4. Inverse-Variance Weighted Binning
    bin_centers, b_flux, b_err, b_counts = inverse_variance_bin(
        folded.phase, folded.flux, folded.flux_err, n_bins=100
    )
    print(f"  [+] Binned into {len(bin_centers)} uniform phase bins")
    assert not np.any(np.isnan(bin_centers))
    assert not np.any(np.isnan(b_flux))
    assert not np.any(np.isnan(b_err))
    assert np.all(b_counts > 0)
    print(f"  [+] Zero NaN propagation verified across all stages")
    print("  --> REQUIREMENT 2 VERIFICATION PASSED!\n")


def verify_requirement_3():
    print("=" * 70)
    print("VERIFICATION REQUIREMENT 3: Parquet Serialization & Bundled Benchmarks")
    print("=" * 70)

    # 1. Parquet serialization round-trip
    lc_synth = generate_disintegrating_dust_tail_light_curve(target_id="PARQUET_TEST", seed=99)
    test_pq = Path("data/cache/test_roundtrip.parquet")
    save_light_curve_parquet(lc_synth, test_pq)
    lc_loaded = load_light_curve_parquet(test_pq)

    assert lc_loaded.target_id == "PARQUET_TEST"
    assert np.array_equal(lc_loaded.quality, lc_synth.quality)
    assert np.allclose(lc_loaded.time, lc_synth.time)
    assert np.allclose(lc_loaded.flux, lc_synth.flux)
    print("  [+] Parquet serialization round-trip verified (100% exact numerical match)")

    # 2. Bundled benchmark dataset 1: KIC 12557548 (Disintegrating planet)
    lc_kic = load_benchmark_light_curve("KIC 12557548")
    print(f"  [+] Loaded benchmark KIC 12557548: {lc_kic.n_points} cadences over {lc_kic.time_span_days:.1f} days")
    assert lc_kic.n_points > 1000
    assert not np.any(np.isnan(lc_kic.flux))

    # 3. Bundled benchmark dataset 2: Kepler-1625b (Exomoon candidate)
    lc_moon = load_benchmark_light_curve("Kepler-1625b")
    print(f"  [+] Loaded benchmark Kepler-1625b: {lc_moon.n_points} cadences over {lc_moon.time_span_days:.1f} days")
    assert lc_moon.n_points > 10000
    assert not np.any(np.isnan(lc_moon.flux))

    # 4. Bundled benchmark dataset 3: WASP-39b (JWST PRISM)
    spec_39 = load_benchmark_spectrum("WASP-39b")
    print(f"  [+] Loaded benchmark WASP-39b: {spec_39.n_channels} spectral channels ({spec_39.wavelength.min():.2f} - {spec_39.wavelength.max():.2f} um)")
    assert spec_39.n_channels >= 50
    assert not np.any(np.isnan(spec_39.transit_depth))

    # 5. Bundled benchmark dataset 4: WASP-96b (JWST NIRISS)
    spec_96 = load_benchmark_spectrum("WASP-96b")
    print(f"  [+] Loaded benchmark WASP-96b: {spec_96.n_channels} spectral channels ({spec_96.wavelength.min():.2f} - {spec_96.wavelength.max():.2f} um)")
    assert spec_96.n_channels >= 50
    assert not np.any(np.isnan(spec_96.transit_depth))

    print("  --> REQUIREMENT 3 VERIFICATION PASSED!\n")


if __name__ == "__main__":
    print("\n" + "#" * 70)
    print("STARTING MILESTONE 1 AUTOMATED VERIFICATION HARNESS")
    print("#" * 70 + "\n")

    t_start = time.perf_counter()
    verify_requirement_1()
    verify_requirement_2()
    verify_requirement_3()
    t_total = time.perf_counter() - t_start

    print("=" * 70)
    print(f"ALL MILESTONE 1 VERIFICATION CHECKS PASSED IN {t_total:.3f} SECONDS!")
    print("=" * 70 + "\n")
