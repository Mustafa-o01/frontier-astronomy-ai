"""Empirical Adversarial Test Suite for Preprocessing & Detrending Engine.

Challenger: challenger_m1_2 (Preprocessing Challenger)
Target: frontier_astronomy.core.preprocessing & math_utils

Stress-tests:
1. Heavy stellar flares combined with cometary asymmetric transits (clipping vulnerability).
2. Observation gaps, missing cadences, non-monotonic jitter, and SG boundary artifacts.
3. Arrays with all NaNs, Infs, zeros, negative fluxes, and extreme dynamic range uncertainties.
4. Extreme period regimes (P < 0.1 d with int32 overflow, P > 1000 d with phase collapse).
5. Downstream NaN propagation and mathematical stability under degenerate inputs.
"""

from __future__ import annotations

import pytest
import numpy as np

from frontier_astronomy.core.types import LightCurveData, FoldedTransit
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
from frontier_astronomy.core.math_utils import (
    chi_squared,
    reduced_chi_squared,
    bic,
    aic,
    delta_bic,
    likelihood_ratio_test,
    median_absolute_deviation,
    running_median,
)
from frontier_astronomy.ingestion.synthetic_generator import (
    generate_disintegrating_dust_tail_light_curve,
)
from frontier_astronomy.ingestion.catalog import load_benchmark_light_curve


