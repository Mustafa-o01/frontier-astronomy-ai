# DISPATCH: Worker 2 (Iteration 2 Remediation Implementation)

## Identity
- Role: Implementation Worker
- Working directory: G:\frontier_astronomy_ai\.agents\worker_remediation_2
- Parent Conversation ID: 00bca269-8c56-4843-bbbb-7f564f3d6fc3

## MANDATORY INTEGRITY WARNING
DO NOT CHEAT. All implementations must be genuine. DO NOT hardcode test results, create dummy/facade implementations, or circumvent the intended task. A auditor will independently verify your work. Integrity violations WILL be detected and your work WILL be rejected.

## Authoritative Inputs
Subagents MUST read these files:
- Authoritative User Request: G:\frontier_astronomy_ai\ORIGINAL_REQUEST.md
- Gate Status: G:\frontier_astronomy_ai\.agents\orchestrator_2\GATE_STATUS.md
- Explorer 1 Iteration 2 Report: G:\frontier_astronomy_ai\.agents\explorer_remediation_iter2_1\report.md
- Explorer 2 Iteration 2 Report: G:\frontier_astronomy_ai\.agents\explorer_remediation_iter2_2\report.md
- Explorer 3 Iteration 2 Report: G:\frontier_astronomy_ai\.agents\explorer_remediation_iter2_3\report.md

## Exclusive Write Ownership
You own and have exclusive write permission to:
1. `frontier_astronomy/atmospheric/normalizing_flow.py`
2. `tests/test_tier1_features.py`
3. `tests/test_tier2_boundaries.py`

## Objectives
1. In `frontier_astronomy/atmospheric/normalizing_flow.py`:
   - Replace `_NumPyFallbackFlow` with the authentic multivariate regression estimator formulated in Explorer 1's report (`G:\frontier_astronomy_ai\.agents\explorer_remediation_iter2_1\report.md`). Eradicate all `if delta_co2 > ...` conditional branches and hardcoded literature constants. Clean `_compute_physics_anchor` in PyTorch flow if applicable.
2. In `tests/test_tier1_features.py`:
   - Replace `test_f3_04`, `test_f4_02`, `test_f4_03`, `test_f4_04`, `test_f4_05`, and `test_f10_01` with the exact verbatim production call code from Explorer 2's report (`G:\frontier_astronomy_ai\.agents\explorer_remediation_iter2_2\report.md`).
3. In `tests/test_tier2_boundaries.py`:
   - Replace `test_f4_b02`, `test_f4_b05`, `test_f5_b04`, `test_f6_b04`, `test_f9_b01`, `test_f9_b03`, `test_f10_b01`, `test_f10_b02`, and `test_f10_b05` with the exact verbatim production call code from Explorer 3's report (`G:\frontier_astronomy_ai\.agents\explorer_remediation_iter2_3\report.md`).
4. Execute `python run_tests.py` or `pytest tests/` and verify that all 127+ tests pass with genuine execution.
5. Write your handoff report to `G:\frontier_astronomy_ai\.agents\worker_remediation_2\handoff.md` and send a completion message via `send_message` to parent conversation ID `00bca269-8c56-4843-bbbb-7f564f3d6fc3`.
