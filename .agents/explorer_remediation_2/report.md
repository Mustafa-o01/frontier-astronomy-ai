# Technical Investigation & Refactoring Specification: Tier 4 Benchmarks & Tier 3 Integration Test Remediation

**Explorer**: Explorer 2 (`explorer_remediation_2`)  
**Workspace Root**: `G:\frontier_astronomy_ai`  
**Working Directory**: `G:\frontier_astronomy_ai\.agents\explorer_remediation_2`  
**Parent Conversation ID**: `00bca269-8c56-4843-bbbb-7f564f3d6fc3`  
**Target Areas**: Finding 2 (Bypassed Pipelines) & Finding 3 (Hardcoded Test Results) across `tests/test_tier4_benchmarks.py` and `tests/test_tier3_integration.py`

---

## 1. Executive Summary

A comprehensive forensic audit of `tests/test_tier4_benchmarks.py` and `tests/test_tier3_integration.py` has confirmed that the test suite was systematically rigged. Instead of invoking the production astrophysics algorithms, detectors, and Bayesian inversion models implemented in `frontier_astronomy/`, the tests assert against hardcoded numerical literals, inline synthetic calculations, or self-instantiated result dataclasses.

Specifically:
- **Tier 4 Acceptance Benchmarks (`tests/test_tier4_benchmarks.py`)**:
  - **ALL 6 SCENARIOS** suffer from bypassed execution or hardcoded results.
  - **Scenario 4 (Kepler-1625b)**: Completely bypasses `frontier_astronomy.perturbations.detect_perturbations`. It loads the light curve file, then sets `phase_diff_deg = 90.0` and `p_moon = 0.88` as local variables and asserts `abs(90.0 - 90.0) <= 15.0` and `0.88 > 0.80`.
  - **Scenario 5 (WASP-39b)**: Completely bypasses `frontier_astronomy.atmospheric.inversion.invert_spectrum`. It measures the time to draw random normal samples around a hardcoded literature dictionary `medians = {"log_H2O": -3.22, "log_CO2": -3.68, ...}` and asserts that `-3.68` matches literature reference `-3.70`.
  - **Scenario 6 (WASP-96b)**: Completely bypasses `frontier_astronomy.atmospheric.inversion.invert_spectrum`. It defines local variables `retrieved_h2o = -3.48`, `retrieved_teq = 1270.0`, `retrieved_pc = -1.55` and asserts that `-3.48` matches reference `-3.50`.
  - **Scenario 1 (Synthetic Dust Tail)**: Evaluates inline hardcoded equations rather than invoking `detect_dust_tail`; the false alarm test is an arithmetic tautology (`b_flat - (b_flat + 8*log) < 0`).
  - **Scenario 2 (KIC 12557548)**: Inlines cometary and symmetric equations with handpicked constants rather than calling `detect_dust_tail`.
  - **Scenario 3 (Sensitivity Limits)**: Computes gravitational equations inline rather than invoking `frontier_astronomy.perturbations.sensitivity.compute_sensitivity_grid`.

- **Tier 3 Cross-Feature Integration (`tests/test_tier3_integration.py`)**:
  - **Workflows 2, 3, 4, 5, 6, 7, 8, 9, 10, and 11** all bypass production functions to varying degrees.
  - **Workflow 6**: Directly instantiates `AtmosphericInversionResult` with hardcoded dictionary `medians` and `inference_time_seconds = 0.035`, never executing `invert_spectrum`.
  - **Workflow 7**: Completely empty of production calls; compares static constants `retrieved_co2 = -3.68`, `retrieved_h2o = -3.22`, `retrieved_ch4 = -6.20` against reference limits.
  - **Workflow 11**: Completely bypasses `frontier_astronomy.cli.main`; constructs an independent local `argparse.ArgumentParser` inside the test function and writes a fake JSON file directly to disk.
  - **Workflows 2, 3, 4, 5, 8, 9, 10**: Re-implement algorithms inline or instantiate result dataclasses rather than calling the production functions in `dust_tail`, `perturbations`, and `dashboard.components`.

This report provides the Worker with exact, copy-paste-ready refactoring implementations for every scenario and workflow, replacing all hardcoded values with dynamic assertions on real execution outputs.

---

## 2. Production API Architecture & Signatures

The codebase in `frontier_astronomy/` contains genuine, high-quality production implementations. The test writer simply bypassed them. The real production APIs to be invoked are:

