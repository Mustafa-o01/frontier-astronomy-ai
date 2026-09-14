## 2026-09-13T22:17:51Z

You are explorer_survey_3, the System & Dashboard Explorer for the Frontier Astronomy AI Discovery Suite project.
Your working directory: G:\frontier_astronomy_ai\.agents\explorer_survey_3
Project root: G:\frontier_astronomy_ai
Original user request: G:\frontier_astronomy_ai\ORIGINAL_REQUEST.md

You MUST read G:\frontier_astronomy_ai\ORIGINAL_REQUEST.md first.

Your objective:
Investigate the system architecture, testing framework, interactive visual discovery dashboard, and development environment in G:\frontier_astronomy_ai:
1. Software Architecture & Package Structure:
   - Modular, clean, production-grade Python package design (e.g. frontier_astronomy/ with modules: core/, ingestion/, dust_tail/, perturbations/, atmospheric/, dashboard/, cli/).
   - Environment and dependencies: Python on Windows, ensuring compatibility with NumPy, SciPy, Lightkurve, Astropy, Matplotlib/Plotly, PyTorch/scikit-learn, Streamlit.
   - Command-line interfaces and programmatic entry points for discovery, model fitting, and batch candidate evaluation.
2. Unified Interactive Discovery & Inspection Dashboard (R4):
   - UI framework evaluation: Streamlit is optimal for interactive astronomical visual analytics.
   - Required views & interactive tools:
     * Candidate Discovery Browser (table of ingested targets, filtering by asymmetry score, TTV significance, atmospheric SNR, search by Kepler/TESS/JWST ID).
     * Light Curve & Transit Inspector (raw time-series, detrended phase-folded flux, model fit overlays: symmetric vs dust tail vs exomoon shoulder).
     * Localized Residual Anomaly Heatmaps (epoch vs orbital phase flux residuals showing depth variations and asymmetric drift).
     * Exomoon & Perturbation Analyzer (O-C / Observed minus Calculated TTV diagrams, secondary shoulder zoom, posterior probability of companion).
     * JWST Atmospheric Inversion View (observed transmission spectrum with error bars, reconstructed best-fit spectra, posterior corner plots / marginal histograms for log(H2O), log(CO2), log(CH4), cloud pressure, temperature).
3. Testing & Verification Infrastructure (4-Tier Methodology):
   - Tier 1: Feature Coverage (>=5 test cases per feature covering all isolated components).
   - Tier 2: Boundary & Corner Cases (>=5 test cases per feature covering noise limits, edge cases, missing data, extreme parameter values).
   - Tier 3: Cross-Feature Integration (pairwise and pipeline-level tests: ingest -> detect -> invert -> report).
   - Tier 4: Real-World Benchmark Workloads (synthetic injection-recovery test suite, KIC 12557548 dust tail recovery, Kepler-1625b perturbation sensitivity validation, WASP-39b atmospheric retrieval 1-sigma reproduction).
   - Automated programmatic test execution runner (pytest or standalone test runner script with zero errors).

Deliverables:
Write your system and testing architectural blueprint to:
- G:\frontier_astronomy_ai\.agents\explorer_survey_3\analysis.md
- G:\frontier_astronomy_ai\.agents\explorer_survey_3\handoff.md
And send a completion message back to the orchestrator.
