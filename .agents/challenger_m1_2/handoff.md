# Milestone 1 Preprocessing Empirical Challenge Report

**Agent**: `challenger_m1_2` (Preprocessing & Detrending Challenger)  
**Date**: 2026-09-14  
**Project**: Frontier Astronomy AI Discovery Suite  
**Working Directory**: `G:\frontier_astronomy_ai\.agents\challenger_m1_2`  
**Test Suite Created**: `G:\frontier_astronomy_ai\tests\test_adversarial_preprocessing.py`  
**Target Module**: `frontier_astronomy.core.preprocessing` & `frontier_astronomy.core.math_utils`

---

## 1. Observation

### 1.1 Empirical Verification Commands and Verbatim Outputs

#### Observation 1: Destruction of Deep Cometary Transit Troughs by `asymmetric_mad_clip`
- **Source Target**: `frontier_astronomy/core/preprocessing.py`, lines 112–119:
  ```python
  mad_val = median_absolute_deviation(residuals)
  ...
  keep_mask = (residuals >= -sigma_low * mad_val) & (residuals <= sigma_high * mad_val)
  ```
- **Empirical Execution Command**:
  ```python
  import numpy as np
  from frontier_astronomy.core.preprocessing import asymmetric_mad_clip

  n = 2000
  t = np.linspace(100, 140, n)
  noise = np.random.default_rng(42).normal(0, 0.0003, n) # 300 ppm Kepler noise
  f = 1.0 + noise
  f[500:508] -= np.array([0.004, 0.009, 0.012, 0.010, 0.007, 0.004, 0.002, 0.001])
  mask = asymmetric_mad_clip(t, f, window_length=101, sigma_high=3.5, sigma_low=6.0)
  ```
- **Verbatim Result**:
  ```
  Total transit points: 8
  Transit points clipped by asymmetric_mad_clip: 7 of 8
  Clipped indices: [0 1 2 3 4 5 6]
  ```
  *Result*: 87.5% of transit cadences were purged as "negative outliers".

#### Observation 2: 100% Elimination of Transits in Bundled Real Benchmark `KIC 12557548`
- **Source Target**: `frontier_astronomy/core/preprocessing.py`, line 470 (`asymmetric_mad_clip` inside `preprocess_light_curve`).
- **Empirical Execution Command**:
  ```python
  from frontier_astronomy.ingestion.catalog import load_benchmark_light_curve
  from frontier_astronomy.core.preprocessing import preprocess_light_curve, asymmetric_mad_clip

  lc = load_benchmark_light_curve('KIC 12557548')
  clip_mask = asymmetric_mad_clip(lc.time, lc.flux, lc.flux_err)
  lc_clean = preprocess_light_curve(lc, clip_outliers=True)
  ```
- **Verbatim Result**:
  ```
  Raw KIC 12557548 points: 4503
  Min flux raw: 0.9837854885577434
  Deep transit points (<0.99) in raw data: 19
  Deep transit points clipped by asymmetric_mad_clip: 19
  Preprocessed points remaining: 4051
  Deep transit points (<0.99) remaining in preprocessed: 0
  ```
  *Result*: 100% (19 of 19) of genuine deep transit cadences in the primary disintegrating exoplanet benchmark were permanently purged.

#### Observation 3: 100% Elimination of Transits and Forward Scattering in Synthetic Dust Tails
- **Source Target**: `frontier_astronomy/ingestion/synthetic_generator.py` and `asymmetric_mad_clip`.
- **Empirical Execution Command**:
  ```python
  from frontier_astronomy.ingestion.synthetic_generator import generate_disintegrating_dust_tail_light_curve
  from frontier_astronomy.core.preprocessing import asymmetric_mad_clip

  lc = generate_disintegrating_dust_tail_light_curve(target_id='SYNTH', duration_days=20.0, depth=0.010, forward_scat_amp=0.0020, noise_ppm=250.0, seed=42)
  ```
