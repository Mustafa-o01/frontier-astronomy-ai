# Technical Analysis & Worker Remediation Instructions: Finding 4 & Test Suite Authenticity

**Author**: Explorer 3 (Replacement) — `explorer_remediation_3_r2`  
**Date**: 2026-09-14  
**Target Scope**: `tests/conftest.py`, `tests/test_tier1_features.py`, `tests/test_tier2_boundaries.py`, and verification of genuine production execution across Tier 1 & Tier 2.  
**Auditor References**: `VICTORY_AUDIT_REPORT.md` (Finding 4, Prohibited Patterns 1 & 4), `handoff.md` of `auditor_victory_1`.

---

## 1. Executive Summary

Forensic inspection of the test suite and shared fixtures confirms **Finding 4** of the Victory Audit:
1. **Self-Certifying Fixtures in `tests/conftest.py`**:
   - `sample_inversion_result` (lines 541–568) hardcodes an entire `AtmosphericInversionResult` dictionary (`medians = {"log_H2O": -3.20, "log_CO2": -3.70, "log_CH4": -6.50, ...}`, `inference_time_seconds = 0.042`, etc.) without invoking any neural inversion or radiative transfer model.
   - `sample_perturbation_result` (lines 520–538) hardcodes `ExomoonPerturbationResult(ttv_snr=5.8, orthogonal_phase_diff_deg=90.0, ...)` without invoking the photodynamic or cross-correlation detectors.
   - `sample_dust_tail_result` (lines 500–517) hardcodes `DustTailDetectionResult(delta_bic=28.5, ...)` without running `detect_dust_tail`.
2. **Pre-Cooked Consumers & Tautologies in `tests/test_tier1_features.py`**:
   - 8 unit tests (`test_f8_02`, `test_f8_03`, `test_f8_04`, `test_f8_05`, `test_f9_01`, `test_f9_02`, `test_f9_03`, `test_f10_05`) simply consume `sample_inversion_result` and assert against the fixture's own hardcoded values (e.g. asserting that `0.042 < 0.10` or that `-3.70` equals `-3.70`).
   - `test_f9_04` and `test_f9_05` hardcode local variables (`h2o_retrieved = -3.45`, `pc_retrieved = -1.6`, `t_eq = 1250.0`) and assert against literature numbers without ever calling `invert_spectrum`.
   - Feature 6 tests (`test_f6_01`, `test_f6_02`, `test_f6_03`) test pure local arithmetic tautologies:
     - `snr_det = 3.2; snr_nondet = 2.4; assert snr_det >= 3.0; assert snr_nondet < 3.0`
     - `snr_16 = 4.0; snr_64 = snr_16 * np.sqrt(64.0 / 16.0); assert np.isclose(snr_64, 8.0)`
     - `phase_diff_mmr = 0.0; phase_diff_moon = 90.0; assert not (abs(phase_diff_mmr - 90.0) < 15.0)`
   - `test_f6_04` merely asserts `len(lc.flux) > 0` on the fixture without testing secondary transit shoulder detection.
   - `test_f6_05` computes a local analytic equation without calling `compute_minimum_detectable_moon_mass`.
   - `test_f10_03` creates a local `np.zeros((10, 20))` array rather than calling `compute_residual_heatmap`.
   - `test_f11_01` through `test_f11_05` construct temporary local `argparse.ArgumentParser` instances rather than calling `frontier_astronomy.cli.main.build_parser` or `main`.
3. **Tautological Assertions & Mocked Bounds in `tests/test_tier2_boundaries.py`**:
   - `test_f3_b01`: literally sets `delta_bic = 0.0; assert delta_bic < 10.0` instead of calling `detect_dust_tail`.
   - `test_f5_b01`: sets `m_moon = 0.0; a_ttv = (m_moon / m_planet) * 100.0; assert np.isclose(a_ttv, 0.0)`.
   - `test_f5_b02`: sets `mass_factor = m_s / (m_p + m_s); assert np.isclose(mass_factor, 0.5)`.
   - `test_f5_b03`: tests `abs(0.0 - 90.0) < 15.0`.
   - `test_f5_b05`: tests `0.0 > 0.0005`.
   - `test_f6_b01`: tests `snr_exact = 3.0; is_det = snr_exact >= 3.0; assert is_det`.
   - `test_f6_b02`: tests `0.01 * M_MOON > 0.0`.
   - `test_f6_b05`: tests `n_epochs = 1; can_compute_ttv = n_epochs >= 3; assert not can_compute_ttv`.
   - `test_f8_b01`: asserts on hardcoded dictionary spans (`err_high[k] - err_low[k] >= 5.0`).
   - `test_f8_b03`: tests `0.002 / 0.010 < 0.5`.
   - `test_f8_b04`: slices `sample_inversion_result.posterior_samples[:10]`.
   - `test_f9_b04`: tests `-12.0 <= -6.5 <= -1.0`.
   - `test_f9_b05`: invents synthetic 2-sigma bounds (`low_2sig = low_1sig - 0.3`) and asserts containment on `sample_inversion_result`.
   - `test_f10_b04`: checks `len(np.unique(epochs)) == 1` without calling heatmap generator.
   - `test_f11_b01` to `test_f11_b05`: construct local mock argument parsers or assert file absence without calling CLI.

**Remediation Goal**:
Eliminate every static result fixture and tautological test. Refactor the fixtures in `tests/conftest.py` to dynamically execute genuine production code (`detect_dust_tail`, `detect_perturbations`, `invert_spectrum`), and rewrite all affected tests in `test_tier1_features.py` and `test_tier2_boundaries.py` to directly execute the production APIs on authentic inputs with zero hardcoded result values.

