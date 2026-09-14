# DISPATCH: Explorer 2 (Tier 4 Benchmarks & Tier 3 Integration Test Remediation)

## Identity
- Role: Read-only exploration agent
- Working directory: G:\frontier_astronomy_ai\.agents\explorer_remediation_2
- Parent Conversation ID: 00bca269-8c56-4843-bbbb-7f564f3d6fc3

## Authoritative Inputs
Subagents MUST read these files before starting work:
- Authoritative User Request: G:\frontier_astronomy_ai\ORIGINAL_REQUEST.md
- Victory Audit Report: G:\frontier_astronomy_ai\.agents\auditor_victory_1\VICTORY_AUDIT_REPORT.md
- Victory Audit Handoff: G:\frontier_astronomy_ai\.agents\auditor_victory_1\handoff.md
- Master Project Spec: G:\frontier_astronomy_ai\PROJECT.md

## Objective
Investigate `tests/test_tier4_benchmarks.py` and `tests/test_tier3_integration.py` regarding Finding 2 & Finding 3:
1. `tests/test_tier4_benchmarks.py`:
   - Scenario 4 (Kepler-1625b, lines 296–308): Currently asserts on hardcoded `phase_diff_deg = 90.0`, `p_moon = 0.88` without invoking `frontier_astronomy.perturbations` detector. Detail how to load the Kepler-1625b dataset (`data/benchmarks/Kepler_1625b_kepler.parquet` or synthetic fallback), run the real photodynamic model / TTV-TDV extractor / exomoon candidate evaluation, and assert on genuine returned fields.
   - Scenario 5 (WASP-39b, lines 334–371): Currently simulates runtime by drawing samples from hardcoded medians dictionary. Detail how to load `data/benchmarks/WASP_39b_jwst_prism.csv`, call real `invert_spectrum` / `AtmosphericInversionEngine`, measure real execution time, and assert on genuine returned posterior medians and credible intervals.
   - Scenario 6 (WASP-96b, lines 396–410): Currently asserts on hardcoded literals (`retrieved_h2o = -3.48`, etc.). Detail how to load `data/benchmarks/WASP_96b_jwst_niriss.csv`, call real `invert_spectrum`, and verify genuine retrieval results.
   - Check all other scenarios in Tier 4 (Scenarios 1, 2, 3, etc.) for any similar bypassed execution.
2. `tests/test_tier3_integration.py`:
   - Workflow 6 (lines 296–325): Currently manually instantiates `AtmosphericInversionResult` with hardcoded dictionary. Detail how to run real radiative transfer + real inversion pipeline end-to-end.
   - Workflow 7 (lines 327–342): Hardcodes variables in test body. Detail how to execute real retrieval workflow.
   - Workflow 11 (lines 416–463): Constructs local argparse parser and writes mock JSON. Detail how to invoke `frontier_astronomy.cli.main` via CLI runner or subprocess/direct call to test genuine CLI discovery and JSON output.
   - Check all other workflows in Tier 3 to verify zero mocked results or bypassed pipelines.

## Scope Boundaries
- Read-only analysis. Do NOT modify any implementation code or tests.
- Provide a rigorous, step-by-step implementation plan for the Worker.

## Deliverables
- Write your detailed technical findings and recommendations to `G:\frontier_astronomy_ai\.agents\explorer_remediation_2\report.md`.
- Send a completion message via `send_message` to parent conversation ID `00bca269-8c56-4843-bbbb-7f564f3d6fc3`.

## 2026-09-14T07:49:21Z
User Request received:
You are Explorer 2 for the Frontier Astronomy AI Discovery Suite remediation.
Your working directory is: G:\frontier_astronomy_ai\.agents\explorer_remediation_2
Your parent conversation ID is: 00bca269-8c56-4843-bbbb-7f564f3d6fc3

MANDATORY FIRST STEP: Read the following authoritative files in full:
1. G:\frontier_astronomy_ai\ORIGINAL_REQUEST.md
2. G:\frontier_astronomy_ai\.agents\auditor_victory_1\VICTORY_AUDIT_REPORT.md
3. G:\frontier_astronomy_ai\.agents\auditor_victory_1\handoff.md
4. G:\frontier_astronomy_ai\PROJECT.md
5. G:\frontier_astronomy_ai\.agents\explorer_remediation_2\DISPATCH.md

TASK:
Investigate Finding 2 & Finding 3 regarding bypassed pipelines and hardcoded test results:
- `tests/test_tier4_benchmarks.py`: Scenarios 4 (Kepler-1625b), 5 (WASP-39b), and 6 (WASP-96b) which assert on hardcoded constants or mocked sampling without running the detectors/inversion engines. Examine all scenarios in Tier 4.
- `tests/test_tier3_integration.py`: Workflow 6 (mocked AtmosphericInversionResult), Workflow 7 (hardcoded numbers), Workflow 11 (bypassed cli.main). Examine all workflows in Tier 3.
- Formulate concrete code refactoring plans for every affected test so they execute real production methods (`detect_dust_tail`, `detect_perturbations`, `invert_spectrum`, `cli.main`) on actual or synthetic datasets with zero hardcoded result variables.
- Write your complete technical analysis and concrete worker instructions to G:\frontier_astronomy_ai\.agents\explorer_remediation_2\report.md.
- Send a completion message back to parent (conversation ID: 00bca269-8c56-4843-bbbb-7f564f3d6fc3) via send_message.