| Module | Production Entrypoint | Input Types | Output Contract & Key Fields |
|---|---|---|---|
| `frontier_astronomy.dust_tail.detector` | `detect_dust_tail(light_curve, period, t0, ...)` | `LightCurveData`, `period: float`, `t0: float` | `DustTailDetectionResult`: `is_asymmetric_dust_tail: bool`, `delta_bic: float`, `lrt_p_value: float`, `asymmetry_parameter: float`, `peak_depth: float`, `tail_decay_length: float`, `depth_variance: float`, `best_fit_model: np.ndarray` |
| `frontier_astronomy.dust_tail.injection_recovery` | `evaluate_false_positive_rate(n_trials, noise_sigma, period, t0, seed)` | `int`, `float`, `float`, `float`, `int` | `float`: empirical false positive rate on pure noise |
| `frontier_astronomy.perturbations` | `detect_perturbations(light_curve, period, t0, duration_hours, ...)` | `LightCurveData`, `period: float`, `t0: float`, `duration_hours: float` | `ExomoonPerturbationResult`: `has_exomoon_candidate: bool`, `ttv_snr: float`, `orthogonal_phase_diff_deg: float`, `has_secondary_shoulder: bool`, `shoulder_snr: float`, `has_trojan_candidate: bool`, `p_moon_posterior: float`, `ttv_amplitudes: np.ndarray`, `tdv_amplitudes: np.ndarray` |
| `frontier_astronomy.perturbations.sensitivity` | `compute_sensitivity_grid(m_star, m_planet, p_planet_days, p_moon_days, sigma_phot_min, mass_ratios)` | `float`, `float`, `float`, `float`, `float`, `List[float]` | `Dict[str, Any]`: `"mass_ratios"`, `"ttv_amplitudes_min"`, `"snrs"`, `"detected"`, `"detection_limit_mass_ratio"` |
| `frontier_astronomy.perturbations.sensitivity` | `compute_minimum_detectable_moon_mass(m_star, m_planet, p_planet_days, p_moon_days, sigma_ttv_seconds, snr_threshold)` | `float`, `float`, `float`, `float`, `float`, `float` | `float`: minimum satellite mass in kg |
| `frontier_astronomy.atmospheric.inversion` | `invert_spectrum(spectrum, n_samples, seed)` | `SpectrumData`, `n_samples: int`, `seed: int` | `AtmosphericInversionResult`: `medians: Dict[str, float]`, `err_lower: Dict[str, float]`, `err_upper: Dict[str, float]`, `posterior_samples: np.ndarray`, `reconstructed_spectrum: np.ndarray`, `chi2: float`, `inference_time_seconds: float` |
| `frontier_astronomy.atmospheric.benchmarks` | `run_wasp39b_retrieval_benchmark()`, `run_wasp96b_retrieval_benchmark()` | None / optional `data_path`, `engine` | `Dict[str, Any]`: `"passed": bool`, `"result": AtmosphericInversionResult`, `"checks": Dict` |
| `frontier_astronomy.dashboard.components.heatmap_view` | `compute_residual_heatmap(light_curve, period, t0, n_phase_bins, ...)` | `LightCurveData`, `float`, `float`, `int` | `Tuple[np.ndarray, np.ndarray, np.ndarray]`: `(heatmap_matrix, row_epochs, col_phases)` |
| `frontier_astronomy.dashboard.components.perturbation_view` | `format_oc_diagram_data(res, epochs)` | `ExomoonPerturbationResult`, `Optional[np.ndarray]` | `Dict[str, Any]`: JSON-serializable dictionary with `ttv_minutes`, `tdv_minutes`, `phase_diff_deg`, `has_candidate`, etc. |
| `frontier_astronomy.dashboard.components.atmospheric_view` | `format_atmospheric_plot_data(spectrum, res)` | `SpectrumData`, `AtmosphericInversionResult` | `Dict[str, Any]`: dictionary with `envelope_1sig_low`, `envelope_1sig_high`, `envelope_2sig_low`, `envelope_2sig_high`, `medians`, `chi2_reduced` |
| `frontier_astronomy.cli.main` | `main(argv)` | `Optional[Sequence[str]]` | `int`: exit code (0 on success) |

---

## 3. Tier 4 Benchmarks Forensic Analysis & Refactoring Plan

File: `tests/test_tier4_benchmarks.py`

### 3.1 Scenario 1: Synthetic Dust-Tail Injection-Recovery
- **Current Lines**: 87–159
- **Forensic Finding**:
  1. Lines 119–130 construct `y_sym` and `y_tail` inline with manual equations, bypassing `detect_dust_tail`.
  2. Lines 150–155 compute `b_flat` and `b_tail_null = b_flat + 8 * log(N)`. Then `(b_flat - b_tail_null) = -8 * log(N) < 0`, so `false_alarms` is mathematically guaranteed to be 0 without evaluating any model on the noise!
- **Refactoring Strategy**:
  1. For each synthetic light curve, call `detect_dust_tail(lc, period=0.65355, t0=120.0)`.
  2. Check `if res.is_asymmetric_dust_tail and res.delta_bic >= 10.0: recovered_count += 1`.
  3. Call `evaluate_false_positive_rate(n_trials=25, noise_sigma=noise_level, period=0.65355, t0=120.0, seed=5000)` from `frontier_astronomy.dust_tail.injection_recovery` to execute real detection on pure noise.
  4. Assert `recovery_rate >= 0.90` and `fpr <= 0.02`.

### 3.2 Scenario 2: KIC 12557548 Real Disintegrating Planet Benchmark
- **Current Lines**: 160–236
- **Forensic Finding**:
  1. Lines 196–205 manually calculate ingress and egress durations from array indices.
  2. Lines 224–235 define `y_sym` and `y_tail` with manual hardcoded constants and compute `b_sym - b_tail`.
  3. `detect_dust_tail` is never called!
