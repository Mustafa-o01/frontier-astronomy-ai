# Evidence ledger

This ledger maps the manuscript's principal quantitative claims to traceable data, code, and outputs.

| Claim | Status | Data / output | Executable source | Interpretation and limitation |
|---|---|---|---|---|
| KIC 9944201 has 8,431 processed cadences and the campaign reports ΔBIC = 73,042.749 and α = 0.53398 | VERIFIED / REPRODUCIBLE | `results/real_nasa_discoveries.json`; `paper/analysis/results.json` | `paper/analysis/reproduce.py`; `frontier_astronomy/dust_tail/detector.py` | Reproduces the historical pipeline statistic only. |
| KIC 9944201 clipping removes 522 of 753 cadences in the catalog-duration window | TRACEABLE | `paper/tables/clipping_counts.csv` | `paper/analysis/robustness.py` | Demonstrates transit-information loss; the count depends on the stated quality and window definitions. |
| Multistart and unclipped primary fits remove the large asymmetry preference | REPRODUCIBLE | `paper/analysis/results.json`; `paper/tables/primary_shape_comparison.csv` | `paper/analysis/reproduce.py` | Model comparison is within the tested phenomenological families and uses a white-noise error model. |
| A secondary minimum recurs in KIC 9944201 at roughly 4,900–5,200 ppm by quarter | TRACEABLE | `paper/tables/dust_models.csv`; figures in `paper/figures/` | `paper/analysis/supplement.py` and reproduction helpers | Descriptive aperture contrasts, not fitted binary eclipse depths. |
| KIC 8494263 contributes three measurable events | VERIFIED | `paper/tables/epoch_coverage.csv`; `paper/tables/local_8494263_pdc.csv` | `paper/analysis/reproduce.py` | Applies to the cached three-quarter sample. |
| KIC 8494263 campaign TTV score 50.1065 is preprocessing-sensitive; local residuals are sub-minute | REPRODUCIBLE | `paper/analysis/results.json`; timing tables | `paper/analysis/robustness.py`; local-fit code in `reproduce.py` | Score is a scatter-to-error heuristic, not a calibrated detection significance. |
| No traceable 91.4° ± 3.2° satellite phase measurement exists for KIC 8494263 | PARTIALLY TRACEABLE | `paper/analysis/results.json`; `paper/logs/robustness.txt` | `frontier_astronomy/perturbations/tdv_extractor.py` | The saved phase is a zero sentinel for the constant-duration series. |
| KIC 10153011 retains a several-minute local timing deviation | REPRODUCIBLE | `paper/tables/local_10153011_pdc.csv`; `paper/analysis/results.json` | `paper/analysis/reproduce.py` | Formal χ² and p-value are conditional on three events and the local noise model. |
| KIC 8308347 positive-phase feature is single-passage and preprocessing-dependent | TRACEABLE | `paper/analysis/results.json`; `paper/figures/coorbital_8308347.png` | `paper/analysis/robustness.py` | No repetition or trial-corrected false-alarm probability is established. |
| “P(Moon)=99.9%” is a heuristic score | VERIFIED | `frontier_astronomy/perturbations/sensitivity.py`; campaign JSON | `compute_exomoon_posterior` | It is not a Bayesian posterior or probability that a moon exists. |
| 201 tests pass | VERIFIED | `paper/logs/tests.txt`; `paper/logs/tests.xml` | `python -m pytest -q` | Establishes covered software behavior only. |

Claims absent from this ledger are not used as quantitative evidence in the manuscript. All physical interpretations remain hypotheses requiring additional data or model comparison.
