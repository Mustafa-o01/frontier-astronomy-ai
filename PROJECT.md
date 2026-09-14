# Project: Frontier Astronomy AI Discovery Suite

## Architecture
The Frontier Astronomy AI Discovery Suite is a modular, high-performance astrophysics detection and atmospheric inversion platform built for real NASA observational archives (Kepler, K2, TESS, JWST). It is engineered in pure Python/NumPy/SciPy/PyTorch to guarantee zero external compiled C-extension build fragility on Windows while delivering sub-second neural inference and robust photometric analysis.

### High-Level System Architecture & Data Flow
```
[ NASA Open Archives / Local Fallback Fixtures ]
   ├── Kepler / K2 FITS Archive (Target Pixel & Light Curve Files)
   ├── TESS FITS Archive (SPOC Light Curves)
   └── JWST Spectrophotometry (NIRSpec PRISM / G395H, NIRISS SOSS)
                   │
                   ▼
┌────────────────────────────────────────────────────────┐
│ frontier_astronomy.ingestion                           │
│  - Pure-Python FITS Binary Table Parser                │
│  - STScI MAST REST Mashup & Static HTTP Client         │
│  - Dual-Mode Storage: Parquet (pyarrow) & CSV Caching  │
│  - Deterministic Synthetic & Benchmark Catalog Loader  │
└────────────────────────────────────────────────────────┘
                   │
                   ▼
┌────────────────────────────────────────────────────────┐
│ frontier_astronomy.core (Preprocessing & Types)         │
│  - Asymmetric MAD Outlier Rejection                    │
│  - Iterative Savitzky-Golay with Transit Masking       │
│  - Phase Folding, Epoch Splitting & Inverse-Var Binning│
└────────────┬────────────────────────────┬──────────────┘
             │                            │
             ▼                            ▼
┌─────────────────────────┐  ┌─────────────────────────┐
│ frontier_astronomy.     │  │ frontier_astronomy.     │
│ dust_tail               │  │ perturbations           │
│ - Rappaport/Brogi Model │  │ - 3-Body Photodynamics  │
│ - Forward Scattering    │  │ - TTV Cross-Correlation │
│ - Evaporative Lifetimes │  │ - TDV-V Duration Metric │
│ - Multi-Epoch Var-Depth │  │ - pi/2 Phase Invariant  │
│ - Delta-BIC & LRT Tests │  │ - L4/L5 Trojan Dips     │
│ - Injection-Recovery    │  │ - Sensitivity Limits    │
└────────────┬────────────┘  └────────────┬────────────┘
             │                            │
             └─────────────┬──────────────┘
                           │
                           ▼
┌────────────────────────────────────────────────────────┐
│ frontier_astronomy.atmospheric                         │
│  - Radiative Transfer Forward Model (0.6 - 5.3 um)     │
│  - Pre-computed Opacity Grids: H2O, CO2, CH4, CO, NH3  │
│  - PyTorch Conditional RealNVP Normalizing Flow        │
│  - Fast Amortized Posterior Sampling (<0.1s runtime)   │
│  - 1-Sigma / 2-Sigma Credible Interval Extraction      │
└──────────────────────────┬─────────────────────────────┘
                           │
                           ▼
┌────────────────────────────────────────────────────────┐
│ frontier_astronomy.dashboard & cli                     │
│  - Streamlit Unified Interactive Discovery UI          │
│    * Candidate Discovery Browser (multi-filter panel)  │
│    * Light Curve & Transit Profile Inspector           │
│    * Localized Residual Anomaly Heatmaps (epoch/phase) │
│    * Exomoon & Perturbation Analyzer (O-C & pi/2 test) │
│    * JWST Atmospheric Inversion View (corner plots)    │
│  - Programmatic CLI: discover, invert, dashboard, bench│
└────────────────────────────────────────────────────────┘
```

---

## Feature Inventory
Every feature from the Survey phase is enumerated below with its assigned milestone:

| # | Feature ID | Feature Name | Description | Milestone | Source |
|---|------------|--------------|-------------|-----------|--------|
| 1 | F1 | Pure-Python FITS & MAST Data Ingestion Engine | Direct STScI REST & static HTTP client, pure-Python/NumPy FITS binary table parser for Kepler/K2/TESS Target Pixel and Light Curve files, quality flag bitmask filtering, BKJD/BTJD cadence alignment, and Parquet caching with hermetic fallback fixtures under `data/`. | Milestone 1 | Survey 2 |
| 2 | F2 | Time-Series Preprocessing & Robust Detrending | Asymmetric MAD-based outlier rejection, iterative Savitzky-Golay detrending with transit masking to safeguard cometary tail depth, phase-folding, epoch slicing, and inverse-variance binning. | Milestone 1 | Survey 2 |
| 3 | F3 | Catastrophic Disintegrating Exoplanet & Dust Tail Hunter | Physical cometary extinction profile (steep ingress, exponential egress tail), Henyey-Greenstein forward scattering pre-ingress brightening bump, Langmuir grain sublimation lifetime modeling, multi-epoch stochastic depth variance, and Delta-BIC >= 10 & Likelihood Ratio Test vs symmetric Mandel-Agol baseline. | Milestone 2 | Survey 1 |
| 4 | F4 | Synthetic Injection-Recovery Suite for Dust Tails | Automated Monte Carlo injection-recovery testing across transit depths (0.1% to 2.0%) and tail decay lengths, evaluating statistical recovery rate (>= 90% at SNR >= 5) and false positive rate (<= 2%) on Kepler/TESS baselines. | Milestone 2 | Survey 1, Survey 3 |
| 5 | F5 | Exomoon & Trojan Gravitational Perturbation Detector | 3-body photodynamic transit modeling, Transit Timing Variation (TTV) and Transit Duration Variation (TDV) extraction, pathognomonic pi/2 (90 deg) orthogonal TTV-TDV phase invariant, secondary transit shoulder anomaly isolation, L4/L5 co-orbital Trojan companion detection (+/- 60 deg phase offset), and stellar baseline decoupling. | Milestone 3 | Survey 1 |
| 6 | F6 | Multi-Body Perturbation Sensitivity Validation Suite | Validation confirming sensitivity to secondary transit perturbations down to signal-to-noise ratios representative of realistic planet-moon configurations (e.g. Neptune/Earth, Jupiter/Earth mass and radius ratios). | Milestone 3 | Survey 1, Survey 3 |
| 7 | F7 | JWST Transmission Spectrophotometry Forward Radiative Transfer | Wavelength-dependent transit depth model (Rp(lambda)/R*)^2, atmospheric scale height H, precomputed cross-section grids for H2O, CO2, CH4, CO, NH3, gray cloud deck pressure Pc, and Rayleigh haze slope across JWST wavelengths (0.6 - 5.3 um). | Milestone 4 | Survey 1 |
| 8 | F8 | Rapid Amortized Bayesian Atmospheric Inversion Engine | PyTorch-native Conditional RealNVP Normalizing Flows / Neural Posterior Estimation (NPE), sub-second inference runtime (< 0.1s per spectrum), generating median, 1-sigma, and 2-sigma credible intervals and full posterior corner distributions for 7 atmospheric parameters. | Milestone 4 | Survey 1 |
| 9 | F9 | Benchmark Exoplanet Atmospheric Validation Suite | Fast atmospheric retrieval on benchmark exoplanet transmission spectra (WASP-39b NIRSpec PRISM, WASP-96b NIRISS) reproducing reference molecular volume mixing ratios within 1-sigma credible intervals. | Milestone 4 | Survey 1, Survey 2 |
| 10 | F10 | Unified Interactive Discovery & Inspection Dashboard | Streamlit interactive application featuring: (1) Candidate Discovery Browser with multi-metric filtering, (2) Light Curve & Transit Inspector with model overlays, (3) Localized Residual Anomaly Heatmaps (epoch vs phase), (4) Exomoon & Perturbation Analyzer with O-C diagram and pi/2 phase test, (5) JWST Atmospheric Inversion View with spectral fit, error envelopes, and 7D posterior corner plots. | Milestone 5 | Survey 3 |
| 11 | F11 | Command-Line Discovery Interface & Orchestration CLI | Programmatic CLI (`frontier_astronomy.cli`) with subcommands `discover`, `invert`, `dashboard`, and `benchmark` for batch data analysis, pipeline execution, and local server startup. | Milestone 5 | Survey 3 |
| 12 | F12 | Comprehensive 4-Tier Automated Verification Test Suite | Programmatic test harness (`run_tests.py` and `pytest`) executing all Tier 1 (Feature Coverage), Tier 2 (Boundary & Corner Cases), Tier 3 (Cross-Feature Integration), and Tier 4 (Real-World Benchmarks) tests with 100% pass rate and zero errors. | Milestone 6 | Survey 3 |
| 13 | F13 | Documentation, Candidate Catalogs & Verification Records | Complete technical documentation detailing data ingestion pipelines, physical model formulations, neural network architectures, verification benchmark results, and cataloged candidate discoveries. | Milestone 6 | Survey 3 |