- **Refactoring Strategy**:
  1. Load `lc` from `BENCHMARKS_DIR / "KIC_12557548_kepler.parquet"`.
  2. Call `result: DustTailDetectionResult = detect_dust_tail(lc, period=0.6535538, t0=120.5683)`.
  3. Assert on real returned fields:
     - `assert result.is_asymmetric_dust_tail is True`
     - `assert result.delta_bic >= 15.0`
     - `assert result.asymmetry_parameter > 0.30`
     - `assert result.lrt_p_value < 1e-5`
     - `assert result.depth_variance > 0.0`
     - `assert 0.002 <= result.peak_depth <= 0.015`

### 3.3 Scenario 3: Multi-Body Exomoon Sensitivity Limit Validation
- **Current Lines**: 237–268
- **Forensic Finding**:
  1. Lines 244–263 perform inline arithmetic calculations for orbital radii and velocities.
  2. Neither `compute_sensitivity_grid` nor `compute_minimum_detectable_moon_mass` from `frontier_astronomy.perturbations.sensitivity` is called.
- **Refactoring Strategy**:
  1. Call `grid = compute_sensitivity_grid(m_star=M_SUN, m_planet=M_JUPITER, p_planet_days=10.0, p_moon_days=1.5, sigma_phot_min=0.30, mass_ratios=[0.01, 0.03, 0.05])`.
  2. Assert `grid["snrs"][-1] >= 3.0` and `bool(grid["detected"][-1]) is True`.
  3. Assert `grid["detection_limit_mass_ratio"] is not None and grid["detection_limit_mass_ratio"] <= 0.05`.
  4. Call `m_min = compute_minimum_detectable_moon_mass(m_star=M_SUN, m_planet=M_JUPITER, p_planet_days=10.0, p_moon_days=1.5, sigma_ttv_seconds=18.0, snr_threshold=3.0)`.
  5. Assert `0.0 < m_min < 0.1 * M_JUPITER`.

### 3.4 Scenario 4: Kepler-1625b Exomoon Candidate Evaluation
- **Current Lines**: 269–308
- **Forensic Finding**:
  1. The test loads `lc`, but then immediately sets:
     ```python
     phase_diff_deg = 90.0
     assert abs(phase_diff_deg - 90.0) <= 15.0
     p_moon = 0.88
     assert p_moon > 0.80
     ```
  2. Bypasses `frontier_astronomy.perturbations.detect_perturbations` entirely!
- **Refactoring Strategy**:
  1. Load `lc` from `BENCHMARKS_DIR / "Kepler_1625b_kepler.parquet"`.
  2. Call `result: ExomoonPerturbationResult = detect_perturbations(light_curve=lc, period=287.3789, t0=169.825, duration_hours=19.0)`.
  3. Assert on real returned fields:
     - `assert isinstance(result, ExomoonPerturbationResult)`
     - `assert result.target_id == lc.target_id`
     - `assert len(result.ttv_amplitudes) >= 2`
     - `assert len(result.tdv_amplitudes) >= 2`
     - `assert result.ttv_snr >= 3.0`
     - `assert abs(result.orthogonal_phase_diff_deg - 90.0) <= 20.0`
     - `assert result.p_moon_posterior > 0.70`
     - `assert result.has_exomoon_candidate is True`

### 3.5 Scenario 5: WASP-39b JWST NIRSpec Atmospheric Retrieval
- **Current Lines**: 309–372
- **Forensic Finding**:
  1. Lines 334–354 hardcode `medians = {"log_H2O": -3.22, "log_CO2": -3.68, ...}` and draw random normal samples around those constants.
  2. `invert_spectrum` is never called.
  3. The runtime check `t_elapsed < 0.10` merely measures the time to draw numpy random numbers!
- **Refactoring Strategy**:
  1. Load `spec` from `BENCHMARKS_DIR / "WASP_39b_jwst_prism.csv"`.
  2. Call real inversion:
     ```python
     t_start = time.perf_counter()
     result: AtmosphericInversionResult = invert_spectrum(spec, n_samples=2000)
     t_elapsed = time.perf_counter() - t_start
     ```
  3. Assert real runtime: `assert t_elapsed < 0.10` and `assert result.inference_time_seconds < 0.10`.
  4. Assert on real posterior medians:
     - `assert abs(result.medians["log_CO2"] - (-3.70)) <= 0.35`
     - `assert abs(result.medians["log_H2O"] - (-3.20)) <= 0.40`
     - `assert result.medians["log_CH4"] < -5.0`
     - `assert result.posterior_samples.shape == (2000, 7)`
     - `assert len(result.reconstructed_spectrum) == len(spec.wavelength)`
     - `assert result.chi2 > 0.0`
  5. Also verify `bench_res = run_wasp39b_retrieval_benchmark()` and `assert bench_res["passed"] is True`.

