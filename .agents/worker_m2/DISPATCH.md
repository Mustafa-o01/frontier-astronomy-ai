## 2026-09-14T01:55:02Z

<USER_REQUEST>
You are worker_m2, the Implementation Worker for Milestone 2: Catastrophic Disintegrating Exoplanet & Dust Tail Hunter (Features F3 & F4).

Working directory: G:\frontier_astronomy_ai\.agents\worker_m2
Project root: G:\frontier_astronomy_ai
Authoritative user request: G:\frontier_astronomy_ai\ORIGINAL_REQUEST.md
System architecture & contracts: G:\frontier_astronomy_ai\PROJECT.md
Survey analyses: G:\frontier_astronomy_ai\.agents\explorer_survey_1\analysis.md
Predecessor handoff & advisory: G:\frontier_astronomy_ai\.agents\worker_m1\handoff.md and G:\frontier_astronomy_ai\.agents\challenger_m1_2\handoff.md

MANDATORY FIRST STEP: Read G:\frontier_astronomy_ai\ORIGINAL_REQUEST.md and G:\frontier_astronomy_ai\PROJECT.md.

MANDATORY INTEGRITY WARNING:
DO NOT CHEAT. All implementations must be genuine. DO NOT hardcode test results, create dummy/facade implementations, or circumvent the intended task. A teamwork_preview_auditor will independently verify your work. Integrity violations WILL be detected and your work WILL be rejected.

Your Exclusive Write Ownership:
- frontier_astronomy/dust_tail/__init__.py
- frontier_astronomy/dust_tail/extinction_model.py (Rappaport/Brogi cometary dust tail forward model: steep sigmoid ingress, exponential egress tail, asymmetry parameter alpha = (t_egress - t_ingress)/t_total > 0.3)
- frontier_astronomy/dust_tail/forward_scattering.py (Henyey-Greenstein / Mie pre-ingress forward-scattering bump)
- frontier_astronomy/dust_tail/sublimation.py (Langmuir grain sublimation dynamics, grain lifetime tau ~ 2-15h)
- frontier_astronomy/dust_tail/detector.py (Multi-epoch variable depth tracking, Delta-BIC >= 10, Likelihood Ratio Test p < 1e-5 vs symmetric transit, returns DustTailDetectionResult matching PROJECT.md)
- frontier_astronomy/dust_tail/injection_recovery.py (Monte Carlo injection-recovery testing across depths 0.1% - 2.0%, evaluating recovery rate >= 90% at SNR >= 5.0, false positive rate <= 2.0%)
- (Optional minor hardenings to frontier_astronomy/core/preprocessing.py: int64 for epoch_split, period finite guards, and transit mask option in preprocess_light_curve so asymmetric_mad_clip does not purge transits).

Verification Requirements:
Run verification commands using python:
1. `python -m pytest tests/test_tier1_features.py -k "TestFeature3 or TestFeature4" -v`
2. `python -m pytest tests/test_tier2_boundaries.py -k "TestFeature3 or TestFeature4" -v`
3. Verify synthetic injection-recovery recovers >= 90% at SNR >= 5.0 and FPR <= 2.0%.
4. Verify KIC 12557548 benchmark light curve detection identifies asymmetric dust tail with Delta-BIC >= 10.
Include verbatim test output in your handoff report.

Deliverables:
- Implement complete genuine code in owned files.
- Write handoff report to G:\frontier_astronomy_ai\.agents\worker_m2\handoff.md.
- Send completion message to orchestrator.
</USER_REQUEST>
