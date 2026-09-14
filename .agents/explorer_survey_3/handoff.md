# Handoff Report: System Architecture, Testing Infrastructure & Interactive Discovery Dashboard

**Agent:** `explorer_survey_3` (System & Dashboard Explorer)  
**Task:** Phase 0 System & Testing Survey for Frontier Astronomy AI Discovery Suite  
**Date:** 2026-09-14  
**Working Directory:** `G:\frontier_astronomy_ai\.agents\explorer_survey_3`  
**Deliverable Files:**  
- `G:\frontier_astronomy_ai\.agents\explorer_survey_3\analysis.md`  
- `G:\frontier_astronomy_ai\.agents\explorer_survey_3\handoff.md`  

---

## 1. Observation

### 1.1 Requirements Observations (`ORIGINAL_REQUEST.md`)
- **Requirements**:
  - Line 12–13: "*R1. Disintegrating Exoplanet & Exocomet Dust Tail Hunter: Ingest and analyze photometric time-series from NASA Kepler and TESS public archives. Implement an automated detector specifically capable of distinguishing asymmetric, variable-depth transits (caused by trailing cometary dust clouds and catastrophically evaporating rocky crusts) from ordinary symmetric exoplanetary transits.*"
  - Line 15–16: "*R2. Exomoon & Trojan World Gravitational Perturbation Detector: Model and decouple mutual multi-body gravitational transit perturbations. Surface candidate exomoons and co-orbital Trojan worlds by isolating subtle Transit Timing Variations (TTVs) and secondary transit shoulder anomalies from stellar baseline noise.*"
  - Line 18–19: "*R3. Rapid Atmospheric Chemistry Inversion for NASA JWST: Perform amortized Bayesian parameter estimation on exoplanet transmission spectrophotometry (such as NIRSpec/NIRISS data from NASA's James Webb Space Telescope) to predict molecular volume mixing ratios (H2O, CO2, CH4) and cloud/haze parameters along with Bayesian posterior uncertainty estimates.*"
  - Line 21–22: "*R4. Unified Interactive Discovery & Inspection Dashboard: Provide an interactive visual analytics dashboard to inspect candidate anomalies, compare raw telescope signals against model reconstructions, visualize localized residual anomaly heatmaps, and interactively filter candidate targets.*"
  - Line 24–25: "*R5. Data Ingestion & Computational Infrastructure: Fetch observational time-series and spectra directly from public NASA open data archives (NASA MAST, Kepler, TESS, and JWST) or leverage relevant open-source astronomical packages / GitHub repositories and skills where appropriate. Ensure all computational models, automated validation pipelines, and dashboard interfaces run in the working directory G:\frontier_astronomy_ai.*"
- **Acceptance Criteria**:
  - Line 30: "*Automated synthetic injection-recovery tests demonstrate statistically significant recovery of asymmetric, variable dust-tail transits against standard symmetric transit baselines.*"
  - Line 31: "*Validation suite confirms sensitivity to secondary transit perturbations down to signal-to-noise ratios representative of realistic planet-moon configurations.*"
  - Line 32: "*Fast atmospheric retrieval on benchmark exoplanet transmission spectra reproduces reference molecular abundance posteriors within 1-sigma credible intervals.*"
  - Line 33: "*End-to-end automated test suite executes programmatically and passes with zero errors.*"
  - Line 36: "*Interactive discovery dashboard runs locally and displays candidate detection profiles, transit residuals, and atmospheric posterior distributions.*"
  - Line 37: "*Complete documentation provided detailing data ingestion, model architectures, verification results, and cataloged candidate discoveries.*"

### 1.2 Host Environment & Tooling Observations
- **Python Version**: `Python 3.14.6` at `C:\Python314\python.exe`.
- **Pre-installed Packages Verified**:
  - `numpy 2.5.2` (Available)
  - `scipy 1.18.1` (Available)
  - `pandas 3.0.5` (Available)
  - `torch 2.13.0` (Available)
  - `matplotlib 3.11.1` (Available)
  - `scikit-learn 1.9.0` (Available)
  - `pytest 9.1.1` (Available)
  - `requests 2.34.2` (Available)
