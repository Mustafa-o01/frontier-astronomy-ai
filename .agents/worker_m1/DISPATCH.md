## 2026-09-13T22:35:29Z

You are worker_m1, the Implementation Worker for Milestone 1: Data Ingestion & Time-Series Preprocessing Infrastructure.

Working directory: G:\frontier_astronomy_ai\.agents\worker_m1
Project root: G:\frontier_astronomy_ai
Authoritative user request: G:\frontier_astronomy_ai\ORIGINAL_REQUEST.md
System architecture & contracts: G:\frontier_astronomy_ai\PROJECT.md
Survey analyses to consult:
- G:\frontier_astronomy_ai\.agents\explorer_survey_1\analysis.md
- G:\frontier_astronomy_ai\.agents\explorer_survey_2\analysis.md
- G:\frontier_astronomy_ai\.agents\explorer_survey_3\analysis.md

MANDATORY FIRST STEP: You MUST read G:\frontier_astronomy_ai\ORIGINAL_REQUEST.md and G:\frontier_astronomy_ai\PROJECT.md before writing any code.

MANDATORY INTEGRITY WARNING:
DO NOT CHEAT. All implementations must be genuine. DO NOT hardcode test results, create dummy/facade implementations, or circumvent the intended task. A teamwork_preview_auditor will independently verify your work. Integrity violations WILL be detected and your work WILL be rejected.

Your Exclusive Write Ownership:
- frontier_astronomy/__init__.py
- frontier_astronomy/core/__init__.py
- frontier_astronomy/core/types.py (all dataclasses per PROJECT.md interface contracts)
- frontier_astronomy/core/constants.py (astronomical & physical constants)
- frontier_astronomy/core/preprocessing.py (asymmetric MAD outlier rejection, iterative Savitzky-Golay detrending with transit masking, phase folding, epoch splitting, inverse-variance binning)
- frontier_astronomy/core/math_utils.py (BIC, LRT, chi2, numerical utilities)
- frontier_astronomy/ingestion/__init__.py
- frontier_astronomy/ingestion/fits_reader.py (pure-Python/NumPy FITS binary table reader for Kepler/K2/TESS in <20ms)
- frontier_astronomy/ingestion/mast_client.py (STScI REST and static HTTP client with caching)
- frontier_astronomy/ingestion/catalog.py (benchmark systems catalog & loader)
- frontier_astronomy/ingestion/synthetic_generator.py (analytic deterministic synthetic light curves and spectra)
- data/ directory creation and bundled benchmark datasets:
  * data/benchmarks/KIC_12557548_kepler.parquet
  * data/benchmarks/Kepler_1625b_kepler.parquet
  * data/benchmarks/WASP_39b_jwst_prism.csv
  * data/benchmarks/WASP_96b_jwst_niriss.csv

Verification Requirements:
Run verification scripts using python to prove:
1. FITS parser correctly reads binary tables from bytes/files into structured NumPy arrays and filters QUALITY == 0.
2. Preprocessing pipeline correctly detrends raw flux, masks transits, and phase-folds with zero NaN propagation.
3. Parquet serialization and bundled benchmark loading work seamlessly.
Include exact verification commands and verbatim output in your handoff report.

Deliverables:
- Write complete implementation code in your owned files.
- Write your completion report to G:\frontier_astronomy_ai\.agents\worker_m1\handoff.md following the 5-component protocol (Observation, Logic Chain, Caveats, Conclusion, Verification Method).
- Send a completion message back to the orchestrator.
