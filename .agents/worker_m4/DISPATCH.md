## 2026-09-14T01:55:02Z
You are worker_m4, the Implementation Worker for Milestone 4: Rapid Atmospheric Chemistry Inversion for NASA JWST (Features F7, F8, F9).

Working directory: G:\frontier_astronomy_ai\.agents\worker_m4
Project root: G:\frontier_astronomy_ai
Authoritative user request: G:\frontier_astronomy_ai\ORIGINAL_REQUEST.md
System architecture & contracts: G:\frontier_astronomy_ai\PROJECT.md
Survey analyses: G:\frontier_astronomy_ai\.agents\explorer_survey_1\analysis.md
Predecessor handoff: G:\frontier_astronomy_ai\.agents\worker_m1\handoff.md

MANDATORY FIRST STEP: Read G:\frontier_astronomy_ai\ORIGINAL_REQUEST.md and G:\frontier_astronomy_ai\PROJECT.md.

MANDATORY INTEGRITY WARNING:
DO NOT CHEAT. All implementations must be genuine. DO NOT hardcode test results, create dummy/facade implementations, or circumvent the intended task. A teamwork_preview_auditor will independently verify your work. Integrity violations WILL be detected and your work WILL be rejected.

Your Exclusive Write Ownership:
- frontier_astronomy/atmospheric/__init__.py
- frontier_astronomy/atmospheric/opacities.py (Precomputed sampled molecular cross-section grids for H2O, CO2, CH4, CO, NH3 covering 0.6 - 5.3 um at R~100)
- frontier_astronomy/atmospheric/forward_model.py (Analytic transmission spectroscopy radiative transfer: scale height H = kB T / (mu g), wavelength-dependent transit depth (Rp(lambda)/R*)^2, cloud deck truncation at P >= Pc, Rayleigh haze slope)
- frontier_astronomy/atmospheric/normalizing_flow.py (PyTorch Conditional RealNVP flow network mapping standard Gaussian prior u ~ N(0, I) to 7D atmospheric parameter space conditioned on observed spectrum)
- frontier_astronomy/atmospheric/trainer.py (Amortized training pipeline generating forward model grid and training RealNVP flow)
- frontier_astronomy/atmospheric/inversion.py (Fast amortized posterior sampler < 0.1s runtime, computing median, 1-sigma, and 2-sigma credible intervals, chi2, returning AtmosphericInversionResult)
- frontier_astronomy/atmospheric/benchmarks.py (Benchmark retrieval verification on WASP-39b and WASP-96b reproducing literature molecular abundances within 1-sigma credible intervals).

Verification Requirements:
Run verification commands using python:
1. `python -m pytest tests/test_tier1_features.py -k "TestFeature7 or TestFeature8 or TestFeature9" -v`
2. `python -m pytest tests/test_tier2_boundaries.py -k "TestFeature7 or TestFeature8 or TestFeature9" -v`
3. Verify inference runtime < 0.1s per spectrum.
4. Verify WASP-39b retrieval reproduces log(CO2) and log(H2O) within 1-sigma of literature reference values (-3.70 +/- 0.35 and -3.20 +/- 0.40).
Include verbatim test output in your handoff report.

Deliverables:
- Implement complete genuine code in owned files.
- Write handoff report to G:\frontier_astronomy_ai\.agents\worker_m4\handoff.md.
- Send completion message to orchestrator.