- **Verbatim Result**:
  ```
  Total cadences: 1077
  Deep transit cadences (flux < 0.995): 44
  Deep transit cadences CLIPPED by asymmetric_mad_clip: 44 / 44 (100.0%)
  Deep transit cadences remaining after preprocess_light_curve: 0
  Forward scattering cadences (> 1.0015): 14
  Forward scattering cadences CLIPPED: 14 / 14 (100.0%)
  ```
  *Result*: Both the transit trough (100%) and the Mie forward-scattering bump (100%) are purged.

#### Observation 4: Integer Overflow in `epoch_split` for Short Periods ($P < 0.1$ d)
- **Source Target**: `frontier_astronomy/core/preprocessing.py`, line 303:
  ```python
  epochs = np.round((t - t0) / period).astype(np.int32)
  ```
- **Empirical Execution Command**:
  ```python
  from frontier_astronomy.core.preprocessing import epoch_split
  t = np.array([2455000.0, 2455001.0])
  ep = epoch_split(t, 0.0005, t0=0.0)
  ```
- **Verbatim Result**:
  ```
  G:\frontier_astronomy_ai\frontier_astronomy\core\preprocessing.py:303: RuntimeWarning: invalid value encountered in cast
    epochs = np.round((t - t0) / period).astype(np.int32)
  t=2455000, P=0.0005 -> epoch: [-2147483648 -2147483648]
  ```
  *Result*: For ultra-short periods ($P = 0.0005$ d $\approx 43$ s) with BJD timestamps ($2.455 \times 10^6$), $(t - t0) / P = 4.91 \times 10^9 > 2^{31} - 1$, resulting in 32-bit integer overflow and collapsing 1,000 distinct epochs into $-2147483648$.

#### Observation 5: Boundary Distortion and False Dips Across Observation Gaps
- **Source Target**: `frontier_astronomy/core/preprocessing.py`, lines 189–221 (`iterative_savgol_detrend`).
- **Empirical Execution Command**:
  ```python
  # 60-day gap between Quarter 1 (flux=1.05) and Quarter 2 (flux=0.95)
  t = np.concatenate([np.linspace(100, 110, 500), np.linspace(180, 190, 500)])
  f = np.concatenate([np.full(500, 1.05), np.full(500, 0.95)])
  fn, cont = iterative_savgol_detrend(t, f, window_days=1.0)
  ```
- **Verbatim Result**:
  ```
  Normalized flux around gap (index 495 to 505):
  [1.02980172 1.03409015 1.03849647 1.04299977 1.04757843 0.95199954
   0.95621691 0.9604394  0.96464444 0.96880872]
  ```
  *Result*: Savitzky-Golay filtering across inter-quarter gaps produces a $-4.8\%$ artificial transit-like dip at the gap boundary.

#### Observation 6: Unsorted Timestamps Corrupt `np.interp` in `iterative_savgol_detrend`
- **Source Target**: `frontier_astronomy/core/preprocessing.py`, lines 214–218:
  ```python
  f_clean[masked_indices] = np.interp(
      t[masked_indices],
      t[unmasked_indices],
      f_clean[unmasked_indices],
  )
  ```
- **Verbatim Result**: `np.interp` with unsorted `xp` produces non-interpolated arbitrary values (`[50., 30.]` instead of `[25., 35.]`) because `np.interp` requires `xp` to be monotonically increasing.

#### Observation 7: Continuum NaN Contamination Propagates to Uncertainties
- **Source Target**: `frontier_astronomy/core/preprocessing.py`, lines 221, 249–256, and line 491:
  ```python
  # In iterative_savgol_detrend:
  normalized_flux = f / continuum
  bad_idx = ~np.isfinite(normalized_flux)
  if np.any(bad_idx):
      normalized_flux[bad_idx] = 1.0
  return normalized_flux, continuum
  ...
  # In preprocess_light_curve:
  fe_norm = fe / continuum
  ```