- **Installability of Interactive Packages**:
  - Command: `python -m pip install --dry-run streamlit plotly astropy`
  - Verbatim Output: `Would install altair-6.2.2 astropy-8.0.1 astropy-iers-data-0.2026.9.7.0.56.14 httptools-0.8.0 itsdangerous-2.2.0 plotly-7.0.0 protobuf-7.36.1 pydeck-0.9.3 pyerfa-2.0.1.5 python-multipart-0.0.32 streamlit-1.63.0 toml-0.10.2 watchdog-6.0.0 websockets-16.1.1`
- **Critical Dependency Conflict Discovered in Lightkurve**:
  - Command: `python -m pip install --dry-run lightkurve`
  - Verbatim Output: `Collecting pandas<3.0.0,>=1.3.6 (from lightkurve)`
  - Verbatim Output: `Would install aiobotocore-3.9.1 ... lightkurve-2.6.0 ... pandas-2.3.3 ... s3fs-2026.7.0`
  - Observation: `lightkurve 2.6.0` pins `pandas < 3.0.0`, which conflicts with the host system's `pandas 3.0.5` and demands a downgrade plus heavy cloud storage dependencies.
- **Hardware & Autograd Performance**:
  - Command: SVD of $500\times 500$ matrix + PyTorch forward/backward autograd.
  - Verbatim Output: `PyTorch + NumPy verification successful in 527.49 ms`.

---

## 2. Logic Chain

1. **Decoupled Native Ingestion Architecture**:
   - *Observation*: `lightkurve 2.6.0` conflicts with the installed `pandas 3.0.5` by demanding a downgrade to `pandas 2.3.3`.
   - *Logic*: Hard-depending on `lightkurve` for primary data ingestion introduces brittle environment state. Therefore, `frontier_astronomy.ingestion` must feature a native, lightweight FITS binary table parser (`fits_reader.py`) and direct NASA MAST REST client (`mast_client.py`), using `numpy` and `pandas 3.0.5`. An optional `lightkurve_adapter.py` is included for compatibility, but the core suite runs with zero third-party dependency conflicts.

2. **Package Structure & Modularity**:
   - *Observation*: The system requires 3 distinct physical detection capabilities (dust tails, perturbations, atmospheric inversion), an interactive UI, a CLI, and data ingestion.
   - *Logic*: The codebase must be organized into high-cohesion subpackages (`core/`, `ingestion/`, `dust_tail/`, `perturbations/`, `atmospheric/`, `dashboard/`, `cli/`) with strictly typed dataclass contracts (`LightCurveData`, `FoldedTransit`, `DustTailDetectionResult`, `ExomoonPerturbationResult`, `SpectrumData`, `AtmosphericInversionResult`).

3. **Streamlit UI Framework Suitability**:
   - *Observation*: R4 requires an interactive visual analytics dashboard with target filtering, raw time-series inspection, model overlays, 2D residual heatmaps, and 7D posterior corner plots.
   - *Logic*: Streamlit (1.63.0) combined with Plotly (7.0.0) WebGL rendering is the optimal framework on Windows. It delivers reactive state management, GPU-accelerated client-side pan/zoom for 100k+ cadence light curves, and tabbed visual inspection without requiring complex frontend build tooling.