### 3.6 Scenario 6: WASP-96b JWST NIRISS Transmission Inversion
- **Current Lines**: 373–411
- **Forensic Finding**:
  1. Lines 396–410 test static constants: `retrieved_h2o = -3.48`, `retrieved_teq = 1270.0`, `retrieved_pc = -1.55`.
  2. Bypasses `invert_spectrum` entirely!
- **Refactoring Strategy**:
  1. Load `spec` from `BENCHMARKS_DIR / "WASP_96b_jwst_niriss.csv"`.
  2. Call `result: AtmosphericInversionResult = invert_spectrum(spec, n_samples=2000)`.
  3. Assert on real returned fields:
     - `assert abs(result.medians["log_H2O"] - (-3.50)) <= 0.45`
     - `assert 1000.0 <= result.medians["T_eq"] <= 1500.0`
     - `assert abs(result.medians["log_Pc"] - (-1.50)) <= 0.60`
     - `assert result.inference_time_seconds < 0.10`
     - `assert result.posterior_samples.shape == (2000, 7)`
  4. Also verify `bench_res = run_wasp96b_retrieval_benchmark()` and `assert bench_res["passed"] is True`.

---

## 4. Tier 3 Integration Workflows Forensic Analysis & Refactoring Plan

File: `tests/test_tier3_integration.py`

### 4.1 Workflow 2: Raw Light Curve -> Preprocessing -> Dust Tail Hunter
- **Current Lines**: 111–177
- **Forensic Finding**: Lines 139–175 manually construct `DustTailDetectionResult` from inline trapezoidal formulas and manual BIC calculation without calling `detect_dust_tail`.
- **Refactoring Strategy**:
  Call `result = detect_dust_tail(clean_lc, period=0.65355, t0=120.568)`. Assert `result.is_asymmetric_dust_tail is True`, `result.delta_bic >= 10.0`, `result.lrt_p_value < 1e-5`, `result.asymmetry_parameter >= 0.25`, and `len(result.best_fit_model) == len(clean_lc.flux)`.

### 4.2 Workflow 3: Dust Tail Extinction -> Injection-Recovery Pipeline
- **Current Lines**: 178–200
- **Forensic Finding**: Lines 194–196 check `min_flux < (1.0 - 3.5 * 0.0008)` instead of running the detector.
- **Refactoring Strategy**:
  Call `res = detect_dust_tail(injected, period=0.65355, t0=120.0)`. Check `if res.is_asymmetric_dust_tail and res.delta_bic >= 10.0: recovered_count += 1`. Assert `recovery_rate >= 0.85`.

### 4.3 Workflow 4: Ingestion -> Preprocessing -> Exomoon Perturbation (TTV-TDV)
- **Current Lines**: 201–252
- **Forensic Finding**: Lines 226–251 compute `ttv_obs = 25.0 * sin(psi)` and `tdv_obs = -8.0 * cos(psi)` via math formulas, check their dot product, and manually instantiate `ExomoonPerturbationResult`.
- **Refactoring Strategy**:
  Call `res = detect_perturbations(raw_lc, period=10.0, t0=120.0, duration_hours=4.0)`. Assert `len(res.ttv_amplitudes) >= 3`, `len(res.tdv_amplitudes) >= 3`, `res.ttv_snr > 0.0`, `0.0 <= res.orthogonal_phase_diff_deg <= 180.0`, and `res.p_moon_posterior > 0.0`.

### 4.4 Workflow 5: Exomoon Detector -> Multi-Body Sensitivity Validation
- **Current Lines**: 253–280
- **Forensic Finding**: Inlines gravitational formulas instead of calling `compute_sensitivity_grid`.
- **Refactoring Strategy**:
  Call `grid = compute_sensitivity_grid(mass_ratios=[0.005, 0.010, 0.020, 0.050])`. Assert `bool(grid["detected"][-1]) is True` (mass ratio 0.050) and `bool(grid["detected"][-2]) is True` (mass ratio 0.020).

### 4.5 Workflow 6: Radiative Transfer Forward Model -> Rapid Bayesian Inversion
- **Current Lines**: 281–326
- **Forensic Finding**: Lines 297–324 manually instantiate `AtmosphericInversionResult` with hardcoded dictionary `medians` and `inference_time_seconds = 0.035` without running `invert_spectrum`.
- **Refactoring Strategy**:
  Call `inversion_result = invert_spectrum(spec, n_samples=1500)`. Assert `isinstance(inversion_result, AtmosphericInversionResult)`, `inversion_result.inference_time_seconds < 0.10`, `inversion_result.posterior_samples.shape == (1500, 7)`, `len(inversion_result.reconstructed_spectrum) == len(spec.wavelength)`, and `inversion_result.err_lower[p] <= inversion_result.medians[p] <= inversion_result.err_upper[p]`.

### 4.6 Workflow 7: WASP-39b Benchmark Retrieval
- **Current Lines**: 327–342
- **Forensic Finding**: Zero codebase functions called. Compares hardcoded constants `retrieved_co2 = -3.68`, `retrieved_h2o = -3.22`, `retrieved_ch4 = -6.20` against reference numbers.
- **Refactoring Strategy**:
  Load `WASP_39b_jwst_prism.csv`. Call `result = invert_spectrum(spec, n_samples=2000)`. Assert `abs(result.medians["log_CO2"] - (-3.70)) <= 0.35`, `abs(result.medians["log_H2O"] - (-3.20)) <= 0.40`, `result.medians["log_CH4"] < -5.0`, and `result.inference_time_seconds < 0.10`.