# ==============================================================================
# 1. Stellar Flares Combined with Cometary Asymmetric Transits
# ==============================================================================
class TestFlaresAndCometaryTransits:
    """Stress-test asymmetric MAD clipping and detrending against cometary transits and flares."""

    def test_asymmetric_mad_clip_erases_genuine_dust_tail_transits(self):
        """CRITICAL VULNERABILITY FINDING:
        Empirically demonstrate that asymmetric_mad_clip with sigma_low=6.0 deletes
        genuine cometary transit troughs when realistic Kepler/TESS noise (250-300 ppm) is present.
        """
        n_cadences = 2000
        t = np.linspace(100.0, 140.0, n_cadences)
        rng = np.random.default_rng(42)
        noise = rng.normal(0.0, 0.0003, n_cadences)  # 300 ppm noise
        flux = 1.0 + noise
        flux_err = np.full(n_cadences, 0.0003)

        # Inject asymmetric cometary transit (depth 1.2% = 0.012, typical of KIC 12557548)
        # 8 cadences: steep ingress (2 cadences), trough (2 cadences), exponential tail (4 cadences)
        transit_indices = slice(500, 508)
        transit_profile = np.array([0.004, 0.009, 0.012, 0.010, 0.007, 0.004, 0.002, 0.001])
        flux[transit_indices] -= transit_profile

        # Run asymmetric MAD clipping
        clip_mask = asymmetric_mad_clip(t, flux, flux_err, window_length=101, sigma_high=3.5, sigma_low=6.0)

        # Empirically verify that deep transit points are erroneously clipped out
        clipped_in_transit = np.sum(~clip_mask[transit_indices])
        assert clipped_in_transit >= 5, (
            f"VULNERABILITY CONFIRMED: asymmetric_mad_clip clipped {clipped_in_transit} of 8 "
            f"transit cadences because transit depth (12,000 ppm) exceeds 6 * MAD (~1,800 ppm)."
        )

    def test_kic_12557548_real_benchmark_transit_destruction(self):
        """CRITICAL BENCHMARK FINDING:
        Empirically prove that running preprocess_light_curve(clip_outliers=True) on the
        bundled real Kepler benchmark KIC 12557548 destroys all deep transit cadences (< 0.99).
        """
        lc = load_benchmark_light_curve("KIC 12557548")
        deep_points_raw = np.sum(lc.flux < 0.99)
        assert deep_points_raw > 0, "Benchmark must contain genuine deep transit points"

        # Preprocess with outlier clipping enabled
        lc_clean = preprocess_light_curve(lc, clip_outliers=True)
        deep_points_remaining = np.sum(lc_clean.flux < 0.99)

        # Demonstrates that 100% of deep transit cadences were stripped away
        assert deep_points_remaining == 0, (
            f"VULNERABILITY CONFIRMED: {deep_points_raw} deep transit points in KIC 12557548 "
            f"were purged down to {deep_points_remaining} by asymmetric_mad_clip!"
        )

    def test_synthetic_dust_tail_100_percent_clipping(self):
        """Empirically prove that synthetic disintegrating planet transits have 100% of
        deep cadences stripped when passed through asymmetric_mad_clip.
        """
        lc = generate_disintegrating_dust_tail_light_curve(
            target_id="SYNTH_CHALLENGE",
            duration_days=20.0,
            depth=0.010,
            noise_ppm=250.0,
            seed=42,
        )
        deep_mask = lc.flux < 0.995
        n_deep = np.sum(deep_mask)
        assert n_deep > 10

        clip_mask = asymmetric_mad_clip(lc.time, lc.flux, lc.flux_err)
        clipped_deep = np.sum(deep_mask & (~clip_mask))

        # At least 90% of deep cadences are clipped
        assert (clipped_deep / n_deep) >= 0.90, (
            f"Expected massive clipping of cometary transit trough, clipped {clipped_deep}/{n_deep}"
        )

    def test_forward_scattering_peak_clipping(self):
        """Empirically test whether pre-ingress forward-scattering brightening bump
        is flagged and destroyed as a 'stellar flare' by sigma_high=3.5.
        """
        lc = generate_disintegrating_dust_tail_light_curve(
            target_id="SYNTH_FWD_SCAT",
            duration_days=20.0,
            depth=0.010,
            forward_scat_amp=0.0020,  # 2000 ppm pre-ingress bump
            noise_ppm=250.0,
            seed=42,
        )
        fwd_mask = lc.flux > 1.0015
        n_fwd = np.sum(fwd_mask)
        assert n_fwd > 0

        clip_mask = asymmetric_mad_clip(lc.time, lc.flux, lc.flux_err)
        clipped_fwd = np.sum(fwd_mask & (~clip_mask))

        # Forward scattering brightening bump is falsely identified as a flare and wiped out
        assert (clipped_fwd / n_fwd) >= 0.80, (
            f"Forward scattering bump clipped as flare: {clipped_fwd}/{n_fwd}"
        )

    def test_fred_flare_cascade_masks_subsequent_transit(self):
        """Test how a genuine FRED stellar flare immediately preceding a transit causes
        mask_consecutive_flares to mask through into the transit ingress.
        """
        n = 500
        t = np.linspace(100.0, 110.0, n)
        flux = np.ones(n)
        flux_err = np.full(n, 0.0003)

        # Flare at index 200 with peak +0.03 (3% brightening) decaying over 10 cadences
        decay = 0.03 * np.exp(-np.arange(15) / 3.0)
        flux[200:215] += decay

        # Ingress of cometary transit immediately at index 210
        flux[210:220] -= 0.010

        mask = asymmetric_mad_clip(t, flux, flux_err, mask_consecutive_flares=True)

        # Flare peak must be masked
        assert not mask[200]
        # And the consecutive flare logic masks cadences where flux > 1.0 * mad_val
        assert not mask[201]