4. **4-Tier Verification Framework**:
   - *Observation*: Acceptance criteria mandate statistically significant dust-tail recovery against symmetric baselines, secondary perturbation sensitivity, 1-sigma atmospheric posterior reproduction, and zero-error programmatic test execution.
   - *Logic*: A strict 4-Tier verification hierarchy ensures comprehensive quality:
     - **Tier 1 (Feature Coverage)**: >=5 isolated unit tests per feature ($25+$ tests).
     - **Tier 2 (Boundary & Corner Cases)**: >=5 extreme/noise/limit tests per feature ($25+$ tests).
     - **Tier 3 (Cross-Feature Integration)**: 5 end-to-end multi-module pipeline workflows.
     - **Tier 4 (Real-World Benchmarks)**: Synthetic 100-lightcurve injection recovery, KIC 12557548 dust tail recovery, Kepler-1625b perturbation sensitivity validation, and WASP-39b JWST NIRSpec atmospheric retrieval reproduction within $1\sigma$.
     - Standalone programmatic test runner `run_tests.py` and `pytest` guarantee 100% programmatic reproducibility.

---

## 3. Caveats

1. **Network Reliance in Automated Tests**:
   - Live NASA MAST REST API calls can encounter transient rate limiting, network latency, or server downtime.
   - *Mitigation*: All automated tests in Tiers 1–4 must run strictly on local bundled datasets (`data/benchmarks/`) and deterministic synthetic generators. Live MAST queries are reserved for interactive user exploration and CLI discovery commands.
2. **Light Curve Rendering Performance**:
   - Full 4-year Kepler time-series contain $\sim 70,000$ observational cadences. Rendering raw unbinned arrays in real-time can introduce UI lag.
   - *Mitigation*: The dashboard will use `@st.cache_data` and intelligent out-of-transit downsampling/binning for full-mission overviews while preserving 100% full cadences across transit ingress and egress windows.
3. **Amortized Inversion Grid Resolution**:
   - Pre-computed molecular opacity cross-sections must be sampled at $R \sim 100$ ($0.6 - 5.3\,\mu\text{m}$) to keep memory footprint under $50\,\text{MB}$ while matching JWST NIRSpec PRISM resolution.

---

## 4. Conclusion

1. The architectural blueprint for the **Frontier Astronomy AI Discovery Suite** is fully specified and documented in `G:\frontier_astronomy_ai\.agents\explorer_survey_3\analysis.md`.
2. The package structure `frontier_astronomy/` is clean, modular, and resilient against Python 3.14 / Pandas 3 dependency constraints.
3. The interactive Streamlit visual analytics dashboard is designed with 5 comprehensive views (Candidate Browser, Light Curve Inspector, Residual Heatmaps, Exomoon Analyzer, JWST Inversion View).
4. The 4-tier verification methodology provides unambiguous, quantitative acceptance criteria and a standalone zero-error test execution runner.
5. The project is ready for Phase 1 synthesis (`PROJECT.md` and `TEST_INFRA.md`).

---

## 5. Verification Method

To independently verify this survey:

1. **Verify Deliverable Artifacts**:
   - Check that `G:\frontier_astronomy_ai\.agents\explorer_survey_3\analysis.md` exists and contains detailed sections for:
     - Software architecture and package structure
     - Streamlit dashboard architecture and 5 views
     - 4-Tier testing methodology (Tier 1-4 test inventory)
     - Real-world benchmark specifications (Synthetic, KIC 12557548, Kepler-1625b, WASP-39b)
   - Check that `G:\frontier_astronomy_ai\.agents\explorer_survey_3\handoff.md` exists and satisfies the 5-component protocol.

2. **Verify Python Environment & Test Runner Compatibility**:
   Execute the following command in PowerShell:
   ```powershell
   python -c "
   import numpy, scipy, pandas, torch, matplotlib, sklearn, pytest
   print('Core scientific stack verified.')
   print(f'Numpy: {numpy.__version__}')
   print(f'Scipy: {scipy.__version__}')
   print(f'Pandas: {pandas.__version__}')
   print(f'Torch: {torch.__version__}')
   print(f'Pytest: {pytest.__version__}')
   "
   ```
   **Pass Condition**: Script outputs versions and exits with code 0.