- **Verbatim Result**: If an uncleaned NaN enters `savgol_filter`, SciPy expands the NaN across the entire filter window. While `normalized_flux` replaces non-finite values with 1.0, `continuum` is returned containing NaNs. Line 491 calculates `fe_norm = fe / continuum`, injecting NaNs directly into `lc.flux_err`.

#### Observation 8: Degenerate Period Guards Miss NaN and Inf
- **Source Target**: `frontier_astronomy/core/preprocessing.py`, lines 276, 300:
  ```python
  if period <= 0:
      raise ValueError(...)
  ```
- **Verbatim Result**:
  - `period = float('nan')`: `nan <= 0` evaluates to `False`. `phase_fold` returns all NaNs; `epoch_split` returns `[-2147483648, ...]`.
  - `period = float('inf')`: `inf <= 0` evaluates to `False`. `phase_fold` returns all zeros.

---

## 2. Logic Chain

1. **Premise on Outlier Clipping**: The stated design intent of `asymmetric_mad_clip` in `PROJECT.md` line 75 and `preprocessing.py` line 82 is to apply a conservative threshold ($\sigma_{\rm low} = 6.0$) to "protect transits" while clipping positive stellar flares ($\sigma_{\rm high} = 3.5$).
2. **Mathematical Reality of Planetary & Dust Tail Transits**:
   - For Kepler space photometry, typical out-of-transit photometric scatter is $\sigma \approx 250 - 300\text{ ppm}$ ($0.00025 - 0.00030$).
   - The MAD of normal residuals evaluates to $\text{MAD} \approx \sigma \approx 0.00030$.
   - The negative rejection boundary is therefore $-6.0 \times \text{MAD} \approx -0.0018$ (1,800 ppm, or 0.18% depth).
   - In contrast, genuine disintegrating exoplanet transits (e.g., KIC 12557548) and gas giant transits exhibit depths of $0.5\% - 2.0\%$ (5,000 to 20,000 ppm).
   - Therefore, every cadence within a genuine transit trough has $\text{residual} = -0.012 < -0.0018$.
   - *Direct Consequence*: `asymmetric_mad_clip` flags the transit points as negative outliers and excises them.
3. **Why Worker Tests Passed**: Worker's unit test `test_asymmetric_mad_clip_protects_transits` passed solely because it tested a synthetic vector with *zero noise* (`f = np.ones(n)`). With no noise, the baseline MAD was 0.0, which triggered a fallback to `np.nanstd(residuals)` computed over the *entire array including the transit itself*. The transit points artificially inflated the standard deviation to $\sim 0.0022$, creating a threshold of $6 \times 0.0022 = 0.0132 > 0.012$. As soon as realistic observational noise is introduced, the MAD reflects the true noise floor and the transit is wiped out.
4. **Forward Scattering Bump Erasure**: The Mie/Henyey-Greenstein forward-scattering peak in disintegrating exoplanets has an amplitude of $\approx 1,000 - 3,000\text{ ppm}$. Since $\sigma_{\rm high} = 3.5$, the positive threshold is $3.5 \times 250\text{ ppm} = 875\text{ ppm}$. Because $2,000\text{ ppm} > 875\text{ ppm}$, the forward scattering peak is flagged as a stellar flare and clipped.
5. **Short Period Integer Overflow**: Astronomical timestamps from NASA Kepler/TESS archives are often expressed in BJD ($\sim 2.455 \times 10^6$ days) or BKJD/BTJD. For ultra-short period candidates ($P < 0.1$ d, or exploratory grids down to $P \sim 0.0005$ d), $(t - t0) / P$ exceeds the maximum representable 32-bit signed integer ($2.147 \times 10^9$), triggering silent wraparound in NumPy's `.astype(np.int32)`.

---

## 3. Caveats

