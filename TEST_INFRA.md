# E2E Test Infra: Frontier Astronomy AI Discovery Suite

## Test Philosophy
- **Opaque-box & Requirement-Driven**: Derived strictly from `ORIGINAL_REQUEST.md` and user acceptance criteria, independent of implementation internals.
- **Progressive Testability**: Verification mechanisms do not depend on features more complex than what is being tested. Tier 1 provides immediate pass/fail signals for isolated modules.
- **Hermetic & Deterministic**: All tests run completely offline using pre-bundled real NASA benchmark fixtures (`data/benchmarks/`) and deterministic synthetic signal generators.
- **Methodology**: Systematic 4-Tier hierarchy (Category-Partition, Boundary Value Analysis, Pairwise Combinatorial Integration, Real-World Benchmark Scenarios) followed by Tier 5 adversarial coverage hardening.

---

## Feature Inventory Coverage Mapping

| # | Feature ID | Feature Name | Source | Tier 1 (Min 5) | Tier 2 (Min 5) | Tier 3 (Pairwise) | Tier 4 (Workload) |
|---|------------|--------------|--------|:--------------:|:--------------:|:-----------------:|:-----------------:|
| 1 | F1 | Pure-Python FITS & MAST Ingestion | R5 | 5 | 5 | ✓ | ✓ |
| 2 | F2 | Time-Series Preprocessing & Detrending | R1, R2, R5 | 5 | 5 | ✓ | ✓ |
| 3 | F3 | Disintegrating Planet & Dust Tail Hunter | R1 | 5 | 5 | ✓ | ✓ |
| 4 | F4 | Synthetic Injection-Recovery Suite | Acceptance Criteria 1 | 5 | 5 | ✓ | ✓ |
| 5 | F5 | Exomoon & Trojan Perturbation Detector | R2 | 5 | 5 | ✓ | ✓ |
| 6 | F6 | Multi-Body Sensitivity Validation | Acceptance Criteria 2 | 5 | 5 | ✓ | ✓ |
| 7 | F7 | JWST Forward Radiative Transfer | R3 | 5 | 5 | ✓ | ✓ |
| 8 | F8 | Rapid Amortized Bayesian Inversion | R3 | 5 | 5 | ✓ | ✓ |
| 9 | F9 | Benchmark Atmospheric Validation | Acceptance Criteria 3 | 5 | 5 | ✓ | ✓ |
| 10 | F10 | Unified Interactive Discovery Dashboard | R4 | 5 | 5 | ✓ | ✓ |
| 11 | F11 | Discovery Interface & Orchestration CLI | R4, R5 | 5 | 5 | ✓ | ✓ |

Total identified features: $N = 11$.

---

## Minimum Test Case Thresholds
- **Tier 1 (Feature Coverage)**: $5 \times 11 = 55$ test cases
- **Tier 2 (Boundary & Corner Cases)**: $5 \times 11 = 55$ test cases
- **Tier 3 (Cross-Feature Combinations)**: $11$ multi-feature integration workflows
- **Tier 4 (Real-World Application Scenarios)**: $\max(5, \lceil 11/2 \rceil) = 6$ application-level benchmark scenarios
- **Total Minimum Threshold**: $\ge 127$ test assertions executed via programmatic test runner with 0 errors.

---

## Test Architecture & Directory Layout
```
tests/
├── __init__.py
├── conftest.py                     # Shared fixtures, synthetic generators, benchmark paths
├── test_tier1_features.py         # Tier 1: Isolated unit tests (>=55 test cases)
├── test_tier2_boundaries.py       # Tier 2: Extreme values, noise, missing cadences (>=55 test cases)
├── test_tier3_integration.py      # Tier 3: End-to-end multi-module pipelines (>=11 workflows)
└── test_tier4_benchmarks.py       # Tier 4: Real-world NASA benchmark acceptance tests
```

---

## Real-World Application Scenarios (Tier 4 Acceptance Benchmarks)

| # | Scenario | Features Exercised | Pass Criteria |
|---|----------|--------------------|---------------|
| 1 | **Synthetic Dust-Tail Injection-Recovery** | F1, F2, F3, F4 | $\ge 90\%$ recovery rate at $\text{SNR} \ge 5.0$; false positive rate $\le 2.0\%$; $\Delta\text{BIC} \ge 10$ on recovered candidates. |
| 2 | **KIC 12557548 Real Disintegrating Planet Benchmark** | F1, F2, F3 | Correct identification of asymmetric cometary tail ($\alpha > 0.3$), variable depth across quarters ($0.2\% - 1.2\%$), and rejection of symmetric model with $\Delta\text{BIC} \ge 15$. |
| 3 | **Multi-Body Exomoon Sensitivity Limit Validation** | F2, F5, F6 | Statistically significant detection of TTV and secondary transit shoulders down to $\text{SNR} = 3.0$ for realistic satellite-to-planet mass ratios ($M_s/M_p \sim 0.01 - 0.05$). |
| 4 | **Kepler-1625b / Kepler-1708b Exomoon Candidate Evaluation** | F1, F2, F5 | Recovery of observed timing variation profile, measurement of TTV-TDV phase shift, and calculation of exomoon posterior probability. |
| 5 | **WASP-39b JWST NIRSpec Atmospheric Retrieval** | F7, F8, F9 | Rapid inversion runtime $< 0.1\text{ s}$; reproduced posterior medians for $\log_{10}(X_{\text{CO}_2})$ and $\log_{10}(X_{\text{H}_2\text{O}})$ within $1\sigma$ credible intervals of literature reference values. |
| 6 | **WASP-96b JWST NIRISS Transmission Inversion** | F7, F8, F9 | Recovery of $\text{H}_2\text{O}$ absorption signature; inferred equilibrium temperature and cloud top pressure within $1\sigma$ credible interval. |

---

## Test Execution Semantic & Command
- Standalone runner: `python run_tests.py`
- Pytest invocation: `pytest tests/ -v --tb=short`
- Expected: All tests pass with exit code 0.