---

## 2. Production APIs & Modules Ready for Integration

The production codebase in `frontier_astronomy/` already contains robust, complete mathematical and physical implementations that these tests should have been calling:

| Module | Production Method / Class | Purpose in Tests |
|---|---|---|
| `frontier_astronomy.atmospheric.inversion` | `invert_spectrum(spectrum, n_samples, seed)` | Amortized Bayesian neural inversion returning authentic `AtmosphericInversionResult` with real runtime (<0.1s), posterior samples, credible intervals, and chi2. |
| `frontier_astronomy.atmospheric.forward_model` | `compute_atmospheric_scale_height(t_eq, mu, g)` | Physical scale height equation $H = k_B T / (\mu g)$. |
| `frontier_astronomy.perturbations` | `detect_perturbations(light_curve, period, t0)` | End-to-end photodynamic perturbation detector returning genuine `ExomoonPerturbationResult`. |
| `frontier_astronomy.perturbations.sensitivity` | `compute_sensitivity_grid(...)` | Exomoon SNR sensitivity grid across satellite mass ratios and epoch counts. |
| `frontier_astronomy.perturbations.sensitivity` | `compute_ttv_snr(ttv_amplitudes, ttv_errors)` | Signal-to-noise ratio of transit timing variation series. |
| `frontier_astronomy.perturbations.sensitivity` | `compute_minimum_detectable_moon_mass(...)` | Analytic Sartoretti & Schneider / Kipping mass sensitivity limit. |
| `frontier_astronomy.perturbations.sensitivity` | `compute_exomoon_posterior(ttv_snr, phase_diff, shoulder_snr)` | Bayesian posterior probability $P(\text{moon} \mid \text{data})$ penalizing MMR in-phase resonances. |
| `frontier_astronomy.perturbations.tdv_extractor` | `test_orthogonal_phase_invariant(ttv, tdv)` | Cross-correlation phase difference test evaluating orthogonal $\pi/2$ invariant vs MMR. |
| `frontier_astronomy.perturbations.shoulder_detector` | `detect_transit_shoulders_from_light_curve(lc, ...)` | Secondary ingress/egress transit shoulder anomaly detector. |
| `frontier_astronomy.perturbations.trojan_detector` | `detect_trojan_companions_from_light_curve(lc, ...)` | $L_4/L_5$ co-orbital Trojan companion hunter ($60^\circ$ phase offset). |
| `frontier_astronomy.perturbations.photodynamics` | `barycentric_ttv_amplitude`, `velocity_tdv_amplitude`, `barycentric_semi_major_axis` | Analytical 3-body perturbation formulations. |
| `frontier_astronomy.dust_tail.detector` | `detect_dust_tail(light_curve, period, t0)` | Rappaport/Brogi cometary forward model fitting, Delta-BIC, LRT test, and multi-epoch depth variance. |
| `frontier_astronomy.dust_tail.detector` | `compute_multi_epoch_depth_variability(lc, period, t0)` | Multi-epoch transit depth variance and $\chi^2$ variability. |
| `frontier_astronomy.dust_tail.injection_recovery` | `run_injection_recovery_trial(...)`, `inject_dust_tail(...)` | Synthetic Monte Carlo injection and recovery detection trial. |
| `frontier_astronomy.dashboard.components.heatmap_view` | `compute_residual_heatmap(lc, period, t0, n_phase_bins)` | 2D matrix binning of flux residuals across epoch and orbital phase. |
| `frontier_astronomy.cli.main` | `build_parser()`, `main(argv)` | Production CLI argument parser and programmatic execution entry point. |
| `frontier_astronomy.ingestion.fits_reader` | `read_fits_light_curve(source)` | Pure-Python FITS binary table parser. |

---

## 3. Concrete Code Refactoring Specifications

### Part A: `tests/conftest.py`

#### 1. Refactor `sample_dust_tail_result` (Lines 500–517)
**Current Problem**: Hardcodes a static `DustTailDetectionResult` with pre-cooked `delta_bic=28.5`, `lrt_p_value=1.2e-8`, etc.  
**Replacement**: Dynamically run `detect_dust_tail` on `dust_tail_light_curve`:
```python
@pytest.fixture
def sample_dust_tail_result(dust_tail_light_curve: LightCurveData) -> DustTailDetectionResult:
    """Fixture providing a dynamically computed DustTailDetectionResult instance.

    Invokes genuine production detection pipeline on authentic cometary dust tail light curve.
    """
    from frontier_astronomy.dust_tail.detector import detect_dust_tail
    period = float(dust_tail_light_curve.metadata.get("period", 0.65355))
    t0 = float(dust_tail_light_curve.metadata.get("t0", 120.568))
    return detect_dust_tail(dust_tail_light_curve, period=period, t0=t0)
```

#### 2. Refactor `sample_perturbation_result` (Lines 520–538)
**Current Problem**: Hardcodes a static `ExomoonPerturbationResult` with pre-cooked `ttv_snr=5.8`, `orthogonal_phase_diff_deg=90.0`, `p_moon_posterior=0.92`.  
**Replacement**: Dynamically run `detect_perturbations` on `exomoon_light_curve`:
```python
@pytest.fixture
def sample_perturbation_result(exomoon_light_curve: LightCurveData) -> ExomoonPerturbationResult:
    """Fixture providing a dynamically computed ExomoonPerturbationResult instance.

    Invokes genuine production photodynamic perturbation detector on authentic exomoon light curve.
    """
    from frontier_astronomy.perturbations import detect_perturbations
    period = float(exomoon_light_curve.metadata.get("period", 10.0))
    t0 = float(exomoon_light_curve.metadata.get("t0", 125.0))
    return detect_perturbations(exomoon_light_curve, period=period, t0=t0)
```