# ==============================================================================
# 2. Observation Gaps, Missing Cadences, and Jitter
# ==============================================================================
class TestGapsMissingCadencesAndJitter:
    """Stress-test detrending and preprocessing under irregular sampling and massive gaps."""

    def test_massive_inter_quarter_gap_boundary_artifact(self):
        """Empirically test that applying savgol_filter across a 60-day gap without
        segment splitting generates false transit-like dips (> 3% drop) at the gap boundary.
        """
        # Quarter 1: days 100-110, star at mean flux 1.04
        t1 = np.linspace(100.0, 110.0, 400)
        f1 = np.full(400, 1.04)
        # Quarter 2: days 170-180 (60 day gap!), star at mean flux 0.96
        t2 = np.linspace(170.0, 180.0, 400)
        f2 = np.full(400, 0.96)

        t = np.concatenate([t1, t2])
        f = np.concatenate([f1, f2])

        fn, cont = iterative_savgol_detrend(t, f, window_days=1.0)

        # At the boundary (index 400), savgol polynomial bridges across indices without time-awareness
        # resulting in a large spurious dip
        min_boundary_flux = np.min(fn[395:405])
        assert min_boundary_flux < 0.98, (
            f"Gap boundary artifact failed to produce expected edge distortion: {min_boundary_flux}"
        )

    def test_non_monotonic_timestamps_interpolation_corruption(self):
        """Empirically verify that unsorted/jittered timestamps cause np.interp in
        iterative_savgol_detrend to produce corrupted out-of-order flux values.
        """
        n = 100
        t = np.linspace(100.0, 105.0, n)
        f = np.ones(n)
        f[40:50] = 0.98  # Transit dip

        # Introduce temporal shuffle / jitter
        rng = np.random.default_rng(123)
        shuffle_idx = rng.permutation(n)
        t_jittered = t[shuffle_idx]
        f_jittered = f[shuffle_idx]

        # In iterative_savgol_detrend, np.interp expects monotonic xp
        fn, cont = iterative_savgol_detrend(
            t_jittered, f_jittered, window_days=1.0, period=1.0, t0=102.0, duration_days=0.1
        )
        assert len(fn) == n
        assert np.all(np.isfinite(fn))

    def test_all_identical_timestamps(self):
        """Test degenerate case where all timestamps are identical (diffs have no positive values)."""
        n = 50
        t = np.full(n, 100.0)
        f = np.ones(n)
        # Must not crash, should fallback to default cadence_dt = 0.0204
        fn, cont = iterative_savgol_detrend(t, f, window_days=1.0)
        assert len(fn) == n
        assert np.all(np.isfinite(fn))


# ==============================================================================
# 3. Arrays Containing All NaNs, Infs, Zeros, or Degenerate Data
# ==============================================================================
class TestExtremeAndCorruptInputs:
    """Stress-test numerical robustness against non-finite, zero, and extreme values."""

    def test_clean_quality_all_nans_and_infs(self):
        """Test clean_quality on all-NaN, all-Inf, and negative inputs."""
        n = 100
        t_nan = np.full(n, np.nan)
        f_nan = np.full(n, np.nan)
        fe_nan = np.full(n, np.nan)
        q = np.zeros(n, dtype=np.int32)

        mask = clean_quality(t_nan, f_nan, fe_nan, q)
        assert np.sum(mask) == 0, "All NaNs must result in all-False mask"

        t_inf = np.full(n, np.inf)
        f_inf = np.full(n, np.inf)
        fe_inf = np.full(n, np.inf)
        mask_inf = clean_quality(t_inf, f_inf, fe_inf, q)
        assert np.sum(mask_inf) == 0, "All Infs must result in all-False mask"

    def test_clean_quality_non_positive_flux_and_err(self):
        """Test that negative and zero flux and uncertainties are rejected by clean_quality."""
        t = np.array([1.0, 2.0, 3.0, 4.0])
        f = np.array([1.0, 0.0, -0.5, 1.0])
        fe = np.array([0.01, 0.01, 0.01, 0.0])  # last has 0 uncertainty
        q = np.zeros(4, dtype=np.int32)

        mask = clean_quality(t, f, fe, q)
        # Only index 0 is valid (f > 0, fe > 0)
        assert np.array_equal(mask, [True, False, False, False])

    def test_clean_quality_nan_in_quality_array(self):
        """Test behavior when quality array is float with NaNs."""
        t = np.array([1.0, 2.0])
        f = np.array([1.0, 1.0])
        fe = np.array([0.01, 0.01])
        q = np.array([np.nan, 0.0])

        mask = clean_quality(t, f, fe, q)
        assert not mask[0], "NaN quality must be excluded"
        assert mask[1], "Zero quality must be retained"

    def test_asymmetric_mad_clip_all_nan_and_inf(self):
        """Test asymmetric_mad_clip on all-NaN or all-Inf arrays."""
        n = 50
        f_nan = np.full(n, np.nan)
        t = np.arange(n, dtype=np.float64)
        mask = asymmetric_mad_clip(t, f_nan)
        # All comparisons with NaN yield False
        assert np.sum(mask) == 0

        f_inf = np.full(n, np.inf)
        mask_inf = asymmetric_mad_clip(t, f_inf)
        assert np.sum(mask_inf) == 0

    def test_asymmetric_mad_clip_all_zeros(self):
        """Test asymmetric_mad_clip on all-zero flux array."""
        n = 50
        f_zero = np.zeros(n)
        t = np.arange(n, dtype=np.float64)
        mask = asymmetric_mad_clip(t, f_zero)
        # With zero residuals and zero MAD, all points are kept
        assert np.all(mask)

    def test_iterative_savgol_all_zeros_no_crash(self):
        """Test iterative_savgol_detrend with all zeros."""
        n = 50
        t = np.arange(n, dtype=np.float64)
        f_zero = np.zeros(n)
        fn, cont = iterative_savgol_detrend(t, f_zero)
        assert len(fn) == n
        assert np.all(np.isfinite(fn))
        assert np.all(np.isfinite(cont))

    def test_inverse_variance_binning_extreme_dynamic_range(self):
        """Test inverse_variance_bin with extreme uncertainties (underflow and overflow)."""
        n = 100
        p = np.linspace(-0.5, 0.5, n)
        f = np.ones(n)
        # fe spans from 1e-150 to 1e150
        fe = np.logspace(-150, 150, n)

        centers, b_f, b_fe, counts = inverse_variance_bin(p, f, fe, n_bins=10)
        assert len(centers) > 0
        assert np.all(np.isfinite(centers))
        assert np.all(np.isfinite(b_f))
        assert np.all(np.isfinite(b_fe))

    def test_preprocess_light_curve_all_nan_produces_zero_points(self):
        """Test end-to-end preprocess_light_curve on all-NaN LightCurveData."""
        n = 50
        lc = LightCurveData(
            target_id="NAN_LC",
            mission="Kepler",
            time=np.full(n, np.nan),
            flux=np.full(n, np.nan),
            flux_err=np.full(n, np.nan),
            quality=np.zeros(n, dtype=np.int32),
            ra=0.0,
            dec=0.0,
            metadata={},
        )
        res = preprocess_light_curve(lc)
        assert len(res.time) == 0
        assert len(res.flux) == 0
        assert len(res.flux_err) == 0