1. **Pre-whitening vs. Phase Masking**: If transit ephemerides ($P, t_0, T_{\rm dur}$) are already known *a priori*, transit masking can be passed to `iterative_savgol_detrend`. However, `asymmetric_mad_clip` currently does not accept transit priors, so calling `preprocess_light_curve(lc, clip_outliers=True)` blindly executes outlier rejection before detrending.
2. **Clean Quality Protection**: `clean_quality(strict=True)` successfully guards against raw non-finite inputs, zeros, and negative fluxes, protecting `preprocess_light_curve` as long as `clean_quality` is called first. The vulnerability occurs if functions are invoked directly or if `strict_quality=False`.

---

## 4. Conclusion & Actionable Mitigations

### Overall Assessment: HIGH RISK / DEFECT CONFIRMED

While `clean_quality`, `inverse_variance_bin`, and Parquet I/O perform robustly on nominal datasets, the preprocessing engine suffers from **two critical domain failures** and **three numerical boundary bugs** that directly threaten the core scientific discovery mission:

1. **Critical Defect 1: Transits excised by default outlier clipping**.
   - *Actionable Mitigation for Milestone 2*: Modify `preprocess_light_curve` so that `clip_outliers=False` by default for transit search pipelines, OR update `asymmetric_mad_clip` to accept `(period, t0, duration_days)` and exclude in-transit cadences from clipping, OR use a single-cadence spike filter (e.g. require single isolated points) rather than clipping contiguous transit troughs.
2. **Critical Defect 2: Forward scattering peaks destroyed**.
   - *Actionable Mitigation for Milestone 2*: Mask the orbital phase window immediately preceding ingress $[-2 \times T_{\rm dur}, 0]$ from positive flare rejection.
3. **High Defect 3: Integer overflow in `epoch_split`**.
   - *Actionable Mitigation for Milestone 2*: Cast epochs to `np.int64` instead of `np.int32`, and check `if not np.isfinite(period) or period <= 0:` in both `phase_fold` and `epoch_split`.
4. **High Defect 4: Detrending artifacts across gaps**.
   - *Actionable Mitigation for Milestone 2*: In `iterative_savgol_detrend`, split light curves into continuous segments whenever $\Delta t > 3 \times \text{median}(\Delta t)$ or $\Delta t > 1.0\text{ day}$, detrending each contiguous segment independently.
5. **Medium Defect 5: Continuum NaN contamination in uncertainties**.
   - *Actionable Mitigation for Milestone 2*: In `iterative_savgol_detrend`, apply `continuum[~np.isfinite(continuum)] = np.nanmedian(f)` before returning, and in `preprocess_light_curve` sanitize `fe_norm[~np.isfinite(fe_norm)] = fe[~np.isfinite(fe_norm)]`.

---

## 5. Verification Method

To independently verify these findings and reproduce all failure modes:

1. **Inspect Adversarial Test Suite**:
   Review the newly created test suite at:
   `G:\frontier_astronomy_ai\tests\test_adversarial_preprocessing.py`
2. **Run Pytest Adversarial Suite**:
   ```powershell
   python -m pytest tests/test_adversarial_preprocessing.py -v --tb=short
   ```
   *Expected Result*: All 18 tests execute, demonstrating reproducible assertions on:
   - `test_asymmetric_mad_clip_erases_genuine_dust_tail_transits`: confirms $\ge 5$ of 8 transit cadences clipped.
   - `test_kic_12557548_real_benchmark_transit_destruction`: confirms 19 deep transit cadences reduced to 0.
   - `test_synthetic_dust_tail_100_percent_clipping`: confirms $>90\%$ deep cadences clipped.
   - `test_forward_scattering_peak_clipping`: confirms $>80\%$ forward scattering cadences clipped.
   - `test_ultra_short_period_int32_overflow_in_epoch_split`: confirms int32 overflow to -2147483648.
   - `test_massive_inter_quarter_gap_boundary_artifact`: confirms false dip $< 0.98$ at gap boundary.
   - `test_degenerate_period_nan_and_inf`: confirms lack of NaN/Inf validation.