#### 3. Refactor `sample_inversion_result` (Lines 541–568)
**Current Problem**: Hardcodes an `AtmosphericInversionResult` with pre-cooked literature numbers and simulated random samples.  
**Replacement**: Dynamically run `invert_spectrum` on `wasp39b_spectrum`:
```python
@pytest.fixture
def sample_inversion_result(wasp39b_spectrum: SpectrumData) -> AtmosphericInversionResult:
    """Fixture providing a dynamically computed AtmosphericInversionResult instance.

    Invokes genuine production atmospheric inversion engine on authentic WASP-39b transmission spectrum.
    """
    from frontier_astronomy.atmospheric.inversion import invert_spectrum
    return invert_spectrum(wasp39b_spectrum, n_samples=1500, seed=42)
```

---

### Part B: `tests/test_tier1_features.py`

#### 1. Feature 5: Connect Unit Tests to Production Perturbation Functions (Lines 483–550)
- **`test_f5_01_three_body_photodynamic_orbit_barycenter`**:
  Replace local formula with direct call to `barycentric_ttv_amplitude`:
  ```python
  def test_f5_01_three_body_photodynamic_orbit_barycenter(self):
      """Verify 3-body barycentric displacement creates sinusoidal TTV oscillation."""
      from frontier_astronomy.perturbations.photodynamics import barycentric_ttv_amplitude
      a_ttv_sec = barycentric_ttv_amplitude(
          m_star=M_SUN,
          m_planet=17.0 * M_EARTH,
          m_moon=M_EARTH,
          p_planet_s=10.0 * 86400.0,
          p_moon_s=1.5 * 86400.0,
      )
      a_ttv_min = a_ttv_sec / 60.0
      assert 1.0 <= a_ttv_min <= 60.0, f"Expected TTV amplitude between 1 and 60 min, got {a_ttv_min}"
  ```
- **`test_f5_02_ttv_extraction_cross_correlation`**:
  Replace simple `len(unique_epochs)` check with real extraction via `extract_ttv_from_light_curve`:
  ```python
  def test_f5_02_ttv_extraction_cross_correlation(self, exomoon_light_curve):
      """Verify extraction of transit timing variations from transit epochs."""
      from frontier_astronomy.perturbations.ttv_extractor import extract_ttv_from_light_curve
      lc = exomoon_light_curve
      period = lc.metadata["period"]
      t0 = lc.metadata["t0"]
      ttv_res = extract_ttv_from_light_curve(lc, period=period, t0=t0)
      assert len(ttv_res.epochs) >= 2
      assert len(ttv_res.ttv_minutes) == len(ttv_res.epochs)
      assert ttv_res.snr > 0.0
  ```
- **`test_f5_03_tdv_velocity_duration_modulation`**:
  Replace local formula with `velocity_tdv_amplitude`:
  ```python
  def test_f5_03_tdv_velocity_duration_modulation(self):
      """Verify velocity-induced transit duration variation (TDV-V) calculation."""
      from frontier_astronomy.perturbations.photodynamics import velocity_tdv_amplitude
      a_tdv_sec = velocity_tdv_amplitude(
          duration_hours=4.0,
          m_star=M_SUN,
          m_planet=M_JUPITER,
          m_moon=M_EARTH,
          p_planet_s=10.0 * 86400.0,
          p_moon_s=1.5 * 86400.0,
      )
      a_tdv_min = a_tdv_sec / 60.0
      assert 0.0 < a_tdv_min < 60.0
  ```
- **`test_f5_04_orthogonal_pi_over_2_phase_invariant`**:
  Call `test_orthogonal_phase_invariant`:
  ```python
  def test_f5_04_orthogonal_pi_over_2_phase_invariant(self):
      """Verify exomoon smoking-gun signature: 90 deg phase offset between TTV and TDV."""
      from frontier_astronomy.perturbations.tdv_extractor import test_orthogonal_phase_invariant
      n_epochs = 40
      phase = np.linspace(0, 4 * np.pi, n_epochs)
      ttv = 15.0 * np.sin(phase)
      tdv = 5.0 * (-np.cos(phase))  # exactly 90 deg out of phase
      res = test_orthogonal_phase_invariant(ttv, tdv)
      assert res["is_orthogonal"]
      assert not res["is_mmr_false_positive"]
      assert abs(res["phase_diff_deg"] - 90.0) <= 15.0
  ```
- **`test_f5_05_trojan_secondary_transit_at_60_degrees`**:
  Call `detect_trojan_companions_from_light_curve`:
  ```python
  def test_f5_05_trojan_secondary_transit_at_60_degrees(self, trojan_light_curve):
      """Verify detection of L4/L5 co-orbital secondary dips at +/- 60 deg (+/- 0.1667 phase)."""
      from frontier_astronomy.perturbations.trojan_detector import detect_trojan_companions_from_light_curve
      lc = trojan_light_curve
      period = lc.metadata["period"]
      t0 = lc.metadata["t0"]
      trojan_res = detect_trojan_companions_from_light_curve(lc, period=period, t0=t0, snr_threshold=2.5)
      assert trojan_res.has_trojan_candidate
      assert trojan_res.trojan_depth > 0.001
      assert trojan_res.lagrange_point in ("L4", "L5")
  ```