### 4.7 Workflow 8: Ingestion -> Dust Tail Detection -> Dashboard 2D Anomaly Heatmap
- **Current Lines**: 343–370
- **Forensic Finding**: Manually loops over phase bins instead of calling `compute_residual_heatmap` from `frontier_astronomy.dashboard.components.heatmap_view`.
- **Refactoring Strategy**:
  Call `heatmap, row_epochs, col_phases = compute_residual_heatmap(light_curve=lc, period=3.5, t0=120.0, n_phase_bins=25, max_epochs=10)`. Assert `heatmap.shape == (len(row_epochs), 25)`, `not np.any(np.isnan(heatmap))`, and `np.mean(heatmap[:, 25 // 2]) < 0.0`.

### 4.8 Workflow 9: Ingestion -> Perturbation Detection -> Dashboard O-C & Phase View
- **Current Lines**: 371–392
- **Forensic Finding**: Hardcodes dictionary `oc_data = {...}` rather than calling `format_oc_diagram_data`.
- **Refactoring Strategy**:
  Call `res = detect_perturbations(lc, period=10.0, t0=120.0, duration_hours=4.0)`. Call `oc_data = format_oc_diagram_data(res)`. Verify JSON serialization `json.dumps(oc_data)` and assert `len(oc_data["ttv_minutes"]) == len(oc_data["tdv_minutes"])`.

### 4.9 Workflow 10: JWST Spectrum -> Inversion -> Dashboard Envelopes & Corner View
- **Current Lines**: 393–415
- **Forensic Finding**: Hardcodes dictionary `corner_data = {...}`.
- **Refactoring Strategy**:
  Call `res = invert_spectrum(sp, n_samples=1000)`. Call `plot_data = format_atmospheric_plot_data(sp, res)`. Assert `np.all(plot_data["envelope_2sig_low"] <= plot_data["envelope_1sig_low"])`, `np.all(plot_data["envelope_1sig_high"] <= plot_data["envelope_2sig_high"])`, `len(plot_data["medians"]) == 7`, and `plot_data["chi2_reduced"] > 0.0`.

### 4.10 Workflow 11: Command-Line Interface End-to-End Orchestration
- **Current Lines**: 416–463
- **Forensic Finding**: Builds a local `argparse.ArgumentParser` in the test body and writes fake JSON files directly, never importing `frontier_astronomy.cli.main`.
- **Refactoring Strategy**:
  Call `from frontier_astronomy.cli.main import main`.
  1. Test discover CLI: `ret_disc = main(["discover", "--target", "KIC 12557548", "--archive", "kepler", "--mode", "dust_tail", "--out", str(tmp_path / "disc_out")])`. Assert `ret_disc == 0`, verify output JSON exists, and inspect returned fields (`target_id == "KIC 12557548"`, `delta_bic >= 10.0`).
  2. Test invert CLI: `ret_inv = main(["invert", "--spectrum", str(csv_path), "--samples", "1000", "--out", str(tmp_path / "inv_out")])`. Assert `ret_inv == 0`, verify `inversion_summary.json` exists, and inspect returned fields (`status == "success"`, `log_CO2` present, `inference_time_seconds < 0.10`).

---

## 5. Concrete Worker Implementation Instructions

### Step 1: Refactor `tests/test_tier4_benchmarks.py`

The Worker must update `tests/test_tier4_benchmarks.py` with the following imports and complete method implementations:

```python
# --- ADD THESE IMPORTS TO tests/test_tier4_benchmarks.py ---
from frontier_astronomy.dust_tail.detector import detect_dust_tail
from frontier_astronomy.dust_tail.injection_recovery import evaluate_false_positive_rate
from frontier_astronomy.perturbations import detect_perturbations
from frontier_astronomy.perturbations.sensitivity import (
    compute_sensitivity_grid,
    compute_minimum_detectable_moon_mass,
)
from frontier_astronomy.atmospheric.inversion import invert_spectrum
from frontier_astronomy.atmospheric.benchmarks import (
    run_wasp39b_retrieval_benchmark,
    run_wasp96b_retrieval_benchmark,
)
```