---

## Milestones
| # | Name | Scope | Dependencies | Status |
|---|------|-------|-------------|--------|
| M1 | Data Ingestion & Time-Series Preprocessing | F1 (FITS & MAST Ingestion Engine), F2 (Preprocessing & Detrending), bundled benchmark datasets | None | DONE |
| M2 | Disintegrating Exoplanet & Dust Tail Hunter | F3 (Dust Tail Extinction Model & Detector), F4 (Synthetic Injection-Recovery Suite) | M1 | DONE |
| M3 | Exomoon & Trojan Perturbation Detector | F5 (TTV/TDV & Trojan Detector), F6 (Perturbation Sensitivity Suite) | M1 | DONE |
| M4 | Rapid Atmospheric Chemistry Inversion for JWST | F7 (Forward Radiative Transfer), F8 (Amortized NPE Inversion), F9 (WASP-39b/WASP-96b Benchmarks) | None | DONE |
| M5 | Unified Interactive Discovery & Inspection Dashboard | F10 (Streamlit 5-View Dashboard), F11 (CLI Entrypoints) | M1, M2, M3, M4 | DONE |
| M6 | End-to-End Verification, Coverage Hardening & Delivery | F12 (100% E2E Test Suite Execution & Tier 5 Adversarial Hardening), F13 (Final Documentation & Catalog Delivery) | M1, M2, M3, M4, M5, E2E Testing Track | DONE |

*Parallel Track:*
- **E2E Testing Track**: Dispatched concurrently with Milestone 1 to build the opaque-box test infrastructure, synthetic injection test generators, and Tier 1-4 test suites. Publishes `TEST_READY.md`.

---

## Interface Contracts

### Data Ingestion ↔ Detection Modules
```python
@dataclass(frozen=True)
class LightCurveData:
    target_id: str                      # e.g., "KIC 12557548" or "TIC 261136679"
    mission: str                        # "Kepler", "K2", or "TESS"
    time: np.ndarray                    # 1D float64 array of BKJD or BTJD cadences
    flux: np.ndarray                    # 1D float64 array of normalized PDC flux
    flux_err: np.ndarray                # 1D float64 array of 1-sigma photometric uncertainty
    quality: np.ndarray                 # 1D int32 array of NASA quality flags (0 = nominal)
    ra: float                           # Target right ascension (degrees)
    dec: float                          # Target declination (degrees)
    metadata: Dict[str, Any]            # Header parameters (channel, quarter, sector, etc.)

@dataclass(frozen=True)
class FoldedTransit:
    phase: np.ndarray                   # Orbital phase in [-0.5, 0.5)
    flux: np.ndarray                    # Normalized flux sorted by phase
    flux_err: np.ndarray                # Uncertainty array
    epoch_indices: np.ndarray           # Integer transit epoch identifier per cadence
    period: float                       # Orbital period in days
    t0: float                           # Transit epoch (BKJD/BTJD)
```