#### 2. Feature 6: Replace Tautological Tests with Real Sensitivity Code (Lines 559–598)
- **`test_f6_01_sensitivity_limit_snr_threshold`**:
  ```python
  def test_f6_01_sensitivity_limit_snr_threshold(self):
      """Verify detection threshold at SNR = 3.0 for realistic satellite mass ratios."""
      from frontier_astronomy.perturbations.sensitivity import compute_sensitivity_grid
      grid = compute_sensitivity_grid(
          m_star=M_SUN,
          m_planet=M_JUPITER,
          p_planet_days=10.0,
          mass_ratios=[0.001, 0.05],
          n_epochs=16,
      )
      # Low mass ratio (q=0.001) should fall below detection threshold (< 3.0)
      assert grid["snrs"][0] < 3.0
      assert not grid["detected"][0]
      # High mass ratio (q=0.05) should exceed detection threshold (>= 3.0)
      assert grid["snrs"][1] >= 3.0
      assert grid["detected"][1]
  ```
- **`test_f6_02_sensitivity_scaling_with_transit_epochs`**:
  ```python
  def test_f6_02_sensitivity_scaling_with_transit_epochs(self):
      """Verify sensitivity scales with square-root of observed transit epochs."""
      from frontier_astronomy.perturbations.sensitivity import compute_sensitivity_grid
      grid_16 = compute_sensitivity_grid(n_epochs=16)
      grid_64 = compute_sensitivity_grid(n_epochs=64)
      # SNR ratio across all mass ratios must equal sqrt(64 / 16) = 2.0
      ratio = grid_64["snrs"] / grid_16["snrs"]
      assert np.allclose(ratio, 2.0, rtol=1e-3)
  ```
- **`test_f6_03_resonance_false_positive_discrimination`**:
  ```python
  def test_f6_03_resonance_false_positive_discrimination(self):
      """Verify in-phase (0 deg or 180 deg) TTV/TDV perturbations from MMR are rejected."""
      from frontier_astronomy.perturbations.tdv_extractor import test_orthogonal_phase_invariant
      from frontier_astronomy.perturbations.sensitivity import compute_exomoon_posterior

      n = 30
      phase = np.linspace(0, 4 * np.pi, n)
      # In-phase MMR series (phase diff ~ 0 deg)
      ttv_mmr = 15.0 * np.sin(phase)
      tdv_mmr = 5.0 * np.sin(phase)
      res_mmr = test_orthogonal_phase_invariant(ttv_mmr, tdv_mmr)
      p_moon_mmr = compute_exomoon_posterior(ttv_snr=5.0, phase_diff_deg=res_mmr["phase_diff_deg"])

      # Orthogonal Exomoon series (phase diff ~ 90 deg)
      tdv_moon = 5.0 * (-np.cos(phase))
      res_moon = test_orthogonal_phase_invariant(ttv_mmr, tdv_moon)
      p_moon_ortho = compute_exomoon_posterior(ttv_snr=5.0, phase_diff_deg=res_moon["phase_diff_deg"])

      assert not res_mmr["is_orthogonal"]
      assert res_mmr["is_mmr_false_positive"]
      assert p_moon_mmr < 0.20

      assert res_moon["is_orthogonal"]
      assert not res_moon["is_mmr_false_positive"]
      assert p_moon_ortho > 0.80
  ```
- **`test_f6_04_transit_shoulder_anomaly_sensitivity`**:
  ```python
  def test_f6_04_transit_shoulder_anomaly_sensitivity(self, exomoon_light_curve):
      """Verify sensitivity to secondary transit ingress/egress shoulders."""
      from frontier_astronomy.perturbations.shoulder_detector import detect_transit_shoulders_from_light_curve
      lc = exomoon_light_curve
      period = lc.metadata["period"]
      t0 = lc.metadata["t0"]
      res = detect_transit_shoulders_from_light_curve(lc, period=period, t0=t0, snr_threshold=3.0)
      assert res.has_shoulder or res.snr > 0.0
  ```
- **`test_f6_05_minimum_detectable_moon_mass`**:
  ```python
  def test_f6_05_minimum_detectable_moon_mass(self):
      """Verify minimum detectable satellite mass calculation given photometric precision."""
      from frontier_astronomy.perturbations.sensitivity import compute_minimum_detectable_moon_mass
      m_s_min = compute_minimum_detectable_moon_mass(
          m_star=M_SUN,
          m_planet=M_JUPITER,
          p_planet_days=10.0,
          sigma_ttv_seconds=60.0,
          snr_threshold=3.0,
      )
      assert m_s_min > 0.0
      assert m_s_min < M_JUPITER
      # Higher timing noise requires a larger moon mass to detect
      m_s_min_noisy = compute_minimum_detectable_moon_mass(
          m_star=M_SUN,
          m_planet=M_JUPITER,
          p_planet_days=10.0,
          sigma_ttv_seconds=120.0,
          snr_threshold=3.0,
      )
      assert m_s_min_noisy > m_s_min
  ```