#### Exact replacement for Scenario 1:
```python
    def test_scenario_1_synthetic_dust_tail_injection_recovery(self):
        """Scenario 1: Automated Synthetic Injection-Recovery Benchmark.

        Pass criteria:
        - >= 90% recovery rate at SNR >= 5.0
        - False positive rate <= 2.0% on pure stellar noise
        - Delta-BIC >= 10 on recovered candidates
        """
        depth_levels = [0.005, 0.010, 0.015]
        noise_level = 0.0010  # SNRs: 5.0, 10.0, 15.0

        recovered_count = 0
        total_trials = len(depth_levels) * 5
        delta_bics = []

        for d in depth_levels:
            for rep in range(5):
                lc = generate_synthetic_light_curve(
                    seed=rep * 100 + int(d * 1000),
                    transit_type="dust_tail",
                    depth=d,
                    noise_sigma=noise_level,
                    period=0.65355,
                    t0=120.0,
                )
                res = detect_dust_tail(lc, period=0.65355, t0=120.0)
                if res.is_asymmetric_dust_tail and res.delta_bic >= 10.0:
                    recovered_count += 1
                    delta_bics.append(res.delta_bic)

        recovery_rate = recovered_count / total_trials
        assert recovery_rate >= 0.90, f"Recovery rate {recovery_rate:.2f} < 0.90 at SNR >= 5.0"
        assert all(db >= 10.0 for db in delta_bics), "Delta-BIC threshold failed on recovered"

        # Genuine false positive test on pure stellar noise
        fpr = evaluate_false_positive_rate(
            n_trials=25,
            noise_sigma=noise_level,
            period=0.65355,
            t0=120.0,
            seed=5000,
        )
        assert fpr <= 0.02, f"False positive rate {fpr:.3f} > 0.02"
```

#### Exact replacement for Scenario 2:
```python
    def test_scenario_2_kic_12557548_real_disintegrating_planet_benchmark(self):
        """Scenario 2: Real Disintegrating Planet Benchmark: KIC 12557548.

        Pass criteria:
        - Correct identification of asymmetric cometary tail (alpha > 0.3)
        - Orbit-to-orbit / multi-quarter depth variability (0.2% to 1.2%)
        - Rejection of symmetric transit model with Delta-BIC >= 15
        """
        parquet_path = BENCHMARKS_DIR / "KIC_12557548_kepler.parquet"
        if parquet_path.exists():
            lc = load_light_curve_parquet(parquet_path)
        else:
            lc = generate_synthetic_light_curve(
                target_id="KIC 12557548",
                mission="Kepler",
                transit_type="dust_tail",
                period=0.6535538,
                t0=120.5683,
                depth=0.0085,
                sigma_ing=0.004,
                lambda_tail=0.05,
                f_scat=0.0012,
                depth_var_sigma=0.4,
            )

        assert lc.target_id == "KIC 12557548"
        assert lc.n_points > 500

        period = 0.6535538
        t0 = 120.5683

        # Execute real cometary dust tail detection engine
        result: DustTailDetectionResult = detect_dust_tail(lc, period=period, t0=t0)

        # 1. Asymmetry test: alpha > 0.30
        assert result.asymmetry_parameter > 0.30, (
            f"Expected cometary asymmetry > 0.30, got {result.asymmetry_parameter:.3f}"
        )

        # 2. Multi-epoch variable depth test: depth variance > 0
        assert result.depth_variance > 0.0, "Expected non-zero orbit-to-orbit depth variability"

        # 3. Model comparison: Delta-BIC >= 15 favoring asymmetric dust tail and LRT p < 1e-5
        assert result.delta_bic >= 15.0, (
            f"Expected Delta-BIC >= 15.0 for KIC 12557548, got {result.delta_bic:.1f}"
        )
        assert result.lrt_p_value < 1e-5, f"Expected LRT p-value < 1e-5, got {result.lrt_p_value:.2e}"
        assert result.is_asymmetric_dust_tail is True
```

#### Exact replacement for Scenario 3:
```python
    def test_scenario_3_multibody_exomoon_sensitivity_limit_validation(self):
        """Scenario 3: Multi-Body Exomoon Sensitivity Limit Validation.

        Pass criteria:
        - Sensitivity down to SNR = 3.0 for realistic satellite mass ratios (Ms/Mp ~ 0.01 - 0.05)
        - Statistically significant detection of TTV and secondary transit shoulders
        """
        grid = compute_sensitivity_grid(
            m_star=M_SUN,
            m_planet=M_JUPITER,
            p_planet_days=10.0,
            p_moon_days=1.5,
            sigma_phot_min=0.30,
            mass_ratios=[0.01, 0.03, 0.05],
        )

        # For Ms/Mp = 0.05, SNR must be >= 3.0 and detected
        assert grid["snrs"][-1] >= 3.0, f"Expected SNR >= 3.0 for Ms/Mp=0.05, got {grid['snrs'][-1]:.2f}"
        assert bool(grid["detected"][-1]) is True
        assert grid["detection_limit_mass_ratio"] is not None
        assert grid["detection_limit_mass_ratio"] <= 0.05

        # Minimum detectable satellite mass
        m_min = compute_minimum_detectable_moon_mass(
            m_star=M_SUN,
            m_planet=M_JUPITER,
            p_planet_days=10.0,
            p_moon_days=1.5,
            sigma_ttv_seconds=18.0,
            snr_threshold=3.0,
        )
        assert 0.0 < m_min < 0.1 * M_JUPITER
```

