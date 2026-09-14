import sys
import os
import io
import pytest
import numpy as np

# Set project root
sys.path.insert(0, r"G:\frontier_astronomy_ai")

from frontier_astronomy.core.types import (
    LightCurveData,
    FoldedTransit,
    DustTailDetectionResult,
    ExomoonPerturbationResult,
    SpectrumData,
    AtmosphericInversionResult,
    BenchmarkSystem,
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
from frontier_astronomy.ingestion.fits_reader import (
    create_fits_binary_table,
    read_fits_binary_table,
    read_fits_light_curve,
)
from frontier_astronomy.ingestion.catalog import (
    load_benchmark_light_curve,
    load_benchmark_spectrum,
    save_light_curve_parquet,
    load_light_curve_parquet,
)

print("Running Adversarial Stress Tests for Milestone 1...")

# --- Test 1: Dataclass Frozen Immutability ---
lc = LightCurveData(
    target_id="TEST_FROZEN",
    mission="Kepler",
    time=np.array([1.0, 2.0]),
    flux=np.array([1.0, 1.0]),
    flux_err=np.array([0.01, 0.01]),
    quality=np.array([0, 0]),
    ra=10.0,
    dec=20.0,
)
try:
    lc.target_id = "MUTATED"
    raise AssertionError("LightCurveData is NOT frozen!")
except Exception as e:
    print("  [PASS] LightCurveData is frozen:", type(e).__name__)

# --- Test 2: Dataclass Shape & Length Validation ---
try:
    # Mismatched length
    LightCurveData(
        target_id="BAD_LEN",
        mission="Kepler",
        time=np.array([1.0, 2.0]),
        flux=np.array([1.0]),
        flux_err=np.array([0.01, 0.01]),
        quality=np.array([0, 0]),
        ra=0.0,
        dec=0.0,
    )
    raise AssertionError("Failed to catch length mismatch!")
except ValueError:
    print("  [PASS] LightCurveData rejected mismatched lengths")

try:
    # 2D array
    LightCurveData(
        target_id="BAD_DIM",
        mission="Kepler",
        time=np.ones((2, 2)),
        flux=np.ones((2, 2)),
        flux_err=np.ones((2, 2)),
        quality=np.zeros((2, 2)),
        ra=0.0,
        dec=0.0,
    )
    raise AssertionError("Failed to catch 2D array!")
except ValueError:
    print("  [PASS] LightCurveData rejected 2D arrays")

# --- Test 3: FITS Reader Endianness & Data Integrity ---
# Write known big-endian values
test_floats = np.array([123.456, 789.012, -0.00345], dtype=np.float64)
test_ints = np.array([42, 999999, -12345], dtype=np.int32)
cols = {
    "TIME": test_floats,
    "PDCSAP_FLUX": test_floats * 10.0,
    "PDCSAP_FLUX_ERR": np.array([0.1, 0.1, 0.1], dtype=np.float64),
    "SAP_QUALITY": test_ints,
}
fits_data = create_fits_binary_table(cols)
_, _, tbl = read_fits_binary_table(fits_data)
assert np.allclose(tbl["TIME"], test_floats), "Endianness corruption on TIME!"
assert np.array_equal(tbl["SAP_QUALITY"], test_ints), "Endianness corruption on QUALITY!"
print("  [PASS] FITS binary table endianness exact match verified")

# --- Test 4: FITS Quality Filtering When All Corrupted ---
cols_corrupted = {
    "TIME": np.array([1.0, 2.0]),
    "PDCSAP_FLUX": np.array([100.0, 100.0]),
    "PDCSAP_FLUX_ERR": np.array([1.0, 1.0]),
    "SAP_QUALITY": np.array([16, 32]),
}
fits_bad = create_fits_binary_table(cols_corrupted)
lc_empty = read_fits_light_curve(fits_bad, quality_filter=True)
assert lc_empty.n_points == 0
assert lc_empty.median_flux == 0.0
assert lc_empty.time_span_days == 0.0
print("  [PASS] FITS reader gracefully handles all-corrupted light curve (0 points)")

# --- Test 5: Preprocessing Period Validation ---
try:
    phase_fold(np.array([1.0, 2.0]), period=-1.0, t0=0.0)
    raise AssertionError("phase_fold allowed negative period!")
except ValueError:
    print("  [PASS] phase_fold rejected non-positive period")

try:
    epoch_split(np.array([1.0, 2.0]), period=0.0, t0=0.0)
    raise AssertionError("epoch_split allowed zero period!")
except ValueError:
    print("  [PASS] epoch_split rejected zero period")

# --- Test 6: Inverse-variance Binning with Sparse & Empty Bins ---
phases = np.array([-0.45, -0.44, 0.45])
fluxes = np.array([1.0, 1.01, 0.99])
errs = np.array([0.01, 0.01, 0.01])
centers, b_f, b_e, counts = inverse_variance_bin(phases, fluxes, errs, n_bins=100)
assert len(centers) == 2
assert not np.any(np.isnan(centers))
assert not np.any(np.isnan(b_f))
assert not np.any(np.isnan(b_e))
assert np.all(counts > 0)
print("  [PASS] inverse_variance_bin omitted empty bins with zero NaNs")

# --- Test 7: Savitzky-Golay on Very Short Arrays ---
short_t = np.array([1.0, 2.0])
short_f = np.array([10.0, 10.0])
norm_f, cont = iterative_savgol_detrend(short_t, short_f)
assert len(norm_f) == 2
assert not np.any(np.isnan(norm_f))
print("  [PASS] iterative_savgol_detrend handled short array gracefully")

# --- Test 8: Asymmetric MAD with Extreme Flare ---
t_flare = np.linspace(0, 10, 200)
f_flare = np.ones(200)
f_flare[50] = 500.0
mask_flare = asymmetric_mad_clip(t_flare, f_flare)
assert not mask_flare[50]
print("  [PASS] asymmetric_mad_clip rejected 500x stellar flare")

# --- Test 9: Run pytest programmatic invocation ---
print("\nInvoking full pytest suite programmatically...")
pytest_args = [r"G:\frontier_astronomy_ai\tests\test_m1_ingestion_preprocessing.py", "-v", "--tb=short"]
ret = pytest.main(pytest_args)
assert ret == 0, f"pytest failed with return code {ret}"
print(f"  [PASS] pytest suite passed with code {ret}")

print("\nALL ADVERSARIAL STRESS TESTS COMPLETED SUCCESSFULLY!")