# DISPATCH: Explorer 3 (Iteration 2 — Tier 2 Boundary Tests Remediation)

## Identity
- Role: Read-only exploration agent
- Working directory: G:\frontier_astronomy_ai\.agents\explorer_remediation_iter2_3
- Parent Conversation ID: 00bca269-8c56-4843-bbbb-7f564f3d6fc3

## CRITICAL OPERATIONAL CONSTRAINT
- DO NOT USE `run_command`! In this environment, shell commands cause interactive blocking.
- Use `view_file`, `write_to_file`, `grep_search`, `find_by_name`, `list_dir`. Write all markdown files directly using `write_to_file`.

## Authoritative Inputs
Subagents MUST read these files before starting work:
- Authoritative User Request: G:\frontier_astronomy_ai\ORIGINAL_REQUEST.md
- Gate Status: G:\frontier_astronomy_ai\.agents\orchestrator_2\GATE_STATUS.md
- Challenger 2 Handoff: G:\frontier_astronomy_ai\.agents\challenger_remediation_2\handoff.md
- Test File: `tests/test_tier2_boundaries.py`

## Objective
Analyze Challenger 2's rejection findings in `tests/test_tier2_boundaries.py`:
1. `test_f4_b02`: Replace generator check with `run_injection_recovery_trial` under extreme noise.
2. `test_f4_b05`: Replace `len([0.01]) == 1` with `run_injection_recovery_trial` on single-depth input.
3. `test_f5_b04`: Replace local array length assert with `detect_perturbations` on irregularly sampled cadences.
4. `test_f6_b04`: Replace local math formula `assert chord > 0.0` with `compute_minimum_detectable_moon_mass` under high impact parameter.
5. `test_f9_b01`: Replace local list sorting assert with `AtmosphericForwardModel` / `invert_spectrum` on unsorted wavelengths.
6. `test_f9_b03`: Replace local `np.median` assert with `invert_spectrum` on a zero-signal flat spectrum to verify wide posterior widths.
7. `test_f10_b01`, `test_f10_b02`, `test_f10_b05`: Replace local array slicing and string assertions with calls to dashboard/ingestion components.
Formulate exact verbatim replacement code for the Worker.

## Deliverables
- Write your analysis and exact worker code instructions to `G:\frontier_astronomy_ai\.agents\explorer_remediation_iter2_3\report.md`.
- Send a completion message via `send_message` to parent conversation ID `00bca269-8c56-4843-bbbb-7f564f3d6fc3`.