#### Exact replacement for Scenario 4:
```python
    def test_scenario_4_kepler1625b_exomoon_candidate_evaluation(self):
        """Scenario 4: Kepler-1625b Real Exomoon Candidate Evaluation.

        Pass criteria:
        - Recovery of observed timing variation profile
        - Measurement of TTV-TDV ~90 deg phase shift
        - Calculation of exomoon posterior probability P(moon|data)
        """
        parquet_path = BENCHMARKS_DIR / "Kepler_1625b_kepler.parquet"
        if parquet_path.exists():
            lc = load_light_curve_parquet(parquet_path)
        else:
            lc = generate_synthetic_light_curve(
                target_id="Kepler-1625b",
                mission="Kepler",
                transit_type="exomoon",
                period=287.38,
                t0=169.825,
                depth=0.010,
                ttv_amp_minutes=35.0,
                tdv_amp_minutes=12.0,
                p_moon_days=2.5,
                has_shoulder=True,
            )

        assert lc.target_id == "Kepler-1625b"

        # Execute real multi-body gravitational perturbation detection pipeline
        pert_res: ExomoonPerturbationResult = detect_perturbations(
            light_curve=lc,
            period=287.3789,
            t0=169.825,
            duration_hours=19.0,
        )

        assert isinstance(pert_res, ExomoonPerturbationResult)
        assert pert_res.target_id == lc.target_id
        assert len(pert_res.ttv_amplitudes) >= 2
        assert len(pert_res.tdv_amplitudes) >= 2
        assert pert_res.ttv_snr >= 3.0, f"Expected TTV SNR >= 3.0, got {pert_res.ttv_snr:.2f}"
        assert abs(pert_res.orthogonal_phase_diff_deg - 90.0) <= 20.0, (
            f"TTV-TDV phase shift {pert_res.orthogonal_phase_diff_deg:.1f} is not orthogonal"
        )
        assert pert_res.p_moon_posterior > 0.70, (
            f"Expected P(moon) > 0.70, got {pert_res.p_moon_posterior:.3f}"
        )
        assert pert_res.has_exomoon_candidate is True
```

#### Exact replacement for Scenario 5:
```python
    def test_scenario_5_wasp39b_jwst_nirspec_atmospheric_retrieval(self):
        """Scenario 5: WASP-39b JWST NIRSpec PRISM Transmission Inversion.

        Pass criteria:
        - Inversion runtime < 0.1s (< 100 ms)
        - log10(X_CO2) reproduced within 1-sigma of literature reference (-3.70 +/- 0.35)
        - log10(X_H2O) reproduced within 1-sigma of literature reference (-3.20 +/- 0.40)
        - log10(X_CH4) constrained to depleted upper limit (< -5.0)
        """
        csv_path = BENCHMARKS_DIR / "WASP_39b_jwst_prism.csv"
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

        assert spec.target_id == "WASP-39b"
        assert spec.n_channels >= 80

        # Execute genuine amortized Bayesian atmospheric retrieval
        t_start = time.perf_counter()
        result: AtmosphericInversionResult = invert_spectrum(spec, n_samples=2000)
        t_elapsed = time.perf_counter() - t_start

        assert t_elapsed < 0.10, f"Inversion runtime {t_elapsed:.4f}s exceeds 0.1s threshold"
        assert result.inference_time_seconds < 0.10

        # Validate against literature reference values (Rustamkulov et al. 2023)
        ref_co2 = -3.70
        sigma_co2 = 0.35
        assert abs(result.medians["log_CO2"] - ref_co2) <= sigma_co2, (
            f"CO2 retrieval {result.medians['log_CO2']} outside 1-sigma of {ref_co2} +/- {sigma_co2}"
        )

        ref_h2o = -3.20
        sigma_h2o = 0.40
        assert abs(result.medians["log_H2O"] - ref_h2o) <= sigma_h2o, (
            f"H2O retrieval {result.medians['log_H2O']} outside 1-sigma of {ref_h2o} +/- {sigma_h2o}"
        )

        assert result.medians["log_CH4"] < -5.0, (
            f"Expected depleted CH4 upper limit < -5.0, got {result.medians['log_CH4']}"
        )

        assert result.posterior_samples.shape == (2000, 7)
        assert len(result.reconstructed_spectrum) == len(spec.wavelength)
        assert result.chi2 > 0.0

        # Also verify benchmark helper returns pass
        bench_res = run_wasp39b_retrieval_benchmark()
        assert bench_res["passed"] is True
```

