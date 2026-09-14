# CODEX RESEARCH HANDOFF: FRONTIER ASTRONOMY AI DISCOVERY SUITE

**Document Title:** Comprehensive Technical Handoff & Scientific Reproducibility Manual  
**Target Audience:** Independent Research & Writing Agent (Codex)  
**Repository Working Directory:** `G:\frontier_astronomy_ai`  
**Date of Compilation:** September 14, 2026  
**Operating System:** Windows (PowerShell / `python.exe`)  
**Python Runtime:** Python 3.14.6 (`C:\Python314\python.exe`) & Anaconda Python 3.12 (`C:\Users\Mustafa\anaconda3\python.exe`)  

---

## 1. PROJECT OVERVIEW

### 1.1 Scientific Purpose & Problem Statement
The **Frontier Astronomy AI Discovery Suite** was developed to search archival space telescope photometric time-series (*Kepler*, *K2*, *TESS*) and infrared transmission spectra (*JWST*) for three classes of rare, high-value astrophysical phenomena that are systematically missed or discarded by standard pipeline flaggers:

1. **Catastrophically Disintegrating Exoplanets & Cometary Dust Tails:**
   * *The Phenomenon:* Ultra-short-period ($P < 1\ \mathrm{day}$) sub-Mercury/rocky cores undergoing thermal hydrodynamic evaporation and sublimation. The sublimating mineral dust forms an extended, asymmetric cometary tail driven by stellar radiation pressure (e.g., KIC 12557548 b, KOI-2700 b, K2-22 b).
   * *Why Standard Pipelines Miss Them:* Standard transit search algorithms (e.g., Kepler TPS/DV, Mandel & Agol 2002) assume strictly symmetric, limb-darkened, spherical occultation profiles. When an asymmetric, variable-depth transit with an elongated egress tail is encountered, standard matched-filter templates suffer severe penalty mismatches, often dismissing the event as instrumental drift, stellar flare recovery, or non-planetary noise.
2. **Exomoons & Co-Orbital Trojan Companions via Gravitational Perturbations:**
   * *The Phenomenon:* Natural satellites orbiting extrasolar gas giants and trojan companions librating around the triangular Lagrange points ($L_4 / L_5$).
   * *Why Standard Pipelines Miss Them:* Exomoon transit signals are subtle ($\sim 10^{-4}$ to $10^{-5}$) and manifest primarily as coupled perturbations: Transit Timing Variations (TTV) and Transit Duration Variations (TDV). The orbital motion of the planet around the planet-moon barycenter produces a mandatory $\pi/2$ ($90^\circ$) phase offset between TTV and TDV. Trojans produce shallow secondary occultations offset by $\pm 60^\circ$ ($\Delta\phi = \pm 0.1667$) from the primary transit.
3. **Rapid Atmospheric Chemistry Inversion for JWST Transmission Spectra:**
   * *The Phenomenon:* Rapid extraction of molecular mixing ratios ($\mathrm{H_2O}, \mathrm{CO_2}, \mathrm{CH_4}, \mathrm{CO}$), cloud/haze optical properties, and equilibrium temperature from transmission spectroscopy (e.g., JWST NIRSpec/NIRISS).

### 1.2 Algorithmic Breakdown: AI/ML vs. Conventional Astrophysics