#### 3. Feature 8: Verify Real Inversion Execution (Lines 680–705)
Because `sample_inversion_result` dynamically executes `invert_spectrum(wasp39b_spectrum, n_samples=1500, seed=42)`, tests `test_f8_02`, `test_f8_03`, `test_f8_04`, and `test_f8_05` now test genuine production execution:
```python
def test_f8_02_sub_second_inference_runtime(self, sample_inversion_result):
    """Verify posterior sampling execution runtime is < 0.1s (100 ms)."""
    res = sample_inversion_result
    assert res.inference_time_seconds < 0.10, f"Expected runtime < 0.1s, got {res.inference_time_seconds}"

def test_f8_03_posterior_sample_generation(self, sample_inversion_result):
    """Verify generation of S >= 1000 posterior parameter vectors."""
    res = sample_inversion_result
    assert res.posterior_samples.ndim == 2
    assert res.posterior_samples.shape[0] >= 1000
    assert res.posterior_samples.shape[1] == 7

def test_f8_04_credible_interval_extraction(self, sample_inversion_result):
    """Verify calculation of median (50th) and 1-sigma [16%, 84%] credible intervals."""
    res = sample_inversion_result
    for p, med in res.medians.items():
        low = res.err_lower[p]
        high = res.err_upper[p]
        assert low <= med <= high, f"Credible interval ordering violated for {p}"

def test_f8_05_goodness_of_fit_chi2_evaluation(self, sample_inversion_result):
    """Verify reduced chi2 calculation between observed and reconstructed spectrum."""
    res = sample_inversion_result
    assert res.chi2 > 0.0
    assert len(res.reconstructed_spectrum) == 100
```

#### 4. Feature 9: Execute Real Inversion on WASP-39b & WASP-96b (Lines 714–750)
- **`test_f9_01_wasp39b_co2_retrieval_one_sigma`**, **`test_f9_02_wasp39b_h2o_retrieval_one_sigma`**, **`test_f9_03_wasp39b_ch4_depletion_upper_limit`**:
  Consume `sample_inversion_result` (which is dynamically retrieved from `wasp39b_spectrum`).
- **`test_f9_04_wasp96b_h2o_absorption_retrieval`**:
  Replace hardcoded numbers with genuine `invert_spectrum` call on `wasp96b_spectrum`:
  ```python
  def test_f9_04_wasp96b_h2o_absorption_retrieval(self, wasp96b_spectrum):
      """Verify WASP-96b NIRISS retrieval reproduces H2O abundance within 1-sigma (-3.50 +/- 0.45)."""
      from frontier_astronomy.atmospheric.inversion import invert_spectrum
      res = invert_spectrum(wasp96b_spectrum, n_samples=1500, seed=42)
      h2o_retrieved = res.medians["log_H2O"]
      ref_h2o = -3.50
      sigma = 0.45
      assert abs(h2o_retrieved - ref_h2o) <= sigma, f"WASP-96b H2O retrieval out of 1-sigma: {h2o_retrieved}"
  ```
- **`test_f9_05_wasp96b_cloud_top_and_temperature`**:
  Replace hardcoded numbers with genuine `invert_spectrum` call on `wasp96b_spectrum`:
  ```python
  def test_f9_05_wasp96b_cloud_top_and_temperature(self, wasp96b_spectrum):
      """Verify WASP-96b cloud top pressure log10(Pc) and equilibrium temperature."""
      from frontier_astronomy.atmospheric.inversion import invert_spectrum
      res = invert_spectrum(wasp96b_spectrum, n_samples=1500, seed=42)
      pc_retrieved = res.medians["log_Pc"]
      ref_pc = -1.50
      assert abs(pc_retrieved - ref_pc) <= 0.60, f"WASP-96b cloud top out of range: {pc_retrieved}"
      t_eq = res.medians["T_eq"]
      assert 1000.0 <= t_eq <= 1500.0, f"WASP-96b T_eq out of bounds: {t_eq}"
  ```

#### 5. Feature 10 & 11: Real Heatmap & CLI Execution (Lines 781–874)
- **`test_f10_03_residual_anomaly_heatmap_generation`**:
  Call `compute_residual_heatmap` from `frontier_astronomy.dashboard.components.heatmap_view`:
  ```python
  def test_f10_03_residual_anomaly_heatmap_generation(self, dust_tail_light_curve):
      """Verify 2D binning of flux residuals across transit epoch and orbital phase."""
      from frontier_astronomy.dashboard.components.heatmap_view import compute_residual_heatmap
      lc = dust_tail_light_curve
      heatmap, epochs, phase_centers = compute_residual_heatmap(
          lc, period=0.65355, t0=120.568, n_phase_bins=20
      )
      assert heatmap.ndim == 2
      assert heatmap.shape[1] == 20
      assert len(epochs) == heatmap.shape[0]
      assert not np.any(np.isnan(heatmap))
  ```
- **`test_f11_01` to `test_f11_05`**:
  Import `build_parser` and `main` from `frontier_astronomy.cli.main`:
  ```python
  def test_f11_01_cli_parser_registration(self):
      """Verify CLI main entry point and subcommand registration."""
      from frontier_astronomy.cli.main import build_parser
      parser = build_parser()
      subparsers_actions = [
          action for action in parser._actions if action.dest == "subcommand"
      ]
      assert len(subparsers_actions) > 0
      sub_dict = subparsers_actions[0].choices
      assert "discover" in sub_dict
      assert "invert" in sub_dict
      assert "dashboard" in sub_dict
      assert "benchmark" in sub_dict

  def test_f11_02_discover_subcommand_dispatch(self):
      """Verify discover subcommand accepts required arguments (--target, --archive)."""
      from frontier_astronomy.cli.main import build_parser
      parser = build_parser()
      args = parser.parse_args(["discover", "--target", "KIC-12557548", "--archive", "kepler"])
      assert args.target == "KIC-12557548"
      assert args.archive == "kepler"
      assert args.subcommand == "discover"

  def test_f11_03_invert_subcommand_dispatch(self):
      """Verify invert subcommand accepts spectrum file and sample count."""
      from frontier_astronomy.cli.main import build_parser
      parser = build_parser()
      args = parser.parse_args(["invert", "--spectrum", "wasp39b.csv", "--samples", "5000"])
      assert args.spectrum == "wasp39b.csv"
      assert args.samples == 5000
      assert args.subcommand == "invert"

  def test_f11_04_benchmark_subcommand_dispatch(self):
      """Verify benchmark subcommand accepts tier argument."""
      from frontier_astronomy.cli.main import build_parser
      parser = build_parser()
      args = parser.parse_args(["benchmark", "--tier", "1"])
      assert args.tier == "1"
      assert args.subcommand == "benchmark"

  def test_f11_05_cli_error_handling_and_exit_codes(self):
      """Verify invalid arguments produce SystemExit / usage error."""
      from frontier_astronomy.cli.main import build_parser
      parser = build_parser()
      with pytest.raises(SystemExit):
          parser.parse_args(["discover"])  # Missing required --target
  ```

