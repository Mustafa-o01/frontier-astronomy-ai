# DISPATCH: Challenger 1 (Atmospheric Inversion Adversarial Challenger)

## Identity
- Role: Code-Executing Adversarial Challenger
- Working directory: G:\frontier_astronomy_ai\.agents\challenger_remediation_1
- Parent Conversation ID: 00bca269-8c56-4843-bbbb-7f564f3d6fc3

## CRITICAL OPERATIONAL CONSTRAINT
- DO NOT USE `run_command`! In this environment, shell commands trigger interactive permission prompts.
- Use `view_file`, `write_to_file`, `grep_search`, `find_by_name`, `list_dir`. Write all report files directly using `write_to_file`.

## Authoritative Inputs
Subagents MUST read these files before starting work:
- Authoritative User Request: G:\frontier_astronomy_ai\ORIGINAL_REQUEST.md
- Victory Audit Rejection Report: G:\frontier_astronomy_ai\.agents\auditor_victory_1\VICTORY_AUDIT_REPORT.md
- Victory Audit Rejection Handoff: G:\frontier_astronomy_ai\.agents\auditor_victory_1\handoff.md
- Master Project Spec: G:\frontier_astronomy_ai\PROJECT.md
- Worker Remediation Handoff: G:\frontier_astronomy_ai\.agents\worker_remediation_1\handoff.md

## Objective
Adversarially challenge the remediated atmospheric inversion engine:
1. Challenge against Target-Sniffing Shortcuts:
   - Verify that renaming the target or passing synthetic exoplanets (e.g. `target_id="UNSEEN-999b"`) does not cause the model to crash, fail, or default to WASP-39b values.
   - Verify that altering spectral features (e.g., removing the 4.3 um CO2 absorption peak, injecting extreme water absorption at 1.4/1.9 um, or varying continuum depth) genuinely shifts posterior sample modes rather than returning hardcoded literature constants.
2. Challenge Normalizing Flow Architecture:
   - Verify that `RealNVPConditionalFlow` does not contain hidden hardcoded modes, delta-CO2 conditional branches, or 10% perturbations.
   - Check sample shape, quantile consistency, and physical bounds clamping.
3. Issue a clear verdict: `CONFIRM_CORRECTNESS` or `REJECT`.

## Deliverables
- Write your adversarial challenge report to `G:\frontier_astronomy_ai\.agents\challenger_remediation_1\handoff.md`.
- Send a completion message via `send_message` to parent conversation ID `00bca269-8c56-4843-bbbb-7f564f3d6fc3` stating your verdict (`CONFIRM_CORRECTNESS` or `REJECT`).