### Dust Tail Hunter Output Contract
```python
@dataclass(frozen=True)
class DustTailDetectionResult:
    target_id: str
    period: float
    t0: float
    is_asymmetric_dust_tail: bool       # True if Delta-BIC >= 10 and LRT p < 1e-5
    delta_bic: float                    # BIC(symmetric) - BIC(dust_tail)
    lrt_p_value: float                  # Likelihood ratio test p-value
    asymmetry_parameter: float          # alpha = (t_egress - t_ingress) / t_total
    peak_depth: float                   # Peak transit extinction
    tail_decay_length: float            # lambda_tail (phase units)
    forward_scattering_amp: float       # f_scat amplitude
    depth_variance: float               # Variance of transit depths across epochs
    best_fit_model: np.ndarray          # Model flux array evaluated at phase
```

### Exomoon & Perturbation Output Contract
```python
@dataclass(frozen=True)
class ExomoonPerturbationResult:
    target_id: str
    period: float
    ttv_amplitudes: np.ndarray          # O-C timing residual per epoch (minutes)
    tdv_amplitudes: np.ndarray          # Transit duration variation per epoch (minutes)
    has_exomoon_candidate: bool         # True if TTV SNR >= 3.0 and pi/2 phase invariant holds
    ttv_snr: float                      # Signal-to-noise ratio of TTV oscillation
    orthogonal_phase_diff_deg: float    # Phase difference (degrees), nominal = 90.0
    has_secondary_shoulder: bool        # Ingress/egress anomaly detected
    shoulder_snr: float                 # Anomaly significance
    has_trojan_candidate: bool          # L4/L5 co-orbital dip detected (+/- 60 deg)
    trojan_lag_depth: float             # Depth of L4/L5 dip
    p_moon_posterior: float             # Bayesian posterior probability of satellite
```

### Atmospheric Inversion Contract
```python
@dataclass(frozen=True)
class SpectrumData:
    target_id: str                      # e.g., "WASP-39b"
    instrument: str                     # e.g., "NIRSpec_PRISM"
    wavelength: np.ndarray              # Wavelength array in microns (0.6 - 5.3 um)
    transit_depth: np.ndarray           # Observed transit depth (Rp/R*)^2 or ppm
    uncertainty: np.ndarray             # 1-sigma uncertainty array

@dataclass(frozen=True)
class AtmosphericInversionResult:
    target_id: str
    medians: Dict[str, float]           # Median posterior values (log_H2O, log_CO2, log_CH4, log_CO, T_eq, log_Pc, haze_slope)
    err_lower: Dict[str, float]         # 1-sigma lower bounds (16th percentile)
    err_upper: Dict[str, float]         # 1-sigma upper bounds (84th percentile)
    posterior_samples: np.ndarray       # Shape (N_samples, 7)
    reconstructed_spectrum: np.ndarray  # Best-fit transit depth at instrument wavelengths
    chi2: float                         # Goodness of fit
    inference_time_seconds: float       # Elapsed runtime (< 0.1s)
```

---