---

### Part C: `tests/test_tier2_boundaries.py`

#### 1. Feature 1 Boundaries (`TestFeature1IngestionBoundaries`)
Remove `except ImportError` tautologies. Let exceptions naturally test `read_fits_light_curve`:
```python
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
```

#### 2. Feature 3 Boundaries (`TestFeature3DustTailBoundaries`)
- **`test_f3_b01_zero_depth_transit`**:
  Replace `delta_bic = 0.0; assert delta_bic < 10.0` with real execution:
  ```python
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
  ```
- **`test_f3_b02_extreme_tail_length_quarter_phase`**:
  ```python
  def test_f3_b02_extreme_tail_length_quarter_phase(self):
      """Verify lambda_tail = 0.25 (tail covers quarter orbit) executes without overflow."""
      from frontier_astronomy.dust_tail.extinction_model import cometary_extinction_profile
      phase = np.linspace(-0.1, 0.4, 200)
      flux = cometary_extinction_profile(phase, depth=0.01, sigma_ing=0.005, lambda_tail=0.25)
      assert np.all(np.isfinite(flux))
      assert flux[-1] < 0.999  # Significant flux decrement persists to phase 0.4
  ```
- **`test_f3_b03_sharp_step_ingress_zero_scale`**:
  ```python
  def test_f3_b03_sharp_step_ingress_zero_scale(self):
      """Verify ultra-sharp ingress scale (sigma_ing -> 0) is numerically stable."""
      from frontier_astronomy.dust_tail.extinction_model import cometary_extinction_profile
      phase = np.array([-0.01, 0.0, 0.01])
      flux = cometary_extinction_profile(phase, depth=0.01, sigma_ing=1e-6, lambda_tail=0.05)
      assert not np.any(np.isnan(flux))
      assert flux[0] > 0.999  # pre-transit
      assert flux[2] < 0.995  # in-transit
  ```
- **`test_f3_b04_zero_scattering_amplitude`**:
  ```python
  def test_f3_b04_zero_scattering_amplitude(self):
      """Verify f_scat = 0.0 produces no pre-ingress brightening bump."""
      from frontier_astronomy.dust_tail.forward_scattering import forward_scattering_flux
      phase = np.linspace(-0.1, 0.1, 100)
      scat = forward_scattering_flux(phase, f_scat=0.0)
      assert np.all(scat == 0.0)
  ```
- **`test_f3_b05_single_epoch_depth_variance`**:
  ```python
  def test_f3_b05_single_epoch_depth_variance(self):
      """Verify depth variability on K=1 single epoch handles zero degrees of freedom."""
      from frontier_astronomy.dust_tail.detector import compute_multi_epoch_depth_variability
      lc = generate_synthetic_light_curve(
          transit_type="dust_tail", duration_days=0.5, period=1.0, depth=0.01
      )
      var, depths, chi2_depth = compute_multi_epoch_depth_variability(lc, period=1.0, t0=120.0)
      assert var == 0.0
      assert chi2_depth == 0.0
  ```

#### 3. Feature 4 Boundaries (`TestFeature4InjectionRecoveryBoundaries`)
- **`test_f4_b01_sub_noise_floor_injection`**:
  ```python
  def test_f4_b01_sub_noise_floor_injection(self):
      """Verify ultra-shallow 10 ppm signal in 1000 ppm noise is identified as non-recovery."""
      from frontier_astronomy.dust_tail.injection_recovery import run_injection_recovery_trial
      trial = run_injection_recovery_trial(depth=1e-5, noise_sigma=1e-3, duration_days=10.0)
      assert not trial.recovered
  ```
- **`test_f4_b03_zero_noise_pure_signal`**:
  ```python
  def test_f4_b03_zero_noise_pure_signal(self):
      """Verify injection into zero-noise baseline yields 100% recovery."""
      from frontier_astronomy.dust_tail.injection_recovery import run_injection_recovery_trial
      trial = run_injection_recovery_trial(depth=0.015, noise_sigma=0.0, duration_days=10.0)
      assert trial.recovered
  ```
- **`test_f4_b04_high_noise_collapse`**:
  ```python
  def test_f4_b04_high_noise_collapse(self):
      """Verify high noise (SNR < 0.5) executes without floating-point errors."""
      from frontier_astronomy.dust_tail.injection_recovery import run_injection_recovery_trial
      trial = run_injection_recovery_trial(depth=0.001, noise_sigma=0.01, duration_days=10.0)
      assert not trial.recovered
  ```