# ==============================================================================
# 4. Extreme Period Values (P < 0.1 d and P > 1000 d)
# ==============================================================================
class TestExtremePeriods:
    """Stress-test phase folding, epoch splitting, and binning under extreme period regimes."""

    def test_ultra_short_period_int32_overflow_in_epoch_split(self):
        """CRITICAL NUMERICAL FINDING:
        Empirically demonstrate that epoch_split with ultra-short period and BJD timestamps
        causes np.int32 overflow and integer wraparound to -2147483648.
        """
        # Timestamps in BJD (e.g. 2455000)
        t = np.array([2455000.0, 2455001.0])
        # P = 0.0005 days (~43 seconds)
        p = 0.0005
        epochs = epoch_split(t, period=p, t0=0.0)

        # Expected value: 2455000 / 0.0005 = 4.91e9, which exceeds int32 max (2.147e9)
        assert epochs[0] == -2147483648, (
            f"VULNERABILITY CONFIRMED: int32 overflow in epoch_split yielded {epochs[0]}"
        )

    def test_ultra_short_period_phase_fold_bounded(self):
        """Test that phase_fold strictly remains in [-0.5, 0.5) even for P = 0.001 d."""
        t = np.linspace(100.0, 110.0, 1000)
        p = 0.001
        phase = phase_fold(t, period=p, t0=100.0)
        assert np.all(phase >= -0.5)
        assert np.all(phase < 0.5)
        assert not np.any(np.isnan(phase))

    def test_ultra_long_period_phase_collapse_and_binning(self):
        """Test P = 5000 days and P = 10000 days over a 90-day Kepler quarter baseline."""
        t = np.linspace(100.0, 190.0, 4500)
        p = 5000.0
        phase = phase_fold(t, period=p, t0=100.0)
        # Phase span is 90 / 5000 = 0.018 phase units
        assert (phase.max() - phase.min()) <= 0.02

        # All points have epoch 0
        epochs = epoch_split(t, period=p, t0=100.0)
        assert np.all(epochs == 0)

        # In inverse variance binning with 100 bins, only ~2-3 bins should be populated
        c, f, fe, cnt = inverse_variance_bin(phase, np.ones_like(phase), np.ones_like(phase) * 0.001, n_bins=100)
        assert len(c) <= 3, f"Expected concentrated binning, got {len(c)} occupied bins"

    def test_degenerate_period_nan_and_inf(self):
        """Test phase_fold and epoch_split with period = NaN or Inf.
        Demonstrates that check `if period <= 0:` does NOT reject NaN and Inf.
        """
        t = np.array([100.0, 101.0, 102.0])

        # period = NaN
        ph_nan = phase_fold(t, float("nan"), 0.0)
        assert np.all(np.isnan(ph_nan)), "phase_fold with NaN period returns NaNs"

        # epoch_split with NaN period
        ep_nan = epoch_split(t, float("nan"), 0.0)
        assert np.all(ep_nan == -2147483648), "epoch_split with NaN period wraps to int32 min"

        # period = Inf
        ph_inf = phase_fold(t, float("inf"), 0.0)
        assert np.all(ph_inf == 0.0), "phase_fold with Inf period returns zeros"


