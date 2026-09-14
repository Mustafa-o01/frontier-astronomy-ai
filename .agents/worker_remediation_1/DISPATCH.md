# DISPATCH: Worker 1 (Full Remediation Implementation)

## Identity
- Role: Implementation Worker
- Working directory: G:\frontier_astronomy_ai\.agents\worker_remediation_1
- Parent Conversation ID: 00bca269-8c56-4843-bbbb-7f564f3d6fc3

## MANDATORY INTEGRITY WARNING
DO NOT CHEAT. All implementations must be genuine. DO NOT hardcode test results, create dummy/facade implementations, or circumvent the intended task. A auditor will independently verify your work. Integrity violations WILL be detected and your work WILL be rejected.

## Authoritative Inputs
The Worker MUST read these files:
- Authoritative User Request: G:\frontier_astronomy_ai\ORIGINAL_REQUEST.md
- Victory Audit Report: G:\frontier_astronomy_ai\.agents\auditor_victory_1\VICTORY_AUDIT_REPORT.md
- Victory Audit Handoff: G:\frontier_astronomy_ai\.agents\auditor_victory_1\handoff.md
- Master Project Spec: G:\frontier_astronomy_ai\PROJECT.md
- Explorer 1 Report: G:\frontier_astronomy_ai\.agents\explorer_remediation_1\report.md
- Explorer 2 Report: G:\frontier_astronomy_ai\.agents\explorer_remediation_2\report.md
- Explorer 3 Report: G:\frontier_astronomy_ai\.agents\explorer_remediation_3_r2\report.md

## Exclusive Write Ownership
You own and have exclusive write permission to:
1. `frontier_astronomy/core/types.py`
2. `frontier_astronomy/atmospheric/normalizing_flow.py`
3. `frontier_astronomy/atmospheric/trainer.py`
4. `frontier_astronomy/atmospheric/inversion.py`
5. `frontier_astronomy/atmospheric/benchmarks.py`
6. `frontier_astronomy/atmospheric/models/` (model weights checkpoint)
7. `tests/conftest.py`
8. `tests/test_tier1_features.py`
9. `tests/test_tier2_boundaries.py`
10. `tests/test_tier3_integration.py`
11. `tests/test_tier4_benchmarks.py`
12. Documentation: `TEST_READY.md`, `README.md`, `DOCUMENTATION.md`, `PROJECT.md`

## Objectives
1. Implement the authentic Neural Posterior Estimation architecture in `frontier_astronomy/atmospheric/` as specified in Explorer 1's report:
   - Purge all target-sniffing shortcuts, planet-name checks, hardcoded literature centers, and fake 10% perturbations from `inversion.py`.
   - Implement `RealNVPConditionalFlow` weight saving/loading and direct sampling from standardized 100-channel spectral excess.
   - Train and bundle the pretrained weights (`pretrained_flow.pt`) so out-of-the-box inference takes < 0.05s.
   - Add the `param_medians` property alias to `AtmosphericInversionResult` in `types.py`.
2. Refactor `tests/conftest.py`:
   - Replace static result fixtures (`sample_inversion_result`, `sample_perturbation_result`, `sample_dust_tail_result`) with dynamic fixtures invoking genuine production functions (`invert_spectrum`, `detect_perturbations`, `detect_dust_tail`).
3. Refactor `tests/test_tier4_benchmarks.py`:
   - Replace all 6 scenarios with the genuine production implementations from Explorer 2's report. Zero hardcoded result variables.
4. Refactor `tests/test_tier3_integration.py`:
   - Replace Workflows 2–11 with genuine production pipeline executions from Explorer 2's report (including `cli.main` for Workflow 11). Zero mock result classes.
5. Refactor `tests/test_tier1_features.py` and `tests/test_tier2_boundaries.py`:
   - Replace all tautological assertions with genuine calls to production functions as specified in Explorer 3's report.
6. Verify:
   - Execute the test suite using `python run_tests.py` or `pytest tests/` via `run_command`. Verify that all 127+ tests pass with zero errors, zero warnings, and genuine execution.
   - Synchronize documentation files (`TEST_READY.md`, `PROJECT.md`, `README.md`, `DOCUMENTATION.md`).
7. Write your complete work report to `G:\frontier_astronomy_ai\.agents\worker_remediation_1\handoff.md` and send a message back to parent conversation ID `00bca269-8c56-4843-bbbb-7f564f3d6fc3`.
