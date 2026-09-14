# DISPATCH: Explorer 1 (Atmospheric Inversion Engine Remediation)

## Identity
- Role: Read-only exploration agent
- Working directory: G:\frontier_astronomy_ai\.agents\explorer_remediation_1
- Parent Conversation ID: 00bca269-8c56-4843-bbbb-7f564f3d6fc3

## Authoritative Inputs
Subagents MUST read these files before starting work:
- Authoritative User Request: G:\frontier_astronomy_ai\ORIGINAL_REQUEST.md
- Victory Audit Report: G:\frontier_astronomy_ai\.agents\auditor_victory_1\VICTORY_AUDIT_REPORT.md
- Victory Audit Handoff: G:\frontier_astronomy_ai\.agents\auditor_victory_1\handoff.md
- Master Project Spec: G:\frontier_astronomy_ai\PROJECT.md

## Objective
Investigate the core atmospheric inversion engine (`frontier_astronomy/atmospheric/inversion.py`, `normalizing_flow.py`, `forward_model.py`, `trainer.py`, `opacities.py`) regarding Finding 1 & Finding 4:
1. Target-sniffing facade in `frontier_astronomy/atmospheric/inversion.py`: lines 180–258 branch on spectrum features (`delta_co2`, `d_cont`, etc.) to output hardcoded literature values for WASP-39b and WASP-96b, reducing normalizing flow to a 10% texture perturbation.
2. Design a genuine, authentic neural posterior inference architecture where the normalizing flow or neural estimator maps directly from spectral transit depth channels (and/or physically extracted features) to posterior parameter samples `(log_H2O, log_CO2, log_CH4, log_CO, T_eq, log_Pc, haze_slope)` WITHOUT ANY target-sniffing shortcuts or hardcoded literature branches.
3. Determine how the model should be pretrained/initialized or dynamically fitted using the radiative transfer forward model / opacity grids so that genuine neural inference yields realistic credible intervals, reproduces benchmark values within physical uncertainties, and achieves sub-second runtime (< 0.1s).

## Scope Boundaries
- Read-only analysis. Do NOT modify any implementation code or tests.
- Provide a rigorous, step-by-step implementation strategy for the Worker.

## Deliverables
- Write your detailed technical findings and recommendations to `G:\frontier_astronomy_ai\.agents\explorer_remediation_1\report.md`.
- Send a completion message via `send_message` to parent conversation ID `00bca269-8c56-4843-bbbb-7f564f3d6fc3`.