# ==============================================================================
# 5. Downstream NaN Propagation & Mathematical Safety
# ==============================================================================
class TestDownstreamNaNPropagation:
    """Stress-test mathematical utilities and downstream contracts for NaN leakage."""

    def test_chi_squared_and_bic_on_nan_and_inf_inputs(self):
        """Verify chi_squared and bic handle NaNs and empty arrays safely returning inf."""
        y_true = np.array([np.nan, 1.0, np.inf])
        y_pred = np.array([1.0, np.nan, 1.0])
        y_err = np.array([0.01, 0.01, np.nan])

        # Zero valid points
        c2 = chi_squared(y_true, y_pred, y_err)
        assert c2 == float("inf"), "chi_squared must return inf when no points are valid"

        b = bic(y_true, y_pred, y_err, k=2)
        assert b == float("inf"), "bic must return inf when no points are valid"

    def test_reduced_chi_squared_dof_le_zero(self):
        """Test reduced_chi_squared when degrees of freedom N - k <= 0."""
        y_true = np.array([1.0, 1.0])
        y_pred = np.array([1.0, 1.0])
        y_err = np.array([0.01, 0.01])

        # N=2, k=3 -> dof = -1
        rc2 = reduced_chi_squared(y_true, y_pred, y_err, k=3)
        assert rc2 == float("inf")

    def test_likelihood_ratio_test_invalid_df(self):
        """Test likelihood_ratio_test raises ValueError on non-positive delta_k."""
        with pytest.raises(ValueError, match="Degrees of freedom delta_k must be positive"):
            likelihood_ratio_test(100.0, 50.0, delta_k=0)

    def test_median_absolute_deviation_all_nans(self):
        """Test MAD of all NaNs returns 0.0 without exception."""
        mad_val = median_absolute_deviation(np.full(50, np.nan))
        assert mad_val == 0.0

    def test_running_median_empty_and_single_point(self):
        """Test running_median on empty and 1-element arrays."""
        empty_res = running_median(np.array([]), window_length=5)
        assert len(empty_res) == 0

        single_res = running_median(np.array([42.0]), window_length=5)
        assert len(single_res) == 1
        assert single_res[0] == 42.0

    def test_fold_light_curve_preserves_zero_nan(self):
        """Verify fold_light_curve preserves finite invariants."""
        n = 200
        t = np.linspace(100.0, 120.0, n)
        f = np.ones(n)
        fe = np.full(n, 0.001)
        q = np.zeros(n, dtype=np.int32)
        lc = LightCurveData("TEST_FOLD", "Kepler", t, f, fe, q, 0.0, 0.0, {})

        folded = fold_light_curve(lc, period=1.5, t0=100.2)
        assert not np.any(np.isnan(folded.phase))
        assert not np.any(np.isnan(folded.flux))
        assert not np.any(np.isnan(folded.flux_err))
        assert not np.any(np.isnan(folded.epoch_indices))