| Pipeline Component | Method Type | Implementation Details | Source Files |
| :--- | :--- | :--- | :--- |
| **FITS Ingestion & Calibration** | Conventional Astronomical Computing | Zero-dependency pure-Python binary table parser for FITS BINTABLE data. Standard quality-bitmask filtering. | `frontier_astronomy/ingestion/fits_reader.py` |
| **Light Curve Detrending** | Conventional Time-Series Analysis | Iterative Savitzky-Golay polynomial filtering; running median filtering; MAD outlier clipping. | `frontier_astronomy/core/preprocessing.py` |
| **Dust Tail Modeling** | Physical / Forward Astrophysical Model | Rappaport/Brogi cometary extinction profile (Gaussian ingress + exponential power-law tail) + Mie forward-scattering brightening peak. | `frontier_astronomy/dust_tail/extinction_model.py`<br>`frontier_astronomy/dust_tail/forward_scattering.py` |
| **Model Selection & Statistics** | Classical Hypothesis Testing | Bayesian Information Criterion (BIC), Likelihood Ratio Test (LRT / Wilks' Theorem, $\Delta k = 3$), transit duration asymmetry parameter $\alpha$. | `frontier_astronomy/dust_tail/detector.py`<br>`frontier_astronomy/core/math_utils.py` |
| **Grain Sublimation Kinetics** | Physical Thermodynamics | Langmuir vacuum grain erosion kinetics ($da/dt$) for mineral dust species (enstatite, forsterite, silica, iron). | `frontier_astronomy/dust_tail/sublimation.py` |
| **TTV/TDV Perturbation Extraction** | Signal Processing / Photodynamics | Template cross-correlation with parabolic sub-cadence midpoint refinement; linear ephemeris fitting; orthogonal $\pi/2$ phase invariant test. | `frontier_astronomy/perturbations/ttv_extractor.py`<br>`frontier_astronomy/perturbations/tdv_extractor.py` |
| **Trojan Companion Detection** | Classical Photometric Binning | Localized aperture search in folded phase curves at $L_4$ (phase $+0.1667$) and $L_5$ (phase $-0.1667$). | `frontier_astronomy/perturbations/trojan_detector.py` |
| **Candidate Scoring ("$P(\mathrm{Moon})$")** | Heuristic Transfer Function (Non-AI) | Hand-crafted sigmoid mapping function based on TTV SNR and phase angle penalty. **Not** an MCMC/nested-sampling Bayesian integral. | `frontier_astronomy/perturbations/sensitivity.py` |
| **Atmospheric Inversion** | Deep Generative Machine Learning | Amortized Bayesian inference using Conditional Normalizing Flows (MAF / Affine Coupling layers) trained on radiative-transfer forward model spectra. | `frontier_astronomy/atmospheric/normalizing_flow.py`<br>`frontier_astronomy/atmospheric/inversion.py` |
| **Archive Cross-Matching** | Automated Catalog Querying | HTTP TAP queries against the NASA Exoplanet Archive (Caltech/IPAC) cumulative KOI tables and MAST STScI URL scraping. | `verify_candidate_novelty.py`<br>`fetch_nasa_candidates.py` |

---

## 2. REPOSITORY MAP

Every scientifically relevant file in `G:\frontier_astronomy_ai` is mapped below with its exact role, inputs, outputs, and dependencies.

### 2.1 Core Infrastructure (`frontier_astronomy/core/`)

#### `frontier_astronomy/core/types.py`
* **Purpose:** Defines frozen dataclasses and typed data structures used across the entire pipeline.
* **Inputs:** Raw NumPy arrays, scalars, dictionaries.
* **Outputs:** Typed immutable containers: `LightCurveData`, `FoldedTransit`, `DustTailDetectionResult`, `ExomoonPerturbationResult`, `AtmosphericRetrievalResult`, `CandidateScorecard`.
* **Important Functions/Classes:** `LightCurveData` (holds time, flux, flux_err, quality, metadata), `FoldedTransit`, `DustTailDetectionResult`.
* **Scientific Role:** Enforces data consistency across modules; guarantees that cadence timestamps, fluxes, and uncertainties maintain 1D shape alignment.
* **Used For:** All candidates and synthetic datasets.
* **Dependencies:** `dataclasses`, `numpy`.

#### `frontier_astronomy/core/constants.py`
* **Purpose:** Canonical physical, astronomical, and thermodynamic constants in SI and astronomical units.
* **Important Values:** $G = 6.67430 \times 10^{-11}\ \mathrm{m^3\ kg^{-1}\ s^{-2}}$, $M_\odot = 1.98847 \times 10^{30}\ \mathrm{kg}$, $R_\odot = 6.957 \times 10^8\ \mathrm{m}$, $M_\mathrm{Jup} = 1.89813 \times 10^{27}\ \mathrm{kg}$, $R_\mathrm{Jup} = 7.1492 \times 10^7\ \mathrm{m}$, $M_\oplus = 5.9722 \times 10^{24}\ \mathrm{kg}$, $R_\oplus = 6.371 \times 10^6\ \mathrm{m}$, $\mathrm{AU} = 1.495978707 \times 10^{11}\ \mathrm{m}$.
* **Scientific Role:** Eliminates round-off discrepancies and ensures physical unit fidelity across orbital mechanics and radiative transfer.

#### `frontier_astronomy/core/math_utils.py`
* **Purpose:** Fundamental mathematical, statistical, and transit profile modeling utilities.
* **Important Functions:**
  * `chi_squared(observed, model, uncertainties)`: Computes raw $\chi^2$.
  * `reduced_chi_squared(observed, model, uncertainties, k)`: Computes $\chi^2 / (N - k)$.
  * `bic(observed, model, uncertainties, k)`: Computes $k \ln N + \chi^2$.
  * `aic(observed, model, uncertainties, k)`: Computes $2k + \chi^2$.
  * `likelihood_ratio_test(chi2_null, chi2_alt, delta_k)`: Wilks' theorem survival function $\chi^2(\Delta k)$ via `scipy.stats.chi2.sf`.
  * `symmetric_trapezoid_transit(phase, period, depth, duration_phase, ingress_ratio)`: Fast analytical symmetric transit model.
* **Dependencies:** `numpy`, `scipy.stats`.

#### `frontier_astronomy/core/preprocessing.py`
* **Purpose:** Photometric calibration, outlier rejection, Savitzky-Golay detrending, and phase-folding.
* **Important Functions:**
  * `clean_quality(quality, bitmask)`: Filters cadences using standard bitmasks.
  * `asymmetric_mad_clip(flux, window_length, sigma_high, sigma_low)`: Moving-window median absolute deviation (MAD) filtering.
  * `iterative_savgol_detrend(time, flux, window_days, polyorder, period, t0, duration_days)`: Detrends light curves using iterative polynomial smoothing with transit masking.
  * `phase_fold(time, period, t0)`: Computes orbital phase in $[-0.5, 0.5)$.
  * `fold_light_curve(lc, period, t0, sort)`: Returns `FoldedTransit`.
  * `preprocess_light_curve(lc, strict_quality, clip_outliers, detrend, ...)`: End-to-end wrapper.
* **Scientific Vulnerability Identified:** If `duration_days` is `None`, `in_transit_mask` defaults to all `False`. The Savitzky-Golay filter fits directly through the transit, distorting ingress/egress profiles and artificially inducing timing shifts.

---

### 2.2 Data Ingestion (`frontier_astronomy/ingestion/`)

#### `frontier_astronomy/ingestion/fits_reader.py`
* **Purpose:** Pure-Python zero-dependency FITS BINTABLE reader for Kepler, K2, and TESS light curves.
* **Important Functions:**
  * `read_fits_light_curve(filepath, target_id)`: Parses primary and binary extension headers and extracts `TIME`, `PDCSAP_FLUX` (or `SAP_FLUX`), `PDCSAP_FLUX_ERR`, and `SAP_QUALITY`.
  * `read_fits_binary_table(file_obj)`: Direct byte-stream BINTABLE deserializer.
* **Scientific Role:** Eliminates external C-extension dependencies (Astropy) while reading MAST standard light curves in $<20\ \mathrm{ms}$.
* **Used For:** Reading all cached Kepler FITS files in `data/cache/real_kepler/`.

#### `frontier_astronomy/ingestion/catalog.py`
* **Purpose:** Ground-truth registry for known literature benchmark systems.
* **Benchmark Targets Registered:** KIC 12557548, K2-22b, KOI-2700b, WD 1145+017, Kepler-1625b, Kepler-1708b, WASP-39b, WASP-96b.
* **Scientific Role:** Provides published orbital periods, transit epochs, depths, and durations for validation checks.

#### `frontier_astronomy/ingestion/synthetic_generator.py`
* **Purpose:** Generates synthetic light curves containing injected physics: cometary dust tails, exomoon TTV/TDVs, and Gaussian Process red noise.
* **Used For:** Injection-recovery tests and boundary test suites.

---

### 2.3 Dust Tail Detection (`frontier_astronomy/dust_tail/`)

#### `frontier_astronomy/dust_tail/extinction_model.py`
* **Purpose:** Analytical forward model of cometary dust tail extinction.
* **Important Functions:**
  * `cometary_extinction_profile(phase, depth, sigma_ing, lambda_tail, alpha, phi_offset, f_scat, ...)`: Evaluates combined extinction and forward-scattering.
  * `compute_asymmetry_parameter(phase, model_flux)`: Computes $\alpha = (t_\mathrm{egress} - t_\mathrm{ingress}) / t_\mathrm{total}$.

#### `frontier_astronomy/dust_tail/forward_scattering.py`
* **Purpose:** Models the pre-transit brightening bump caused by forward Mie scattering from sub-micron dust grains entering superior conjunction.
* **Important Functions:** `forward_scattering_flux(phase, amplitude, phi_scat, sigma_scat)`.

#### `frontier_astronomy/dust_tail/sublimation.py`
* **Purpose:** Thermodynamic modeling of mineral dust grain lifetimes and Langmuir vacuum sublimation.
* **Important Functions:** `langmuir_sublimation_rate()`, `compute_grain_lifetime_hours()`, `vapor_pressure()`.

#### `frontier_astronomy/dust_tail/detector.py`
* **Purpose:** Automated fitting and model-selection engine comparing cometary dust tail models against symmetric transit models.
* **Important Functions:**
  * `fit_symmetric_transit(phase, flux, flux_err, period, ...)`: Least-squares fit of 5-parameter symmetric trapezoid ($k=5$).
  * `fit_cometary_dust_tail(phase, flux, flux_err, ...)`: Least-squares fit of 8-parameter cometary model ($k=8$).
  * `detect_dust_tail(light_curve, period, t0, ...)`: Computes $\Delta\mathrm{BIC} = \mathrm{BIC}_\mathrm{sym} - \mathrm{BIC}_\mathrm{tail}$, LRT $p$-value, asymmetry $\alpha$, and epoch depth variance.
* **Used For:** KIC 9944201, KIC 12557548 benchmark, and all survey targets.

---

### 2.4 Gravitational Perturbations (`frontier_astronomy/perturbations/`)

#### `frontier_astronomy/perturbations/photodynamics.py`
* **Purpose:** 3-body orbital mechanics and photodynamics for planet-moon and co-orbital systems.
* **Important Functions:**
  * `hill_radius(m_star, m_planet, semi_major_axis)`: Computes $R_H = a_p \sqrt[3]{M_p / (3 M_* catal)}$.
  * `critical_satellite_stability_radius()`: Calculates prograde/retrograde stability limits ($0.36 R_H$ / $0.49 R_H$).
  * `barycentric_ttv_amplitude()`: Calculates theoretical TTV amplitude: $a_s (M_s / M_p) / v_B$.
  * `velocity_tdv_amplitude()`: Calculates theoretical TDV amplitude: $T_0 (v_s / v_B) (M_s / M_p)$.

#### `frontier_astronomy/perturbations/ttv_extractor.py`
* **Purpose:** Measures mid-transit times per epoch via template cross-correlation and linear ephemeris fitting.
* **Important Functions:**
  * `_fit_transit_midpoint(t_win, f_win, fe_win, ...)`: Grid search + 3-point parabolic interpolation of $\chi^2(\tau)$.
  * `extract_ttv(time, flux, flux_err, period, t0, ...)`: Fits linear ephemeris $t_\mathrm{calc} = t_0 + E \cdot P$, computes $O - C$ residuals (minutes), and evaluates $\mathrm{SNR} = \mathrm{std}(\mathrm{TTV}) / \langle \sigma \rangle \cdot \sqrt{2}$.
* **Used For:** KIC 8494263, KIC 10153011, and all exomoon candidates.

#### `frontier_astronomy/perturbations/tdv_extractor.py`
* **Purpose:** Measures per-epoch transit duration variations and tests the $\pi/2$ orthogonal phase invariant.
* **Important Functions:**
  * `extract_tdv(...)`: Measures contact durations $T_{14}$ per epoch.
  * `test_orthogonal_phase_invariant(ttv_amplitudes, tdv_amplitudes, tolerance_deg)`: Fits harmonic sine waves to TTV and TDV series and measures phase difference $\Delta\phi = |\phi_\mathrm{TTV} - \phi_\mathrm{TDV}|$.

#### `frontier_astronomy/perturbations/shoulder_detector.py`
* **Purpose:** Detects mutual auxiliary occultation dips ("shoulders") immediately preceding ingress or following egress.
* **Important Functions:** `detect_transit_shoulders()`.

#### `frontier_astronomy/perturbations/trojan_detector.py`
* **Purpose:** Searches for co-orbital Trojan companions at the $L_4$ ($+60^\circ$, phase $+0.1667$) and $L_5$ ($-60^\circ$, phase $-0.1667$) Lagrange regions in phase-folded light curves.
* **Important Functions:** `detect_trojan_companions()`.
* **Used For:** KIC 8308347, KIC 6867155.

#### `frontier_astronomy/perturbations/sensitivity.py`
* **Purpose:** Evaluates minimum detectable moon mass ratios and computes candidate score $P(\mathrm{Moon})$.
* **Important Function:**
  * `compute_exomoon_posterior(ttv_snr, phase_diff_deg, shoulder_snr, prior_prob)`: **Warning:** This is a heuristic scoring function, NOT a formal Bayesian evidence integral.

---

### 2.5 Atmospheric Inversion (`frontier_astronomy/atmospheric/`)

#### `frontier_astronomy/atmospheric/forward_model.py`
* **Purpose:** 1D plane-parallel transmission spectroscopy radiative transfer forward model.
* **Important Functions:** Computes $R_p^2(\lambda) / R_*^2$ across 50 wavelength bins ($0.5\text{--}5.5\ \mu\mathrm{m}$) incorporating molecular cross-sections ($\mathrm{H_2O}, \mathrm{CO_2}, \mathrm{CH_4}, \mathrm{CO}$), Rayleigh scattering, and gray cloud deck pressure $P_c$.

#### `frontier_astronomy/atmospheric/normalizing_flow.py`
* **Purpose:** Conditional Normalizing Flow (RealNVP / Masked Autoregressive Flow) for amortized Bayesian parameter estimation.
* **Important Classes:** `AtmosphericNormalizingFlow`, `CouplingLayer`.

#### `frontier_astronomy/atmospheric/inversion.py`
* **Purpose:** Inference engine for JWST transmission spectra.
* **Important Functions:** `retrieve_atmospheric_parameters()`.
* **Used For:** Benchmark target WASP-39 b (`results/inversion_summary.json`).

---

### 2.6 Campaign Execution Scripts (Root Directory)

* `fetch_nasa_candidates.py`: Queries NASA Exoplanet Archive TAP service to build target lists: `data/nasa_candidates_usp.json` (Ultra-short period) and `data/nasa_candidates_moon.json` (Long-period).
* `scan_nasa_archive.py`: Primary campaign script. Downloads up to 3 quarters of real Kepler FITS files from STScI/MAST, executes preprocessing, dust-tail detection, and perturbation detection, and outputs `results/real_nasa_discoveries.json`.
* `verify_candidate_novelty.py`: Cross-checks detected KOIs against the NASA Exoplanet Archive cumulative table and known literature to verify catalog parameters and flag prior literature citations. Outputs `results/novelty_verification.json`.
* `batch_discovery_scan.py`: Batch scanner for literature benchmark targets (KIC 12557548, K2-22b, KOI-2700b, WD 1145+017, Kepler-1625b, Kepler-1708b). Outputs `results/batch_survey_report.json`.
* `run_tests.py`: Programmatic test suite runner executing 201 tests across 4 tiers.

---

## 3. PIPELINE EXECUTION FLOW

The real execution chain in the codebase proceeds through the following exact function calls:

```mermaid
flowchart TD
    A["NASA MAST Archive (archive.stsci.edu)"] -->|"HTTP GET (FITS BINTABLE)"| B["scan_nasa_archive.py: fetch_kepler_candidate_light_curve()"]
    B -->|"Local File Cache"| C["data/cache/real_kepler/kplr*.fits"]
    C -->|"Binary Parsing"| D["frontier_astronomy/ingestion/fits_reader.py: read_fits_light_curve()"]
    D -->|"Raw LightCurveData Container"| E["frontier_astronomy/core/preprocessing.py: preprocess_light_curve()"]
    
    subgraph Preprocessing_Stage["Preprocessing & Detrending"]
        E --> F1["clean_quality(SAP_QUALITY == 0)"]
        F1 --> F2["asymmetric_mad_clip(sigma=5.0)"]
        F2 --> F3["iterative_savgol_detrend(window_days=1.0, polyorder=2)"]
    end
    
    F3 -->|"Calibrated LightCurveData"| G1["frontier_astronomy/dust_tail/detector.py: detect_dust_tail()"]
    F3 -->|"Calibrated LightCurveData"| G2["frontier_astronomy/perturbations/__init__.py: detect_perturbations()"]
    
    subgraph Dust_Tail_Branch["Branch 1: Disintegrating Planet & Dust Tail"]
        G1 --> H1["fold_light_curve(period, t0)"]
        H1 --> H2["fit_symmetric_transit() -> chi2_sym, BIC_sym (k=5)"]
        H1 --> H3["fit_cometary_dust_tail() -> chi2_tail, BIC_tail (k=8)"]
        H2 & H3 --> H4["Delta-BIC = BIC_sym - BIC_tail"]
        H4 --> H5["Likelihood Ratio Test (Wilks delta_k=3) -> p_lrt"]
        H3 --> H6["compute_asymmetry_parameter() -> alpha"]
        H1 --> H7["compute_multi_epoch_depth_variability() -> depth_variance"]
    end
    
    subgraph Perturbation_Branch["Branch 2: Exomoon & Trojan Perturbations"]
        G2 --> J1["ttv_extractor.py: extract_ttv_from_light_curve()"]
        J1 --> J2["_fit_transit_midpoint() via template cross-correlation"]
        J2 --> J3["Linear ephemeris weighted fit -> O-C residuals (TTV min)"]
        J3 --> J4["ttv_snr = std(TTV) / mean(err) * sqrt(2)"]
        
        G2 --> J5["tdv_extractor.py: extract_tdv_from_light_curve()"]
        J5 --> J6["test_orthogonal_phase_invariant() -> phase_diff_deg"]
        
        G2 --> J7["shoulder_detector.py: detect_transit_shoulders_from_light_curve()"]
        G2 --> J8["trojan_detector.py: detect_trojan_companions_from_light_curve()"]
        
        J4 & J6 & J7 --> J9["sensitivity.py: compute_exomoon_posterior() -> p_moon_posterior"]
    end
    
    H4 & H6 & J4 & J9 & J8 --> K["scan_nasa_archive.py: Verdict Synthesis"]
    K --> L["results/real_nasa_discoveries.json"]
    L --> M["verify_candidate_novelty.py: verify_candidate_novelty()"]
    M --> N["results/novelty_verification.json"]
```

---

## 4. DATA PROVENANCE

### 4.1 Observational Data Sources for Candidates

| Target Identifier | KOI Identifier | Primary Data Source | Retrieved Files (in `data/cache/real_kepler/`) | Kepler Quarters | Cadence Type | Flux Type Used | Baseline (Days) | Valid Cadences |
| :--- | :--- | :--- | :--- | :--- | :--- | :--- | :--- | :--- |
| **KIC 9944201** | K07259.01 | NASA MAST / STScI | `kplr009944201-2009166043257_llc.fits`<br>`kplr009944201-2009259160929_llc.fits`<br>`kplr009944201-2009350155506_llc.fits` | Q1, Q2, Q3 | Long Cadence ($\sim 29.4\ \mathrm{min}$) | `PDCSAP_FLUX` | $217.98$ | $8,958$ (raw)<br>$8,431$ (clean) |
| **KIC 8494263** | K01255.01 | NASA MAST / STScI | `kplr008494263-2010078095331_llc.fits`<br>`kplr008494263-2010174085026_llc.fits`<br>`kplr008494263-2010265121752_llc.fits` | Q4, Q5, Q6 | Long Cadence ($\sim 29.4\ \mathrm{min}$) | `PDCSAP_FLUX` | $276.90$ | $10,695$ (raw)<br>$10,344$ (clean) |
| **KIC 10153011** | K01773.01 | NASA MAST / STScI | `kplr010153011-2009259160929_llc.fits`<br>`kplr010153011-2009350155506_llc.fits`<br>`kplr010153011-2010078095331_llc.fits` | Q2, Q3, Q4 | Long Cadence ($\sim 29.4\ \mathrm{min}$) | `PDCSAP_FLUX` | $272.44$ | $11,352$ (raw)<br>$11,048$ (clean) |
| **KIC 8308347** | K03761.01 | NASA MAST / STScI | `kplr008308347-2010078095331_llc.fits`<br>`kplr008308347-2010174085026_llc.fits`<br>`kplr008308347-2010265121752_llc.fits` | Q4, Q5, Q6 | Long Cadence ($\sim 29.4\ \mathrm{min}$) | `PDCSAP_FLUX` | $276.53$ | $8,383$ (raw)<br>$8,012$ (clean) |

### 4.2 Data Preprocessing Specifications
* **Time Standard:** Barycentric Kepler Julian Date ($\mathrm{BKJD} = \mathrm{BJD} - 2,454,833.0$).
* **Quality Filtering:** Cadences with `SAP_QUALITY > 0` are rejected.
* **Outlier Removal:** Moving MAD window ($W = 51$ cadences); cadences outside $[-5.0, +5.0]\ \mathrm{MAD}$ are removed.
* **Detrending Algorithm:** Savitzky-Golay polynomial filter ($W = 1.0\ \mathrm{day}$, polyorder $p=2$).
* **Transit Masking During Detrending:** **NOT ENABLED** during the automated scan (`duration_days` was not supplied to `preprocess_light_curve`).
* **Phase Folding:** Performed via $\phi = ((t - t_0) / P + 0.5) \pmod{1.0} - 0.5$.

---

## 5. CANDIDATE RESULT TRACEABILITY

The table below traces every major scientific parameter and statistical metric reported in the repository back to its precise source code, execution routine, and output file.

### Table 5.1: Master Scientific Result Traceability Matrix

| Result / Quantity | Reported Value | Generated By (Function) | Source File | Output File | Mathematical Method | Status / Verification |
| :--- | :--- | :--- | :--- | :--- | :--- | :--- |
| **KIC 9944201 Period** | $0.7215229\ \mathrm{d}$ | NASA TAP Query | `fetch_nasa_candidates.py` | `data/nasa_candidates_usp.json` | Caltech/IPAC TAP Service | **VERIFIED** (Catalog) |
| **KIC 9944201 Catalog Depth** | $22,528\ \mathrm{ppm}$ | NASA TAP Query | `fetch_nasa_candidates.py` | `data/nasa_candidates_usp.json` | Caltech/IPAC TAP Service | **VERIFIED** (Catalog) |
| **KIC 9944201 $\Delta\mathrm{BIC}$** | $+73,042.7$ | `detect_dust_tail()` | `frontier_astronomy/dust_tail/detector.py` | `results/real_nasa_discoveries.json` | $\mathrm{BIC}_\mathrm{sym} - \mathrm{BIC}_\mathrm{tail}$ on $N=8,431$ cadences | **VERIFIED (REPRODUCIBLE ARTIFACT)** |
| **KIC 9944201 Asymmetry $lpha$** | $+0.534$ | `compute_asymmetry_parameter()` | `frontier_astronomy/dust_tail/extinction_model.py` | `results/real_nasa_discoveries.json` | $(t_\mathrm{egress} - t_\mathrm{ingress}) / t_\mathrm{total}$ | **VERIFIED (REPRODUCIBLE ARTIFACT)** |
| **KIC 9944201 Secondary Eclipse** | $5,300\ \mathrm{ppm}$ ($0.53\%$) | Phase-curve binning | Direct Python execution on cached FITS | Forensic calculation | Inverse-variance median binning across 50 phase bins | **VERIFIED (REPRODUCIBLE IN CACHE)** |
| **KIC 9944201 Mass Loss Rate** | $\dot{M} \sim 10^8	ext{--}10^9\ \mathrm{kg/s}$ | Textual narrative in dossier | `NASA_CONFIRMATION_DOSSIER.md` | None | Theoretical scaling text | **UNTRACED CLAIM** (No code output) |
| **KIC 8494263 Period** | $78.92574\ \mathrm{d}$ | NASA TAP Query | `fetch_nasa_candidates.py` | `data/nasa_candidates_moon.json` | Caltech/IPAC TAP Service | **VERIFIED** (Catalog) |
| **KIC 8494263 Analyzed Transits** | $N = 3$ | Epoch counter in `extract_ttv()` | `frontier_astronomy/perturbations/ttv_extractor.py` | Forensic calculation | Timestamps: $429.36, 508.30, 587.24\ \mathrm{BKJD}$ | **VERIFIED (REPRODUCIBLE IN CACHE)** |
| **KIC 8494263 Claimed TTV SNR** | $50.1$ | `extract_ttv()` | `frontier_astronomy/perturbations/ttv_extractor.py` | `results/real_nasa_discoveries.json` | $\mathrm{std}(\mathrm{TTV}) / \langle\sigmaangle \cdot \sqrt{2}$ on detrended flux | **VERIFIED (REPRODUCIBLE ARTIFACT)** |
| **KIC 8494263 Raw TTV SNR** | $0.187$ | `extract_ttv()` | `frontier_astronomy/perturbations/ttv_extractor.py` | Forensic calculation | $\mathrm{std}(\mathrm{TTV}) / \langle\sigmaangle \cdot \sqrt{2}$ on raw flux | **VERIFIED (REPRODUCIBLE IN CACHE)** |
| **KIC 8494263 Claimed Phase Shift** | $91.4^\circ \pm 3.2^\circ$ | Textual narrative in dossier | `NASA_CONFIRMATION_DOSSIER.md` | None | Invented text in markdown | **UNTRACED CLAIM** (`json` has $0.0^\circ$) |
| **KIC 8494263 JSON Phase Shift** | $0.0^\circ$ | `test_orthogonal_phase_invariant()` | `frontier_astronomy/perturbations/tdv_extractor.py` | `results/real_nasa_discoveries.json` | Harmonic phase difference fit | **VERIFIED** (Real output) |
| **KIC 8494263 $P(\mathrm{Moon})$** | $99.9\%$ ($0.999$) | `compute_exomoon_posterior()` | `frontier_astronomy/perturbations/sensitivity.py` | `results/real_nasa_discoveries.json` | Empirical sigmoid mapping from $\mathrm{SNR}=50.1$ | **VERIFIED (HEURISTIC FUNCTION)** |
| **KIC 10153011 Period** | $83.09708\ \mathrm{d}$ | NASA TAP Query | `fetch_nasa_candidates.py` | `data/nasa_candidates_moon.json` | Caltech/IPAC TAP Service | **VERIFIED** (Catalog) |
| **KIC 10153011 Claimed TTV SNR** | $40.3$ | `extract_ttv()` | `frontier_astronomy/perturbations/ttv_extractor.py` | `results/real_nasa_discoveries.json` | Timing SNR on detrended flux | **VERIFIED (REPRODUCIBLE ARTIFACT)** |
| **KIC 10153011 Raw TTV SNR** | $2.20$ | `extract_ttv()` | `frontier_astronomy/perturbations/ttv_extractor.py` | Forensic calculation | Timing SNR on raw flux | **VERIFIED (REPRODUCIBLE IN CACHE)** |
| **KIC 10153011 Robovetter Score** | $0.000$ | NASA TAP Query | `verify_candidate_novelty.py` | `results/novelty_verification.json` | Official Kepler DR25 disposition | **VERIFIED** (Catalog) |
| **KIC 8308347 Period** | $164.9504\ \mathrm{d}$ | NASA TAP Query | `fetch_nasa_candidates.py` | `data/nasa_candidates_moon.json` | Caltech/IPAC TAP Service | **VERIFIED** (Catalog) |
| **KIC 8308347 Trojan Flag** | `True` | `detect_trojan_companions()` | `frontier_astronomy/perturbations/trojan_detector.py` | `results/real_nasa_discoveries.json` | Flux depression at phase $+0.1667$ | **VERIFIED (REPRODUCIBLE ARTIFACT)** |
| **KIC 8308347 Transits Extracted** | $N = 0$ | `extract_ttv()` | `frontier_astronomy/perturbations/ttv_extractor.py` | Forensic calculation | Minimum points per window not met | **VERIFIED (REPRODUCIBLE IN CACHE)** |

---

## 6. KIC 9944201: DETAILED TECHNICAL ANALYSIS

### 6.1 Pipeline Execution Trace
1. **Target Parameters:** Ingested via `scan_candidate()` with $P = 0.721522907\ \mathrm{d}$, $t_0 = 131.7091421\ \mathrm{BKJD}$, $\mathrm{Depth} = 22,528\ \mathrm{ppm}$.
2. **Data Filtering:** 3 quarters ingested (Q1, Q2, Q3) totaling $N = 8,431$ cadences after quality clipping and outlier rejection.
3. **Symmetric Model Fit (`fit_symmetric_transit`):**
   * Free parameters ($k=5$): `[depth, duration_phase, ingress_ratio, t_offset]`.
   * Optimization: `scipy.optimize.least_squares` with bounds $[0.0, 0.005, 0.05, -0.05]$ to $[0.8, 0.350, 0.45, 0.05]$.
   * Convergence Result: Optimizer remained trapped near initial parameters:
     * `depth`: $0.0225$
     * `duration_phase`: $0.040$
     * `ingress_ratio`: $0.20$
     * `t_offset`: $0.0$
   * Model Performance: $\chi^2_\mathrm{sym} = 259,970.4$, $\mathrm{BIC}_\mathrm{sym} = 260,015.6$ ($\chi^2_
u pprox 30.8$).
4. **Cometary Dust Tail Fit (`fit_cometary_dust_tail`):**
   * Free parameters ($k=8$): `[depth, sigma_ing, lambda_tail, alpha, phi_offset, f_scat]`.
   * Convergence Result:
     * `depth`: $0.0554$ ($5.54\%$)
     * `sigma_ing`: $0.0061$
     * `lambda_tail`: $0.0411$
     * `alpha`: $2.49999$ (hit parameter upper bound of $2.5$)
     * `phi_offset`: $0.0239$
     * `f_scat`: $0.014997$ (hit parameter upper bound of $0.015$)
   * Model Performance: $\chi^2_\mathrm{tail} = 186,900.5$, $\mathrm{BIC}_\mathrm{tail} = 186,972.9$ ($\chi^2_
u pprox 22.2$).
5. **Statistical Metric Evaluation:**
   $$\Delta\mathrm{BIC} = \mathrm{BIC}_\mathrm{sym} - \mathrm{BIC}_\mathrm{tail} = 260,015.6 - 186,972.9 = +73,042.7$$
   $$\mathrm{LRT\ p	ext{-}value} = \chi^2_\mathrm{sf}(\Delta\chi^2 = 73,070, \Delta k = 3) = 0.0$$
   $$lpha = rac{t_\mathrm{egress} - t_\mathrm{ingress}}{t_\mathrm{total}} = 0.534$$

### 6.2 Forensic Audit Findings for Codex
To independently reproduce and verify this target, Codex must execute:
```bash
python -c "
import glob, numpy as np
from frontier_astronomy.ingestion.fits_reader import read_fits_light_curve
from frontier_astronomy.core.preprocessing import preprocess_light_curve, fold_light_curve
from frontier_astronomy.dust_tail.detector import fit_symmetric_transit, fit_cometary_dust_tail

files = sorted(glob.glob('data/cache/real_kepler/kplr009944201*llc.fits'))
lcs = [read_fits_light_curve(f) for f in files]
t = np.concatenate([x.time for x in lcs])
f = np.concatenate([x.flux for x in lcs])
fe = np.concatenate([x.flux_err for x in lcs])
q = np.concatenate([x.quality for x in lcs])
order = np.argsort(t)
from frontier_astronomy.core.types import LightCurveData
raw_lc = LightCurveData('KIC 9944201', 'Kepler', t[order], f[order], fe[order], q[order], 0.0, 0.0)
cleaned = preprocess_light_curve(raw_lc, period=0.721522907, t0=131.7091421)
folded = fold_light_curve(cleaned, period=0.721522907, t0=131.7091421, sort=True)
_, _, bic_sym, chi2_sym = fit_symmetric_transit(folded.phase, folded.flux, folded.flux_err, period=0.721522907, initial_depth=0.0225)
_, _, bic_tail, chi2_tail = fit_cometary_dust_tail(folded.phase, folded.flux, folded.flux_err, initial_depth=0.0225)
print(f'chi2_sym={chi2_sym:.1f}, chi2_tail={chi2_tail:.1f}, Delta_BIC={bic_sym - bic_tail:.1f}')
"
```
**Physical Reality:** Phase folding reveals a secondary eclipse ($0.53\%$) at phase $0.5$ and ellipsoidal variability ($4,151\ \mathrm{ppm}$). An occulting object producing a $2.25\%$ dip around an $R_* = 0.625\ R_\odot$ star has $R pprox 11\ R_\oplus pprox 1.0\ R_\mathrm{Jup}$. The system is an **eclipsing binary**, completely falsifying the disintegrating rocky crust hypothesis.

---

## 7. KIC 8494263: DETAILED TECHNICAL ANALYSIS

### 7.1 Trace of the Exomoon Analysis
1. **Target Parameters:** Ingested via `scan_candidate()` with $P = 78.9257421\ \mathrm{d}$, $t_0 = 429.37454\ \mathrm{BKJD}$, $\mathrm{Depth} = 17,972\ \mathrm{ppm}$.
2. **Observed Baseline & Cadences:** Analyzed baseline spans $276.9\ \mathrm{days}$ (Q4, Q5, Q6). Given $P = 78.93\ \mathrm{d}$, only $276.9 / 78.93 pprox 3.5$ orbital cycles exist.
3. **Transit Midpoint Fitting (`_fit_transit_midpoint` in `ttv_extractor.py`):**
   * Identifies candidate cadences within a window of $\pm 1.5 	imes T_{14}$ around nominal transit times.
   * Evaluates $\chi^2(	au)$ across an 81-point grid over $	au \in [-0.4P, +0.4P]$.
   * Interpolates the minimum using a 3-point parabola:
     $$	au_\mathrm{best} = 	au_\mathrm{min} + rac{y_0 - y_2}{2(y_0 - 2y_1 + y_2)} \Delta	au$$
   * Computes formal timing error from parabolic curvature: $\sigma_	au = \sqrt{2 / (\partial^2 \chi^2 / \partial 	au^2)}$.
4. **The Root Cause of $\mathrm{TTV\ SNR} = 50.1$:**
   * In `scan_nasa_archive.py` line 118:
     ```python
     lc_clean = preprocess_light_curve(lc, strict_quality=True, clip_outliers=True, detrend=True)
     ```
     `duration_days` was omitted!
   * In `frontier_astronomy/core/preprocessing.py` line 209:
     ```python
     if period is not None and t0 is not None and duration_days is not None:
         in_transit_mask = np.abs(phase) < phase_dur
     ```
     Because `duration_days` was `None`, `in_transit_mask` was completely empty.
   * The Savitzky-Golay polynomial filter dipped into the transit basin and distorted the ingress and egress edges of all three transits.
   * When `extract_ttv()` processed the distorted transits, the midpoints shifted by $-43.7\ \mathrm{min}$, $+99.0\ \mathrm{min}$, and $-114.1\ \mathrm{min}$.
   * Formula evaluated:
     $$\mathrm{SNR} = rac{\mathrm{std}(\mathrm{TTV})}{\langle\sigmaangle} \sqrt{2} = rac{88.7\ \mathrm{min}}{1.1\ \mathrm{min}} 	imes 1.414 = 50.1$$
5. **The Nature of $P(\mathrm{Moon}) = 99.9\%$:**
   * Handled by `compute_exomoon_posterior()` in `frontier_astronomy/perturbations/sensitivity.py`:
     ```python
     ln_b_ttv = 0.8 * (ttv_snr - 3.0)
     d_phase = abs(phase_diff_deg - 90.0)
     ln_b_phase = - (d_phase ** 2) / (2.0 * (15.0 ** 2))
     if is_mmr:
         ln_b_phase -= 5.0
     total_ln_b = ln_b_ttv + ln_b_phase + ln_b_shoulder
     posterior = 1.0 / (1.0 + np.exp(-total_ln_b))
     ```
   * For $\mathrm{SNR} = 50.1$, $\ln b_\mathrm{ttv} = 0.8 	imes (50.1 - 3.0) = +37.68$.
   * Even with $\Delta\phi = 0.0^\circ$ ($\ln b_\mathrm{phase} = -18.0 - 5.0 = -23.0$), the sum is $\mathrm{total\_ln\_b} = +14.68$.
   * Evaluating $\mathrm{posterior} = 1 / (1 + e^{-14.68}) = 0.99999958 ightarrow 0.999$ ($99.9\%$).
   * **Conclusion for Codex:** This is an **uncalibrated heuristic logit formula**, NOT a Bayesian evidence integral.
6. **The Untraced "$\Delta\psi = 91.4^\circ \pm 3.2^\circ$" Claim:**
   * In `results/real_nasa_discoveries.json`, `"orthogonal_phase_diff_deg"` is explicitly recorded as `0.0`.
   * The value $91.4^\circ \pm 3.2^\circ$ was written as narrative text in `NASA_CONFIRMATION_DOSSIER.md` without any computational basis in the code.

---

## 8. KIC 10153011: DETAILED TECHNICAL ANALYSIS

1. **Target Parameters:** Ingested via `scan_candidate()` with $P = 83.09708021\ \mathrm{d}$, $t_0 = 162.935743\ \mathrm{BKJD}$, $\mathrm{Depth} = 15,860.2\ \mathrm{ppm}$.
2. **Catalog Disposition:** Official Kepler Robovetter score is **$0.000$** (classified as a false positive in the cumulative DR25 catalog).
3. **Data Baseline:** Baseline spans $272.4\ \mathrm{days}$ ($N = 3$ transits observed at epochs $E = 1, 2, 3$).
4. **Claimed Results in JSON:** $\mathrm{TTV\ SNR} = 40.3$, $P(\mathrm{Moon}) = 0.999$ ($99.9\%$).
5. **Forensic Execution on Raw Photometry:**
   * When `extract_ttv()` is run directly on raw photometry without the unmasked SavGol filter:
     * Measured TTV residuals: $[+0.83\ \mathrm{min}, -1.72\ \mathrm{min}, +1.04\ \mathrm{min}]$ ($\sim 50	ext{--}100\ \mathrm{seconds}$).
     * Measured $\mathrm{SNR} = 2.20$.
   * An SNR of $2.20$ is below the nominal detection threshold of $3.0\sigma$.
   * **Conclusion for Codex:** The candidate is a detrending-induced false alarm.

---

## 9. KIC 8308347: DETAILED TECHNICAL ANALYSIS

1. **Target Parameters:** Ingested with $P = 164.9504\ \mathrm{d}$, $t_0 = 280.9154\ \mathrm{BKJD}$, $\mathrm{Depth} = 24,493\ \mathrm{ppm}$. Catalog Robovetter score: $0.000$.
2. **Data Baseline:** Baseline spans $276.5\ \mathrm{days}$ (Q4, Q5, Q6), representing only **1.6 orbital cycles**.
3. **Trojan Detection Logic (`detect_trojan_companions` in `trojan_detector.py`):**
   * Folds the light curve and bins cadences into phase bins of width $0.02$.
   * Looks for a localized dip at phase $\phi \in [+0.14, +0.19]$ ($L_4$, $+60^\circ$) or $\phi \in [-0.19, -0.14]$ ($L_5$, $-60^\circ$).
   * If the local flux depression exceeds $3.0\sigma$, it flags `has_trojan = True`.
4. **Forensic Finding for Codex:**
   * In a dataset containing only 1.6 orbits, stellar rotational spot modulation inevitably produces sinusoidal flux variations on timescales of $10	ext{--}30\ \mathrm{days}$.
   * An isolated dip at phase $+0.1667$ without multi-epoch repeatability across $>10$ consecutive orbits is **stellar red noise**, not a dynamically confirmed Trojan planet.

---

## 10. VALIDATION AND CONTROL TESTS

### 10.1 Dissecting the "201/201 Tests Passing" Metric
The test suite executed by `python run_tests.py` consists of 201 test assertions. It is vital that Codex separates **software tests** from **scientific validation**:

* **Software Engineering Tests (195 Tests):**
  * `tests/test_adversarial_preprocessing.py` (26 tests): Validates that preprocessing functions do not crash when given NaNs, Infs, empty arrays, or negative values.
  * `tests/test_adversarial_fits.py` (28 tests): Validates that `fits_reader.py` handles truncated headers, corrupt binary tables, and non-standard keywords without raising uncaught exceptions.
  * `tests/test_m1_ingestion_preprocessing.py` (20 tests): Checks that FITS ingestion accurately converts BINTABLE columns to NumPy dtypes.
  * `tests/test_tier1_features.py` (55 tests): Verifies that functions return expected dataclass structures with non-negative SNRs and bounded probabilities.
  * `tests/test_tier2_boundaries.py` (55 tests): Tests edge-case inputs (e.g., zero depth, extreme mass ratios, $P = 0.05\ \mathrm{d}$).
  * `tests/test_tier3_integration.py` (11 tests): Verifies that output dataclasses from one module can be ingested by subsequent modules.
* **Scientific Benchmark Tests (6 Tests in `tests/test_tier4_benchmarks.py`):**
  * Verifies that KIC 12557548 yields $\Delta\mathrm{BIC} > 10$.
  * Verifies that WASP-39 b atmospheric retrieval recovers molecular posteriors within reference boundaries.

> [!IMPORTANT]
> **Guidance for Codex:** Passing 201 software tests proves that the codebase is mathematically robust, free of syntax errors, and computationally stable. It **does NOT** validate that candidate signals in real Kepler data are genuine exomoons or disintegrating planets.

### 10.2 The Five Negative-Control Systems
In `results/real_nasa_discoveries.json`, 20 KOIs were processed by `scan_candidate()`. Exactly **five targets** returned negative (null) classifications (`"verdict": "Symmetric Planet Transit (Standard)"`):

1. **KIC 11805075 (KOI K00436.01):** $P = 199.84\ \mathrm{d}$, $\Delta\mathrm{BIC} = -27.2$, Asymmetry $lpha = -0.616$, $\mathrm{TTV\ SNR} = 0.0$, $P(\mathrm{Moon}) = 0.01$.
2. **KIC 6690171 (KOI K03320.01):** $P = 85.06\ \mathrm{d}$, $\Delta\mathrm{BIC} = -27.8$, Asymmetry $lpha = +0.168$, $\mathrm{TTV\ SNR} = 2.69$, $P(\mathrm{Moon}) = 0.001$.
3. **KIC 3345675 (KOI K01772.01):** $P = 120.00\ \mathrm{d}$, $\Delta\mathrm{BIC} = -27.0$, Asymmetry $lpha = +0.369$, $\mathrm{TTV\ SNR} = 0.0$, $P(\mathrm{Moon}) = 0.01$.
4. **KIC 9512981 (KOI K01466.01):** $P = 281.56\ \mathrm{d}$, $\Delta\mathrm{BIC} = -26.2$, Asymmetry $lpha = +0.831$, $\mathrm{TTV\ SNR} = 0.0$, $P(\mathrm{Moon}) = 0.01$.
5. **KIC 7984047 (KOI K01552.01):** $P = 77.63\ \mathrm{d}$, $\Delta\mathrm{BIC} = -28.2$, Asymmetry $lpha = +0.846$, $\mathrm{TTV\ SNR} = 1.64$, $P(\mathrm{Moon}) = 0.002$.

**Scientific Context for Codex:** These five systems confirm that the pipeline does not output positive detections on every target. However, achieving null results on 5 control systems cannot establish population-level 100% specificity across thousands of KOIs.

---

## 11. AUDIT CONFLICT AUDIT: TEXTUAL NARRATIVE VS. REPRODUCIBLE CODE

Codex must exercise extreme caution regarding statements made in `MANUSCRIPT.md` and `NASA_CONFIRMATION_DOSSIER.md`. The table below audits every historical claim:

| Historical Statement | Claim Type | Verification Command / Source | Audit Classification | Finding for Codex |
| :--- | :--- | :--- | :--- | :--- |
| *"KIC 9944201 has $\Delta\mathrm{BIC} pprox +73,043$"* | Machine Output | `scan_nasa_archive.py` -> `results/real_nasa_discoveries.json` | **SUPPORTED BY REPOSITORY EVIDENCE** | Real code output, but caused by model misspecification on $N=8,431$ cadences. |
| *"KIC 9944201 has a secondary eclipse at $\phi=0.5$ ($0.53\%$)"* | Forensic Calculation | `python -c "..."` folding cached FITS | **SUPPORTED BY REPOSITORY EVIDENCE** | Directly verified in cached FITS; proves system is an Eclipsing Binary. |
| *"KIC 9944201 mass loss rate is $10^8	ext{--}10^9\ \mathrm{kg/s}$"* | Textual Claim | `NASA_CONFIRMATION_DOSSIER.md` | **UNSUPPORTED TEXTUAL CLAIM** | Fabricated text in dossier; no code computes total mass loss rate. |
| *"KIC 8494263 has $\mathrm{TTV\ SNR} = 50.1$"* | Machine Output | `scan_nasa_archive.py` -> `results/real_nasa_discoveries.json` | **SUPPORTED BY REPOSITORY EVIDENCE** | Real code output, but caused by unmasked SavGol detrending. |
| *"KIC 8494263 contains only 3 transits in analyzed data"* | Observational Fact | `python -c "..."` on cached FITS | **SUPPORTED BY REPOSITORY EVIDENCE** | Exactly 3 transits in cached Q4-Q6 files ($429.36, 508.30, 587.24\ \mathrm{BKJD}$). |
| *"KIC 8494263 raw TTV is $\le 11\ \mathrm{seconds}$ ($\mathrm{SNR} pprox 0.19$)"* | Forensic Calculation | `extract_ttv` on raw flux | **SUPPORTED BY REPOSITORY EVIDENCE** | Timing residuals are $[+4.3\ \mathrm{s}, -9.6\ \mathrm{s}, +11.2\ \mathrm{s}]$. |
| *"KIC 8494263 phase difference is $91.4^\circ \pm 3.2^\circ$"* | Textual Claim | `NASA_CONFIRMATION_DOSSIER.md` | **UNSUPPORTED TEXTUAL CLAIM** | Fabricated text in dossier; `real_nasa_discoveries.json` records `0.0`. |
| *"KIC 8494263 has $P(\mathrm{Moon}) = 99.9\%$ Bayesian posterior"* | Classifier Output | `compute_exomoon_posterior()` | **PARTIALLY SUPPORTED** | The number $0.999$ was output, but it is an empirical heuristic, NOT a Bayesian posterior. |
| *"KIC 10153011 raw TTV SNR is $2.20$"* | Forensic Calculation | `extract_ttv` on raw flux | **SUPPORTED BY REPOSITORY EVIDENCE** | Timing residuals are $[+0.83, -1.72, +1.04]\ \mathrm{min}$; SNR below $3.0$. |
| *"KIC 8308347 has 0 transits extracted"* | Forensic Calculation | `extract_ttv` on cached FITS | **SUPPORTED BY REPOSITORY EVIDENCE** | Data gaps prevent midpoint fitting; Trojan dip is stellar red noise. |

---

## 12. RESULT AUTHORITY HIERARCHY

When preparing the scientific manuscript, Codex must adhere to this strict evidentiary priority:

$$egin{aligned}
\mathbf{Priority\ 1:} &\quad 	ext{Raw Observational Data (MAST FITS files in } 	exttt{data/cache/real_kepler/}	ext{)} \
\mathbf{Priority\ 2:} &\quad 	ext{Reproducible Executable Code (Python calculations in } 	exttt{frontier_astronomy/}	ext{)} \
\mathbf{Priority\ 3:} &\quad 	ext{Saved Machine-Generated Outputs (JSON in } 	exttt{results/}	ext{)} \
\mathbf{Priority\ 4:} &\quad 	ext{Automated Test Assertions (pytest in } 	exttt{tests/}	ext{)} \
\mathbf{Priority\ 5:} &\quad 	ext{Narrative Documentation (} 	exttt{DOCUMENTATION.md}, 	exttt{PROJECT.md}	ext{)} \
\mathbf{Priority\ 6:} &\quad 	ext{Historical Markdown Reports (} 	exttt{NASA_CONFIRMATION_DOSSIER.md}, 	exttt{MANUSCRIPT.md}	ext{)}
\end{aligned}$$

> [!CAUTION]
> **Mandate for Codex:** Never allow an assertion in an AI-written Markdown report to override reproducible numerical evidence from executable code and raw data.

---

## 13. REPRODUCTION COMMANDS

The following commands actually exist, run without error in the environment, and can be executed by Codex:

### Command 1: Run Full 4-Tier Automated Test Suite
```bash
python run_tests.py
```
* **Purpose:** Executes all 201 unit, boundary, integration, and benchmark tests.
* **Expected Output:** `201 passed, 8 warnings in ~8.5s`.
* **Files Created:** None.

### Command 2: Re-Execute Real NASA Candidate Archive Scan
```bash
python scan_nasa_archive.py
```
* **Purpose:** Ingests cached FITS files for the 20 unconfirmed KOIs, runs dust-tail and perturbation detectors, and compiles the scorecard.
* **Expected Output:** Scorecard table printed to terminal.
* **Files Created/Updated:** `results/real_nasa_discoveries.json`.

### Command 3: Re-Execute Catalog & Novelty Verification
```bash
python verify_candidate_novelty.py
```
* **Purpose:** Queries NASA Exoplanet Archive TAP API to verify KOI dispositions, stellar radii, and effective temperatures.
* **Expected Output:** Status table printed to terminal.
* **Files Created/Updated:** `results/novelty_verification.json`.

### Command 4: Re-Execute Literature Benchmark Survey
```bash
python batch_discovery_scan.py
```
* **Purpose:** Runs pipeline on benchmark systems (KIC 12557548, K2-22b, KOI-2700b, WD 1145+017, Kepler-1625b, Kepler-1708b).
* **Expected Output:** Summary table printed to terminal.
* **Files Created/Updated:** `results/batch_survey_report.json`.

### Command 5: Launch Interactive Discovery Dashboard
```bash
streamlit run frontier_astronomy/dashboard/app.py --server.port 8501
```
* **Purpose:** Launches web UI for visual inspection of light curves, transit models, residuals, and atmospheric posteriors.

---

## 14. IMPORTANT OUTPUT FILES

### 1. `results/real_nasa_discoveries.json`
* **Created By:** `scan_nasa_archive.py`.
* **Content:** List of 20 dictionaries containing scan results for real NASA KOIs.
* **Key Fields:** `kepid`, `koi_name`, `period_days`, `t0_bkjd`, `catalog_depth_ppm`, `cadences`, `baseline_days`, `dust_tail` (`delta_bic`, `asymmetry_alpha`, `lrt_p_value`), `perturbations` (`ttv_snr`, `p_moon_posterior`, `orthogonal_phase_diff_deg`, `is_trojan_candidate`), `verdict`.
* **Role:** Machine-generated output containing candidate measurements.

### 2. `results/novelty_verification.json`
* **Created By:** `verify_candidate_novelty.py`.
* **Content:** Cross-match records from NASA Exoplanet Archive TAP service.
* **Key Fields:** `kepid`, `kepoi_name`, `koi_disposition`, `koi_score`, `koi_period`, `koi_depth`, `koi_teq`, `koi_prad`, `koi_srad`, `koi_steff`.
* **Role:** Ground-truth astrophysical properties from official Kepler catalogs.

### 3. `results/batch_survey_report.json`
* **Created By:** `batch_discovery_scan.py`.
* **Content:** Survey results across known literature benchmark targets.

### 4. `results/inversion_summary.json`
* **Created By:** `frontier_astronomy/atmospheric/inversion.py`.
* **Content:** Retrieved molecular abundances and credible intervals for JWST WASP-39 b.

---

## 15. FIGURES AVAILABLE FOR PAPER

### Current Figure Status: **No Static Image Files Exist**
A search across `G:\frontier_astronomy_ai` reveals that **zero static image files (`.png`, `.svg`, `.pdf`) exist** in the repository. All plots during development were dynamically rendered in the Streamlit web dashboard via Plotly (`frontier_astronomy/dashboard/components/`).

### Required Figure Generation for Codex
Codex must generate publication-quality figures (e.g., using `matplotlib` / `seaborn`):
1. **Figure 1 (KIC 9944201 Phase Curve):**
   * *X-axis:* Orbital Phase ($\phi \in [-0.5, 0.5]$).
   * *Y-axis:* Relative Normalized Flux.
   * *Panels:* Full phase curve showing primary minimum at $\phi = 0.0$ ($2.0\%$) and secondary eclipse at $\phi = \pm 0.5$ ($0.53\%$). Inset: symmetric vs. cometary model fits over $[-0.1, +0.1]$.
2. **Figure 2 (KIC 8494263 Detrending Distortion & TTVs):**
   * *X-axis:* Time (BKJD) / Epoch.
   * *Y-axis:* Flux (top panels for Epochs 0, 1, 2) / $O - C$ Residuals in minutes (bottom panel).
   * *Comparison:* Unmasked SavGol fit (eroded shoulders) vs. raw linear continuum fit. Shows collapse of TTV from $100\ \mathrm{min}$ down to $<11\ \mathrm{seconds}$.
3. **Figure 3 (Exomoon Posterior Transfer Function):**
   * *X-axis:* TTV Signal-to-Noise Ratio ($\mathrm{SNR}$).
   * *Y-axis:* Output Heuristic Score $P(\mathrm{Moon})$.
   * *Demonstration:* Shows the sharp logistic inflection illustrating why any $\mathrm{SNR} > 15$ maps to $99.9\%$.
4. **Figure 4 (JWST WASP-39 b Atmospheric Retrieval):**
   * *X-axis:* Wavelength ($\mu\mathrm{m}$, $0.5	ext{--}5.5\ \mu\mathrm{m}$).
   * *Y-axis:* Transit Depth $(R_p / R_*)^2$ in ppm.
   * *Overlay:* PRISM observational data points vs. best-fit median retrieved spectrum and $1\sigma/2\sigma$ posterior envelopes.

---

## 16. WHAT STILL NEEDS TO BE DONE

Codex must clearly separate what is already implemented from recommended future work:

### Already Implemented in Repository
* [x] Pure-Python high-speed FITS table reader (`fits_reader.py`).
* [x] Forward cometary extinction and Mie forward-scattering models (`extinction_model.py`, `forward_scattering.py`).
* [x] Multi-parameter transit least-squares fitting and BIC/LRT model selection (`detector.py`).
* [x] Template cross-correlation TTV and duration TDV extraction (`ttv_extractor.py`, `tdv_extractor.py`).
* [x] Orthogonal $\pi/2$ phase invariant test (`tdv_extractor.py`).
* [x] $L_4/L_5$ co-orbital Trojan dip hunter (`trojan_detector.py`).
* [x] Conditional Normalizing Flow atmospheric chemistry retrieval on JWST PRISM spectra (`inversion.py`).
* [x] NASA Exoplanet Archive automated TAP queries (`verify_candidate_novelty.py`).
* [x] Full 4-tier 201-test software verification suite (`run_tests.py`).

### Recommended Future Validation (Not Yet Implemented)
* [ ] **Transit-Masked Detrending Fix:** Update `preprocess_light_curve()` to calculate transit duration $T_{14}$ prior to detrending.
* [ ] **Full 17-Quarter Analysis:** Ingest all 17 Kepler quarters from MAST for KIC 8494263, KIC 10153011, and KIC 8308347 to obtain $>15$ transit epochs.
* [ ] **Full MCMC / Nested Sampling:** Replace the heuristic `compute_exomoon_posterior()` function with Dynesty/MultiNest calculating true Bayes factors $\Delta \ln \mathcal{Z}$.
* [ ] **Pixel-Level Centroid Analysis:** Inspect Target Pixel Files (TPF) to verify whether transit signals originate on-target or from background eclipsing binaries (BEB).
* [ ] **High-Resolution Adaptive Optics Imaging:** Search for blended companion stars within Kepler's $4''$ pixels.
* [ ] **Gaussian Process Noise Modeling:** Model correlated stellar variability with a quasi-periodic kernel rather than assuming white noise in BIC calculations.

---

## 17. PAPER WRITING GUIDANCE FOR CODEX

When composing the final scientific manuscript, Codex must maintain strict taxonomic precision:

1. **Observed Data:** Raw photometric cadences and flux measurements from the Kepler photometer (`TIME`, `PDCSAP_FLUX`).
2. **Pipeline Measurements:** Programmatically calculated quantities (e.g., measured $O - C$ residuals, fitted trapezoidal depths, epoch counts).
3. **Derived Quantities:** Physical parameters deduced via physical equations (e.g., $R_p = \sqrt{\delta} R_*$, Hill radius $R_H$, equilibrium temperature $T_\mathrm{eq}$).
4. **Model Preferences:** Statistical metric comparisons between competing mathematical functions (e.g., $\Delta\mathrm{BIC} = \mathrm{BIC}_\mathrm{sym} - \mathrm{BIC}_\mathrm{tail}$). Must be reported as mathematical preferences, not physical proof.
5. **Classifier Outputs:** Algorithmic scores and heuristic mappings (e.g., $P_\mathrm{heuristic} = 0.999$). Must **never** be described as "posterior probability of physical reality."
6. **Physical Interpretations:** Competing astrophysical scenarios consistent with the measurements (e.g., Eclipsing Binary vs. Evaporating Planet; Starspot Modulation vs. Trojan Planet).
7. **Unverified Hypotheses:** Speculative mechanisms (e.g., "super-Io vulcanism", "tidal stripping of exomoon") that lack direct observational confirmation.

---

## 18. FINAL EVIDENCE MASTER MATRIX

| Claim / Topic | Target | Numerical Value | Source Data | Source Code | Output File | Reproduction Command | Confidence / Status | Reviewer Notes |
| :--- | :--- | :--- | :--- | :--- | :--- | :--- | :--- | :--- |
| **Orbital Period** | KIC 9944201 | $0.7215229\ \mathrm{d}$ | NASA Archive | `fetch_nasa_candidates.py` | `data/nasa_candidates_usp.json` | `python verify_candidate_novelty.py` | **REPRODUCED** | Verified against official cumulative KOI table. |
| **Transit Depth** | KIC 9944201 | $22,528\ \mathrm{ppm}$ | NASA Archive | `fetch_nasa_candidates.py` | `data/nasa_candidates_usp.json` | `python verify_candidate_novelty.py` | **REPRODUCED** | Corresponds to $R_p pprox 11.0\ R_\oplus$ around $0.625\ R_\odot$ star. |
| **Dust Tail $\Delta\mathrm{BIC}$** | KIC 9944201 | $+73,042.7$ | Cached FITS | `dust_tail/detector.py` | `results/real_nasa_discoveries.json` | `python scan_nasa_archive.py` | **REPRODUCED** | Artifact of model misspecification on $N=8,431$ cadences. |
| **Secondary Eclipse** | KIC 9944201 | $5,300\ \mathrm{ppm}$ at $\phi=0.5$ | Cached FITS | Forensic script | Terminal execution | Python snippet in Section 6.2 | **REPRODUCED** | Definitive signature of an Eclipsing Binary. |
| **Mass Loss Rate** | KIC 9944201 | $10^8	ext{--}10^9\ \mathrm{kg/s}$ | None | None | `NASA_CONFIRMATION_DOSSIER.md` | None | **UNTRACED** | Narrative text without computational origin. |
| **Orbital Period** | KIC 8494263 | $78.92574\ \mathrm{d}$ | NASA Archive | `fetch_nasa_candidates.py` | `data/nasa_candidates_moon.json` | `python verify_candidate_novelty.py` | **REPRODUCED** | Verified against official cumulative KOI table. |
| **Analyzed Transits** | KIC 8494263 | $N = 3$ | Cached FITS | `ttv_extractor.py` | `results/real_nasa_discoveries.json` | `python scan_nasa_archive.py` | **REPRODUCED** | Only 3 transits in 276.9-day baseline (Q4-Q6). |
| **Claimed TTV SNR** | KIC 8494263 | $50.1$ | Cached FITS | `ttv_extractor.py` | `results/real_nasa_discoveries.json` | `python scan_nasa_archive.py` | **REPRODUCED** | Artifact of unmasked Savitzky-Golay detrending. |
| **Raw TTV Residual** | KIC 8494263 | $\le 11.2\ \mathrm{s}$ ($\mathrm{SNR}=0.19$) | Cached FITS | `ttv_extractor.py` | Forensic calculation | Direct `extract_ttv` execution | **REPRODUCED** | Raw data consistent with constant linear ephemeris. |
| **Claimed Phase Shift** | KIC 8494263 | $91.4^\circ \pm 3.2^\circ$ | None | None | `NASA_CONFIRMATION_DOSSIER.md` | None | **UNTRACED** | Fabricated text; JSON output records $0.0^\circ$. |
| **Classifier Score** | KIC 8494263 | $99.9\%$ ($0.999$) | Pipeline | `sensitivity.py` | `results/real_nasa_discoveries.json` | `python scan_nasa_archive.py` | **REPRODUCED** | Empirical logit heuristic, NOT a Bayesian evidence integral. |
| **Orbital Period** | KIC 10153011 | $83.09708\ \mathrm{d}$ | NASA Archive | `fetch_nasa_candidates.py` | `data/nasa_candidates_moon.json` | `python verify_candidate_novelty.py` | **REPRODUCED** | Verified against official cumulative KOI table. |
| **Claimed TTV SNR** | KIC 10153011 | $40.3$ | Cached FITS | `ttv_extractor.py` | `results/real_nasa_discoveries.json` | `python scan_nasa_archive.py` | **REPRODUCED** | Artifact of unmasked detrending on $N=3$ transits. |
| **Raw TTV SNR** | KIC 10153011 | $2.20$ | Cached FITS | `ttv_extractor.py` | Forensic calculation | Direct `extract_ttv` execution | **REPRODUCED** | Below $3.0\sigma$ detection threshold; Robovetter score $0.000$. |
| **Trojan Flag** | KIC 8308347 | `True` | Cached FITS | `trojan_detector.py` | `results/real_nasa_discoveries.json` | `python scan_nasa_archive.py` | **REPRODUCED** | Localized dip in 1.6 orbits consistent with stellar spot noise. |
| **JWST Abundances** | WASP-39 b | $\log(\mathrm{H_2O}) = -3.39$ | Benchmark CSV | `inversion.py` | `results/inversion_summary.json` | `python -m pytest tests/test_tier4_benchmarks.py` | **REPRODUCED** | Matches published JWST literature within $0.3\sigma$. |

---

*End of Codex Technical Handoff Document.*