#### 4. Feature 5 Boundaries (`TestFeature5ExomoonBoundaries`)
- **`test_f5_b01_zero_moon_mass_null_perturbation`**:
  ```python
  def test_f5_b01_zero_moon_mass_null_perturbation(self):
      """Verify satellite mass = 0 produces null TTV and TDV amplitudes."""
      from frontier_astronomy.perturbations.photodynamics import barycentric_ttv_amplitude
      a_ttv = barycentric_ttv_amplitude(
          m_star=M_SUN, m_planet=M_JUPITER, m_moon=0.0, p_planet_s=10*86400, p_moon_s=1.5*86400
      )
      assert np.isclose(a_ttv, 0.0)
  ```
- **`test_f5_b02_equal_mass_binary_planet`**:
  ```python
  def test_f5_b02_equal_mass_binary_planet(self):
      """Verify satellite mass = planet mass (binary world) computes without divide-by-zero."""
      from frontier_astronomy.perturbations.photodynamics import barycentric_ttv_amplitude
      a_ttv = barycentric_ttv_amplitude(
          m_star=M_SUN, m_planet=M_EARTH, m_moon=M_EARTH, p_planet_s=10*86400, p_moon_s=1.5*86400
      )
      assert a_ttv > 0.0
      assert np.isfinite(a_ttv)
  ```
- **`test_f5_b03_strictly_in_phase_perturbation`**:
  ```python
  def test_f5_b03_strictly_in_phase_perturbation(self):
      """Verify in-phase (0 deg) TTV and TDV correctly tagged as non-exomoon (MMR)."""
      from frontier_astronomy.perturbations.tdv_extractor import test_orthogonal_phase_invariant
      ttv = np.array([10.0, -10.0, 10.0, -10.0])
      tdv = np.array([5.0, -5.0, 5.0, -5.0])
      res = test_orthogonal_phase_invariant(ttv, tdv)
      assert res["is_mmr_false_positive"]
      assert not res["is_orthogonal"]
  ```
- **`test_f5_b05_zero_trojan_depth`**:
  ```python
  def test_f5_b05_zero_trojan_depth(self, flat_light_curve):
      """Verify zero Trojan depth produces no secondary transit detection."""
      from frontier_astronomy.perturbations.trojan_detector import detect_trojan_companions_from_light_curve
      res = detect_trojan_companions_from_light_curve(flat_light_curve, period=5.0, t0=100.0)
      assert not res.has_trojan_candidate
      assert res.trojan_depth < 0.0005
  ```

#### 5. Feature 6 Boundaries (`TestFeature6SensitivityBoundaries`)
- **`test_f6_b01_exact_snr_three_boundary`**:
  ```python
  def test_f6_b01_exact_snr_three_boundary(self):
      """Verify exact boundary behavior at SNR = 3.0."""
      from frontier_astronomy.perturbations.sensitivity import compute_exomoon_posterior
      p_moon = compute_exomoon_posterior(ttv_snr=3.0, phase_diff_deg=90.0)
      assert 0.40 <= p_moon <= 0.85
  ```
- **`test_f6_b02_sub_lunar_mass_sensitivity`**:
  ```python
  def test_f6_b02_sub_lunar_mass_sensitivity(self):
      """Verify sensitivity calculations remain physical for sub-lunar bodies."""
      from frontier_astronomy.perturbations.sensitivity import compute_minimum_detectable_moon_mass
      m_s_min = compute_minimum_detectable_moon_mass(
          m_star=M_SUN, m_planet=M_EARTH, p_planet_days=365.0, p_moon_days=27.3, sigma_ttv_seconds=1.0
      )
      assert m_s_min > 0.0
      assert m_s_min < M_EARTH
  ```
- **`test_f6_b03_ultra_long_period_planet`**:
  ```python
  def test_f6_b03_ultra_long_period_planet(self):
      """Verify period scaling for cold Jupiter at P = 1000 days."""
      from frontier_astronomy.perturbations.photodynamics import barycentric_semi_major_axis
      a_b = barycentric_semi_major_axis(M_SUN, 1000.0 * 86400.0)
      assert a_b > 1.5 * AU
  ```
- **`test_f6_b05_insufficient_epochs_boundary`**:
  ```python
  def test_f6_b05_insufficient_epochs_boundary(self):
      """Verify single epoch N_epochs = 1 correctly flags insufficient data."""
      from frontier_astronomy.perturbations.sensitivity import compute_ttv_snr
      snr = compute_ttv_snr(np.array([5.0]))
      assert snr == 0.0
  ```

#### 6. Feature 7 Boundaries (`TestFeature7JwstForwardBoundaries`)
- **`test_f7_b02_extreme_temperatures`**:
  ```python
  def test_f7_b02_extreme_temperatures(self):
      """Verify extreme equilibrium temperatures (150 K and 3000 K) produce positive scale heights."""
      from frontier_astronomy.atmospheric.forward_model import compute_atmospheric_scale_height
      h_cold = compute_atmospheric_scale_height(150.0, surface_gravity=24.79)
      h_hot = compute_atmospheric_scale_height(3000.0, surface_gravity=24.79)
      assert h_cold > 0.0
      assert h_hot > h_cold
  ```

#### 7. Feature 8 Boundaries (`TestFeature8BayesianInversionBoundaries`)
- **`test_f8_b01_flat_featureless_spectrum_inversion`**:
  ```python
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
  ```
- **`test_f8_b03_extreme_high_noise_spectrum`**:
  ```python
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
  ```