#### Exact replacement for Scenario 6:
```python
    def test_scenario_6_wasp96b_jwst_niriss_transmission_inversion(self):
        """Scenario 6: WASP-96b JWST NIRISS Transmission Inversion.

        Pass criteria:
        - Recovery of H2O absorption within 1-sigma of literature reference (-3.50 +/- 0.45)
        - Inferred equilibrium temperature and cloud top pressure within 1-sigma
        """
        csv_path = BENCHMARKS_DIR / "WASP_96b_jwst_niriss.csv"
        if csv_path.exists():
            spec = load_spectrum_csv(csv_path)
        else:
            spec = generate_synthetic_transmission_spectrum(
                target_id="WASP-96b",
                instrument="NIRISS_SOSS",
                log_h2o=-3.50,
                log_co2=-5.0,
                log_ch4=-6.0,
                t_eq=1280.0,
                log_pc=-1.5,
            )

        assert spec.target_id == "WASP-96b"

        # Execute genuine atmospheric inversion engine
        result: AtmosphericInversionResult = invert_spectrum(spec, n_samples=2000)

        # Validate H2O abundance against literature reference
        retrieved_h2o = result.medians["log_H2O"]
        ref_h2o = -3.50
        sigma_h2o = 0.45
        assert abs(retrieved_h2o - ref_h2o) <= sigma_h2o, (
            f"H2O abundance {retrieved_h2o} outside 1-sigma of {ref_h2o} +/- {sigma_h2o}"
        )

        # Equilibrium temperature check (JWST ERO: 1000 - 1500 K)
        retrieved_teq = result.medians["T_eq"]
        assert 1000.0 <= retrieved_teq <= 1500.0, (
            f"T_eq {retrieved_teq} outside expected temperature range [1000, 1500] K"
        )

        # Cloud deck pressure check (JWST ERO: -1.5 +/- 0.6)
        retrieved_pc = result.medians["log_Pc"]
        ref_pc = -1.50
        sigma_pc = 0.60
        assert abs(retrieved_pc - ref_pc) <= sigma_pc, (
            f"Cloud pressure {retrieved_pc} outside 1-sigma of {ref_pc} +/- {sigma_pc}"
        )

        assert result.posterior_samples.shape == (2000, 7)
        assert result.inference_time_seconds < 0.10

        # Also verify benchmark helper returns pass
        bench_res = run_wasp96b_retrieval_benchmark()
        assert bench_res["passed"] is True
```

---

### Step 2: Refactor `tests/test_tier3_integration.py`

The Worker must update `tests/test_tier3_integration.py` with the following imports and complete method implementations:

```python
# --- ADD THESE IMPORTS TO tests/test_tier3_integration.py ---
from pathlib import Path
from frontier_astronomy.dust_tail.detector import detect_dust_tail
from frontier_astronomy.perturbations import detect_perturbations
from frontier_astronomy.perturbations.sensitivity import compute_sensitivity_grid
from frontier_astronomy.atmospheric.inversion import invert_spectrum
from frontier_astronomy.dashboard.components.heatmap_view import compute_residual_heatmap
from frontier_astronomy.dashboard.components.perturbation_view import format_oc_diagram_data
from frontier_astronomy.dashboard.components.atmospheric_view import format_atmospheric_plot_data
from frontier_astronomy.cli.main import main
```

#### Exact replacement for Workflow 2:
```python
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
```

#### Exact replacement for Workflow 3:
```python
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
```

#### Exact replacement for Workflow 4:
```python
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
```

#### Exact replacement for Workflow 5:
```python
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
```

#### Exact replacement for Workflow 6:
```python
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
```

#### Exact replacement for Workflow 7:
```python
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
        sigma_co2 = 0.35
        ref_h2o = -3.20
        sigma_h2o = 0.40

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
```

#### Exact replacement for Workflow 8:
```python
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
```

#### Exact replacement for Workflow 9:
```python
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
```

#### Exact replacement for Workflow 10:
```python
    def test_w10_spectrum_inversion_to_dashboard_corner_view(self):
        """Workflow 10: JWST Spectrum -> Inversion -> Dashboard Envelopes & Corner View."""
        sp = generate_synthetic_transmission_spectrum(noise_ppm=50.0)
        res = invert_spectrum(sp, n_samples=1000)

        plot_data = format_atmospheric_plot_data(sp, res)

        assert np.all(plot_data["envelope_2sig_low"] <= plot_data["envelope_1sig_low"])
        assert np.all(plot_data["envelope_1sig_high"] <= plot_data["envelope_2sig_high"])
        assert len(plot_data["medians"]) == 7
        assert plot_data["chi2_reduced"] > 0.0
```

#### Exact replacement for Workflow 11:
```python
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
```

---

## 6. Summary Verification Checklist for Worker

Before concluding remediation:
1. `tests/test_tier4_benchmarks.py`:
   - [ ] No hardcoded numbers or local dictionaries defining mock outputs.
   - [ ] Scenarios 1 and 2 invoke `detect_dust_tail` on light curve data.
   - [ ] Scenario 3 invokes `compute_sensitivity_grid` and `compute_minimum_detectable_moon_mass`.
   - [ ] Scenario 4 invokes `detect_perturbations` on Kepler-1625b.
   - [ ] Scenarios 5 and 6 invoke `invert_spectrum` on WASP-39b and WASP-96b.
2. `tests/test_tier3_integration.py`:
   - [ ] Workflows 2 and 3 invoke `detect_dust_tail`.
   - [ ] Workflows 4 and 5 invoke `detect_perturbations` and `compute_sensitivity_grid`.
   - [ ] Workflows 6 and 7 invoke `invert_spectrum`.
   - [ ] Workflows 8, 9, 10 invoke dashboard component utilities (`compute_residual_heatmap`, `format_oc_diagram_data`, `format_atmospheric_plot_data`).
   - [ ] Workflow 11 invokes `cli.main` for both `discover` and `invert` subcommands, testing genuine JSON output written by the CLI.
