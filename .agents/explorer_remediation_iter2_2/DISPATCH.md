# DISPATCH: Explorer 2 (Iteration 2 — Tier 1 Feature Tests Remediation)

## Identity
- Role: Read-only exploration agent
- Working directory: G:\frontier_astronomy_ai\.agents\explorer_remediation_iter2_2
- Parent Conversation ID: 00bca269-8c56-4843-bbbb-7f564f3d6fc3

## CRITICAL OPERATIONAL CONSTRAINT
- DO NOT USE `run_command`! In this environment, shell commands cause interactive blocking.
- Use `view_file`, `write_to_file`, `grep_search`, `find_by_name`, `list_dir`. Write all markdown files directly using `write_to_file`.

## Authoritative Inputs
Subagents MUST read these files before starting work:
- Authoritative User Request: G:\frontier_astronomy_ai\ORIGINAL_REQUEST.md
- Gate Status: G:\frontier_astronomy_ai\.agents\orchestrator_2\GATE_STATUS.md
- Challenger 2 Handoff: G:\frontier_astronomy_ai\.agents\challenger_remediation_2\handoff.md
- Test File: `tests/test_tier1_features.py`

## Objective
Analyze Challenger 2's rejection findings in `tests/test_tier1_features.py`:
1. `test_f3_04_multi_epoch_depth_variability`: Replace local random normal array and `# placeholder` with a call to `frontier_astronomy.dust_tail.detector.compute_multi_epoch_depth_variability`.
2. `test_f4_02_recovery_rate_at_high_snr`: Replace generator heuristic (`if np.min(lc.flux) < (1.0 - 4.0 * 0.001)`) with `detect_dust_tail` or `run_injection_recovery_trial`.
3. `test_f4_03_false_positive_rate_on_stellar_noise`: Replace algebraically impossible `delta_bic` subtraction with `frontier_astronomy.dust_tail.injection_recovery.evaluate_false_positive_rate`.
4. `test_f4_04_parameter_recovery_fidelity`: Replace `1.0 - np.min(lc.flux)` with `res = detect_dust_tail(...)` and verify `res.peak_depth`.
5. `test_f4_05_injection_grid_dynamic_range`: Replace generator array check with `run_injection_recovery_trial` across the depth grid.
6. `test_f10_01_candidate_discovery_browser_filtering`: Replace filtering of local hardcoded list with `frontier_astronomy.ingestion.catalog` or dashboard filter routines.
Formulate exact verbatim replacement code for the Worker.

## Deliverables
- Write your analysis and exact worker code instructions to `G:\frontier_astronomy_ai\.agents\explorer_remediation_iter2_2\report.md`.
- Send a completion message via `send_message` to parent conversation ID `00bca269-8c56-4843-bbbb-7f564f3d6fc3`.

## 2026-09-14T08:15:08Z
You are Explorer 2 for Iteration 2 of the Frontier Astronomy AI Discovery Suite remediation.
Your working directory is: G:\frontier_astronomy_ai\.agents\explorer_remediation_iter2_2
Your parent conversation ID is: 00bca269-8c56-4843-bbbb-7f564f3d6fc3

CRITICAL CONSTRAINT:
DO NOT USE `run_command`! In this environment, shell commands cause interactive blocking.
Use `view_file`, `write_to_file`, `grep_search`, `find_by_name`, `list_dir`. Write all markdown files directly using `write_to_file`.

MANDATORY FIRST STEP: Read the following authoritative files in full:
1. G:\frontier_astronomy_ai\ORIGINAL_REQUEST.md
2. G:\frontier_astronomy_ai\.agents\orchestrator_2\GATE_STATUS.md
3. G:\frontier_astronomy_ai\.agents\challenger_remediation_2\handoff.md
4. G:\frontier_astronomy_ai\PROJECT.md
5. G:\frontier_astronomy_ai\.agents\explorer_remediation_iter2_2\DISPATCH.md

TASK:
Analyze Challenger 2's rejection findings in `tests/test_tier1_features.py`:
1. `test_f3_04_multi_epoch_depth_variability`: Replace local random normal array and `# placeholder` with a call to `frontier_astronomy.dust_tail.detector.compute_multi_epoch_depth_variability`.
2. `test_f4_02_recovery_rate_at_high_snr`: Replace generator heuristic (`if np.min(lc.flux) < (1.0 - 4.0 * 0.001)`) with `detect_dust_tail` or `run_injection_recovery_trial`.
3. `test_f4_03_false_positive_rate_on_stellar_noise`: Replace algebraically impossible `delta_bic` subtraction with `frontier_astronomy.dust_tail.injection_recovery.evaluate_false_positive_rate`.
4. `test_f4_04_parameter_recovery_fidelity`: Replace `1.0 - np.min(lc.flux)` with `res = detect_dust_tail(...)` and verify `res.peak_depth`.
5. `test_f4_05_injection_grid_dynamic_range`: Replace generator array check with `run_injection_recovery_trial` across the depth grid.
6. `test_f10_01_candidate_discovery_browser_filtering`: Replace filtering of local hardcoded list with `frontier_astronomy.ingestion.catalog` or dashboard filter routines.
- Formulate exact verbatim replacement code for the Worker in `G:\frontier_astronomy_ai\.agents\explorer_remediation_iter2_2\report.md`.
- Send a completion message via `send_message` to parent conversation ID `00bca269-8c56-4843-bbbb-7f564f3d6fc3`.
