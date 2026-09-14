# DISPATCH: Explorer 3 (Conftest Fixtures, Tier 1/2 Test Auditing & Full Suite Verification)

## Identity
- Role: Read-only exploration agent
- Working directory: G:\frontier_astronomy_ai\.agents\explorer_remediation_3
- Parent Conversation ID: 00bca269-8c56-4843-bbbb-7f564f3d6fc3

## Authoritative Inputs
Subagents MUST read these files before starting work:
- Authoritative User Request: G:\frontier_astronomy_ai\ORIGINAL_REQUEST.md
- Victory Audit Report: G:\frontier_astronomy_ai\.agents\auditor_victory_1\VICTORY_AUDIT_REPORT.md
- Victory Audit Handoff: G:\frontier_astronomy_ai\.agents\auditor_victory_1\handoff.md
- Master Project Spec: G:\frontier_astronomy_ai\PROJECT.md

## Objective
Investigate `tests/conftest.py`, `tests/test_tier1_features.py`, and `tests/test_tier2_boundaries.py` regarding Finding 4 and general test authenticity:
1. `tests/conftest.py`:
   - Inspect `sample_inversion_result` fixture (lines 541–568): Currently pre-cooks static result object with hardcoded literature numbers and fake 0.042s inference time.
   - Detail how this fixture (and any dependent fixtures) must be refactored to dynamically execute the genuine `invert_spectrum` engine on a synthetic or cached benchmark spectrum, or produce authentic execution outputs.
2. `tests/test_tier1_features.py`:
   - Inspect tests that consume `sample_inversion_result`: `test_f8_02`, `test_f8_03`, `test_f8_04`, `test_f9_01`, `test_f9_02`, `test_f9_03`.
   - Inspect tautological assertions:
     - `test_f6_01_sensitivity_limit_snr_threshold` (lines 560–565): `snr_det = 3.2; snr_nondet = 2.4; assert snr_det >= 3.0`
     - `test_f6_02_sensitivity_scaling_with_transit_epochs` (lines 566–572): `snr_16 = 4.0; snr_64 = snr_16 * np.sqrt(...)`
     - `test_f6_03_resonance_false_positive_discrimination` (lines 573–581): `phase_diff_mmr = 0.0; phase_diff_moon = 90.0; assert not (...)`
     - `test_f9_04_wasp96b_h2o_absorption_retrieval` (lines 736–742): `h2o_retrieved = -3.45; ref_h2o = -3.50; assert abs(...)`
     - `test_f9_05_wasp96b_cloud_top_and_temperature` (lines 743–750): `pc_retrieved = -1.6; ref_pc = -1.5; assert abs(...)`
   - Formulate replacement implementations for every single tautological test so that they call real functions in `frontier_astronomy.perturbations` and `frontier_astronomy.atmospheric`.
3. `tests/test_tier2_boundaries.py`:
   - Scan for any similar arithmetic tautologies (e.g. `snr_exact = 3.0; assert snr_exact >= 3.0` and `delta_bic = 0.0; assert delta_bic < 10.0` mentioned in audit report).
   - Detail how to ensure boundary tests genuinely exercise the boundary behavior of production functions.
4. Verify overall test suite count and structure (`run_tests.py`) to ensure 127+ tests remain comprehensive and authentic.

## Scope Boundaries
- Read-only analysis. Do NOT modify any implementation code or tests.
- Provide a rigorous, step-by-step implementation plan for the Worker.

## Deliverables
- Write your detailed technical findings and recommendations to `G:\frontier_astronomy_ai\.agents\explorer_remediation_3\report.md`.
- Send a completion message via `send_message` to parent conversation ID `00bca269-8c56-4843-bbbb-7f564f3d6fc3`.