## Code Layout
```
G:\frontier_astronomy_ai\
├── ORIGINAL_REQUEST.md                 # Authoritative user request
├── PROJECT.md                          # Global system architecture & milestone index
├── TEST_INFRA.md                       # 4-Tier test strategy & verification thresholds
├── TEST_READY.md                       # Created upon E2E test suite completion
├── run_tests.py                        # Standalone zero-error test runner
├── pytest.ini                          # Pytest configuration
├── data/
│   ├── benchmarks/                     # Curated real NASA benchmark products
│   │   ├── KIC_12557548_kepler.parquet # Disintegrating planet benchmark
│   │   ├── Kepler_1625b_kepler.parquet # Exomoon candidate benchmark
│   │   ├── WASP_39b_jwst_prism.csv     # Real JWST NIRSpec PRISM spectrum
│   │   └── WASP_96b_jwst_niriss.csv    # Real JWST NIRISS SOSS spectrum
│   ├── synthetic/                      # Generated verification fixtures
│   └── cache/                          # Local cache for MAST downloads
├── frontier_astronomy/
│   ├── __init__.py
│   ├── core/
│   │   ├── __init__.py
│   │   ├── types.py                    # Typed dataclasses and result contracts
│   │   ├── constants.py                # Astronomical & physical constants
│   │   ├── preprocessing.py            # MAD outlier rejection, Savitzky-Golay, folding
│   │   └── math_utils.py               # BIC, LRT, statistical utilities
│   ├── ingestion/
│   │   ├── __init__.py
│   │   ├── fits_reader.py              # Zero-dependency pure-Python FITS binary table reader
│   │   ├── mast_client.py              # STScI REST & static HTTP client with caching
│   │   ├── catalog.py                  # Benchmark systems index & loader
│   │   └── synthetic_generator.py      # High-fidelity analytic lightcurve/spectra generator
│   ├── dust_tail/
│   │   ├── __init__.py
│   │   ├── extinction_model.py         # Rappaport/Brogi cometary dust tail forward model
│   │   ├── forward_scattering.py       # Henyey-Greenstein pre-ingress brightening model
│   │   ├── sublimation.py              # Grain evaporation dynamics & lifetime modeling
│   │   ├── detector.py                 # Multi-epoch variable depth & Delta-BIC/LRT detector
│   │   └── injection_recovery.py       # Automated Monte Carlo injection-recovery harness
│   ├── perturbations/
│   │   ├── __init__.py
│   │   ├── photodynamics.py            # 3-body transit perturbation model
│   │   ├── ttv_extractor.py            # Transit timing variation cross-correlation engine
│   │   ├── tdv_extractor.py            # Transit duration variation & pi/2 phase invariant
│   │   ├── shoulder_detector.py        # Ingress/egress secondary transit shoulder detector
│   │   ├── trojan_detector.py          # L4/L5 co-orbital Trojan dip hunter
│   │   └── sensitivity.py              # Moon/planet mass ratio sensitivity validation
│   ├── atmospheric/
│   │   ├── __init__.py
│   │   ├── opacities.py                # Sampled molecular cross-section grids (H2O, CO2, etc.)
│   │   ├── forward_model.py            # Analytic transmission spectroscopy radiative transfer
│   │   ├── normalizing_flow.py         # PyTorch Conditional RealNVP flow network
│   │   ├── trainer.py                  # Amortized model training & grid generator
│   │   └── inversion.py                # Rapid posterior sampler & credible interval calculator
│   ├── dashboard/
│   │   ├── __init__.py
│   │   ├── app.py                      # Main Streamlit interactive discovery dashboard
│   │   ├── components/                 # Plotly charts, heatmaps, and corner plots
│   │   │   ├── lightcurve_view.py
│   │   │   ├── heatmap_view.py
│   │   │   ├── perturbation_view.py
│   │   │   └── atmospheric_view.py
│   │   └── state.py                    # Session state and caching management
│   └── cli/
│       ├── __init__.py
│       └── main.py                     # CLI entrypoint: discover, invert, dashboard, test
└── tests/
    ├── __init__.py
    ├── conftest.py
    ├── test_tier1_features.py          # >=5 tests per feature (isolated component coverage)
    ├── test_tier2_boundaries.py        # >=5 tests per feature (extreme values, noise, limits)
    ├── test_tier3_integration.py       # Cross-feature end-to-end integration workflows
    └── test_tier4_benchmarks.py        # Real-world benchmark recovery & acceptance tests
```
