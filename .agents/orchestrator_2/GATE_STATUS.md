## Gate — Iteration 1
| Agent | Role | Verdict | Source |
|-------|------|---------|--------|
| worker_remediation_1 | teamwork_preview_worker | DONE (pass full remediation) | handoff.md |
| reviewer_remediation_1 | teamwork_preview_reviewer | APPROVE | handoff.md |
| reviewer_remediation_2 | teamwork_preview_reviewer | APPROVE | handoff.md |
| challenger_remediation_1 | teamwork_preview_challenger | REJECT (NumPy fallback facade in normalizing_flow.py) | handoff.md |
| challenger_remediation_2 | teamwork_preview_challenger | REJECT (15 lingering tautologies/bypassed functions in Tier 1 and Tier 2) | handoff.md |
| auditor_remediation_1 | teamwork_preview_auditor | CLEAN | handoff.md |

Gate Result: **FAIL** (challenger_remediation_1 & challenger_remediation_2 REJECT)

### Specific Issues Requiring Remediation:
1. **NumPy Fallback Facade in `frontier_astronomy/atmospheric/normalizing_flow.py`** (from Challenger 1):
   - Lines 348–391 of `_NumPyFallbackFlow` contain explicit delta-CO2 conditional branch (`if delta_co2 > 0.2:`) and hardcoded literature reference modes (`co2_mode = np.clip(-3.70 + ...)`, `h2o_mode = np.clip(-3.30 + ...)`, `co_mode = -3.5`, `t_eq_mode = 1150.0`, `pc_mode = -1.8`).
   - Remediation: Replace the heuristic mode formulas with an authentic linear projection / matrix inversion estimator or linear weights trained on synthetic spectra that map standardized 100-channel spectral excess directly to the 7 parameters without any conditional branches or literature constants.
2. **Lingering Tautologies and Bypassed Tests in `tests/test_tier1_features.py`** (from Challenger 2):
   - `test_f3_04`: Replace local random normal array and `# placeholder` with a call to `compute_multi_epoch_depth_variability`.
   - `test_f4_02`: Replace `if np.min(lc.flux) < (1.0 - 4.0 * 0.001)` with a call to `run_injection_recovery_trial` or `detect_dust_tail`.
   - `test_f4_03`: Replace algebraically impossible `delta_bic = bic_flat - (bic_flat + 8*ln(N))` with a call to `evaluate_false_positive_rate`.
   - `test_f4_04`: Replace `1.0 - np.min(lc.flux)` with `res = detect_dust_tail(lc, ...); assert np.isclose(res.peak_depth, true_depth, rtol=0.25)`.
   - `test_f4_05`: Replace generator array check with `run_injection_recovery_trial` across the depth grid.
   - `test_f10_01`: Connect to `frontier_astronomy.dashboard` filtering logic or catalog loader rather than filtering a hardcoded local list.
3. **Lingering Tautologies in `tests/test_tier2_boundaries.py`** (from Challenger 2):
   - `test_f4_b02`: Call `run_injection_recovery_trial` with extreme noise.
   - `test_f4_b05`: Call `run_injection_recovery_trial` with single-element depth array.
   - `test_f5_b04`: Call `detect_perturbations` on irregularly sampled cadences.
   - `test_f6_b04`: Call `compute_minimum_detectable_moon_mass` with near-grazing impact parameter rather than asserting `chord > 0.0`.
   - `test_f9_b01`: Pass unsorted wavelength array to `AtmosphericForwardModel` or `invert_spectrum` to verify sorting handling.
   - `test_f9_b03`: Pass flat spectrum to `invert_spectrum` to verify broad unconstrained posterior widths.
   - `test_f10_b01`, `test_f10_b02`, `test_f10_b05`: Call genuine dashboard/ingestion components.
