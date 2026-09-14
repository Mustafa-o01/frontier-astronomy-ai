# Original User Request

## Initial Request — 2026-09-14T01:14:19Z

Build an end-to-end Frontier Astronomy AI Discovery Suite combining three unprecedented detection capabilities on real NASA observational data: (1) Catastrophic Disintegrating Exoplanet & Dust Tail Hunter, (2) Exomoon & Trojan Planet Gravitational Perturbation Detector, and (3) Rapid Atmospheric Chemistry Inversion for NASA JWST Transmission Spectra.

Working directory: G:\frontier_astronomy_ai
Integrity mode: demo

## Requirements

### R1. Disintegrating Exoplanet & Exocomet Dust Tail Hunter
Ingest and analyze photometric time-series from NASA Kepler and TESS public archives. Implement an automated detector specifically capable of distinguishing asymmetric, variable-depth transits (caused by trailing cometary dust clouds and catastrophically evaporating rocky crusts) from ordinary symmetric exoplanetary transits.

### R2. Exomoon & Trojan World Gravitational Perturbation Detector
Model and decouple mutual multi-body gravitational transit perturbations. Surface candidate exomoons and co-orbital Trojan worlds by isolating subtle Transit Timing Variations (TTVs) and secondary transit shoulder anomalies from stellar baseline noise.

### R3. Rapid Atmospheric Chemistry Inversion for NASA JWST
Perform amortized Bayesian parameter estimation on exoplanet transmission spectrophotometry (such as NIRSpec/NIRISS data from NASA's James Webb Space Telescope) to predict molecular volume mixing ratios (H2O, CO2, CH4) and cloud/haze parameters along with Bayesian posterior uncertainty estimates.

### R4. Unified Interactive Discovery & Inspection Dashboard
Provide an interactive visual analytics dashboard to inspect candidate anomalies, compare raw telescope signals against model reconstructions, visualize localized residual anomaly heatmaps, and interactively filter candidate targets.

### R5. Data Ingestion & Computational Infrastructure
Fetch observational time-series and spectra directly from public NASA open data archives (NASA MAST, Kepler, TESS, and JWST) or leverage relevant open-source astronomical packages / GitHub repositories and skills where appropriate. Ensure all computational models, automated validation pipelines, and dashboard interfaces run in the working directory G:\frontier_astronomy_ai.

## Acceptance Criteria

### Detection & Model Verification
- [ ] Automated synthetic injection-recovery tests demonstrate statistically significant recovery of asymmetric, variable dust-tail transits against standard symmetric transit baselines.
- [ ] Validation suite confirms sensitivity to secondary transit perturbations down to signal-to-noise ratios representative of realistic planet-moon configurations.
- [ ] Fast atmospheric retrieval on benchmark exoplanet transmission spectra reproduces reference molecular abundance posteriors within 1-sigma credible intervals.
- [ ] End-to-end automated test suite executes programmatically and passes with zero errors.

### Delivery & User Interface
- [ ] Interactive discovery dashboard runs locally and displays candidate detection profiles, transit residuals, and atmospheric posterior distributions.
- [ ] Complete documentation provided detailing data ingestion, model architectures, verification results, and cataloged candidate discoveries.
