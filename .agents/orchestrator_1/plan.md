# Plan: Frontier Astronomy AI Discovery Suite Orchestration

## Objective
Deliver a production-ready, fully verified Frontier Astronomy AI Discovery Suite running locally in `G:\frontier_astronomy_ai` with:
1. Disintegrating Exoplanet & Dust Tail Hunter (Kepler/TESS time-series, asymmetric variable-depth transit detection).
2. Exomoon & Trojan World Gravitational Perturbation Detector (multi-body transit perturbations, TTVs, secondary shoulder anomalies).
3. Rapid Atmospheric Chemistry Inversion for NASA JWST Transmission Spectra (amortized Bayesian parameter estimation, molecular VMRs H2O/CO2/CH4, cloud/haze parameters, posterior uncertainties).
4. Unified Interactive Discovery & Inspection Dashboard (visual analytics, raw signal vs model reconstructions, residual heatmaps, candidate filtering).
5. Robust Data Ingestion & Infrastructure (NASA MAST, Kepler, TESS, JWST data ingestion, verification pipelines, running in `G:\frontier_astronomy_ai`).

## Phased Execution Strategy
- **Phase 0: Survey (Top-Level Orchestration)**
  - Spawn 3 parallel Explorers to survey:
    - Explorer 1: Scientific models & physics formulations (dust tail scattering models, asymmetric transit profiles like Rappaport/Brogi models, exomoon/Trojan TTV/TDV & photodynamic models, JWST transmission spectroscopy forward models & Bayesian amortized neural inversion).
    - Explorer 2: Data ingestion & NASA archives interfaces (lightkurve, astroquery/MAST, Kepler/TESS target pixel / light curve files, JWST NIRSpec/NIRISS spectra archives, benchmark datasets: KIC 12557548, K2-22b, Kepler-1625b, WASP-39b, WASP-96b).
    - Explorer 3: System architecture, testing infrastructure & interactive dashboard (modular package structure, E2E test framework, synthetic injection-recovery harness, Streamlit/Dash/FastAPI dashboard architecture, packaging and dependencies in Python/Windows).
- **Phase 1: Project Architecture & Feature Inventory (PROJECT.md & TEST_INFRA.md)**
  - Synthesize Explorer findings.
  - Establish `PROJECT.md` with complete Feature Inventory, Milestones, Code Layout, Interface Contracts.
  - Establish `TEST_INFRA.md` with 4-tier test architecture, verification thresholds, and test harness design.
- **Phase 2: Dual Track Dispatch**
  - **Track A: E2E Testing Track Orchestrator**
    - Sub-orchestrator designs and implements test harness, synthetic injection benchmarks, validation datasets, and Tier 1-4 automated tests.
    - Publishes `TEST_READY.md`.
  - **Track B: Implementation Track (Sub-orchestrators for milestones)**
    - Milestone 1: Data Ingestion & NASA Archive Client (Kepler/TESS/JWST fetching, local caching, mock/synthetic fallback generators).
    - Milestone 2: Disintegrating Exoplanet & Exocomet Dust Tail Hunter (asymmetric profile modeling, cometary dust tail dynamics, variable depth detection, statistical recovery).
    - Milestone 3: Exomoon & Trojan World Gravitational Perturbation Detector (TTV/TDV extraction, multi-body transit perturbation modeling, secondary shoulder anomaly detector).
    - Milestone 4: Rapid Atmospheric Chemistry Inversion for NASA JWST (forward radiative transfer / atmospheric grid, amortized neural posterior estimation, VMR & haze extraction, 1-sigma credible interval benchmarks).
    - Milestone 5: Unified Interactive Discovery & Inspection Dashboard (visual analytics, candidate filtering, residual heatmaps, raw vs reconstruction viewers).
- **Phase 3: Integration & Final Milestone**
  - Phase 1: 100% E2E test pass across Tiers 1-4.
  - Phase 2: Adversarial coverage hardening (Tier 5) with Challenger -> Worker -> Reviewer -> Forensic Auditor loop.
- **Phase 4: Final Documentation, Verification, & Delivery Report to Sentinel**