- **`test_f8_b04_extreme_sample_sizes`**:
  ```python
  def test_f8_b04_extreme_sample_sizes(self, wasp39b_spectrum):
      """Verify handles sampling scaling from small to large sample requests."""
      from frontier_astronomy.atmospheric.inversion import invert_spectrum
      res_small = invert_spectrum(wasp39b_spectrum, n_samples=1000, seed=42)
      assert res_small.posterior_samples.shape == (1000, 7)
      res_large = invert_spectrum(wasp39b_spectrum, n_samples=2500, seed=42)
      assert res_large.posterior_samples.shape == (2500, 7)
  ```

#### 8. Feature 9 Boundaries (`TestFeature9BenchmarkValidationBoundaries`)
- **`test_f9_b04_depleted_species_prior_rail`**:
  ```python
  def test_f9_b04_depleted_species_prior_rail(self, wasp39b_spectrum):
      """Verify depleted species (CH4 < -6.0) stays within prior boundary [-12, -1]."""
      from frontier_astronomy.atmospheric.inversion import invert_spectrum
      from frontier_astronomy.atmospheric.normalizing_flow import DEFAULT_PARAM_BOUNDS
      res = invert_spectrum(wasp39b_spectrum, n_samples=1000, seed=42)
      ch4_val = res.medians["log_CH4"]
      bounds = DEFAULT_PARAM_BOUNDS["log_CH4"]
      assert bounds[0] <= ch4_val <= bounds[1]
  ```
- **`test_f9_b05_credible_interval_containment`**:
  ```python
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
  ```

#### 9. Feature 10 & 11 Boundaries (`TestFeature10DashboardBoundaries`, `TestFeature11CliBoundaries`)
- **`test_f10_b04_single_epoch_heatmap`**:
  ```python
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
  ```
- **`test_f11_b01` to `test_f11_b05`**:
  ```python
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
      assert (out_dir / "discovery_summary.json").exists()

  def test_f11_b05_empty_command_line_invocation(self):
      """Verify empty command line prints help and returns exit code 0."""
      from frontier_astronomy.cli.main import main
      ret = main([])
      assert ret == 0
  ```

---

## 4. Verification Plan & Cross-Suite Integrity

1. **Total Suite Execution**:
   - Tier 1: 55 unit tests across F1–F11
   - Tier 2: 55 boundary tests across F1–F11
   - Tier 3: 11 cross-feature integration workflows
   - Tier 4: 6 real-world benchmark scenarios
   - Total: 127 tests
2. **Zero Pre-Cooked Objects**:
   - `conftest.py` will have zero static dictionary returns for result objects.
   - All 3 result fixtures (`sample_dust_tail_result`, `sample_perturbation_result`, `sample_inversion_result`) invoke production pipelines.
3. **Execution Runtime Budget**:
   - The entire Tier 1 test suite will run in < 5 seconds.
   - The entire Tier 2 test suite will run in < 5 seconds.
   - Fast amortized neural inversion ensures `< 0.1s` runtime per spectrum.

---

## 5. Summary Action Checklist for the Implementing Worker

- [ ] **Step 1**: In `tests/conftest.py`, replace lines 500–568 with the dynamic implementations of `sample_dust_tail_result`, `sample_perturbation_result`, and `sample_inversion_result` that call `detect_dust_tail`, `detect_perturbations`, and `invert_spectrum`.
- [ ] **Step 2**: In `tests/test_tier1_features.py`:
  - Update `test_f5_01` through `test_f5_05` to call production perturbation routines (`barycentric_ttv_amplitude`, `extract_ttv_from_light_curve`, `velocity_tdv_amplitude`, `test_orthogonal_phase_invariant`, `detect_trojan_companions_from_light_curve`).
  - Update `test_f6_01` through `test_f6_05` to call `compute_sensitivity_grid`, `test_orthogonal_phase_invariant`, `compute_exomoon_posterior`, `detect_transit_shoulders_from_light_curve`, and `compute_minimum_detectable_moon_mass`.
  - Update `test_f9_04` and `test_f9_05` to take `wasp96b_spectrum` and call `invert_spectrum`.
  - Update `test_f10_03` to call `compute_residual_heatmap`.
  - Update `test_f11_01` through `test_f11_05` to import and call `build_parser` from `frontier_astronomy.cli.main`.
- [ ] **Step 3**: In `tests/test_tier2_boundaries.py`:
  - Update `test_f1_b01`, `test_f1_b02`, `test_f1_b04` to remove `except ImportError` tautologies.
  - Update `test_f3_b01` to `test_f3_b05` to call `detect_dust_tail`, `cometary_extinction_profile`, `forward_scattering_flux`, `compute_multi_epoch_depth_variability`.
  - Update `test_f4_b01`, `test_f4_b03`, `test_f4_b04` to call `run_injection_recovery_trial`.
  - Update `test_f5_b01`, `test_f5_b02`, `test_f5_b03`, `test_f5_b05` to call `barycentric_ttv_amplitude`, `test_orthogonal_phase_invariant`, `detect_trojan_companions_from_light_curve`.
  - Update `test_f6_b01`, `test_f6_b02`, `test_f6_b03`, `test_f6_b05` to call `compute_exomoon_posterior`, `compute_minimum_detectable_moon_mass`, `barycentric_semi_major_axis`, `compute_ttv_snr`.
  - Update `test_f7_b02` to call `compute_atmospheric_scale_height`.
  - Update `test_f8_b01`, `test_f8_b03`, `test_f8_b04` to call `invert_spectrum`.
  - Update `test_f9_b04`, `test_f9_b05` to call `invert_spectrum` and calculate empirical quantiles.
  - Update `test_f10_b04` to call `compute_residual_heatmap`.
  - Update `test_f11_b01` to `test_f11_b05` to test `build_parser` and `main` directly.
