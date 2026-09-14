# Reproducibility

This paper is reproducible from the local repository at `G:\frontier_astronomy_ai` and the cached Kepler products under `data/cache/real_kepler/`. The directory is a local working copy, not a public code archive.

## Environment

The verified rerun used Python 3.14.6 on Windows 11 with NumPy 2.5.2, SciPy 1.18.1, Matplotlib 3.11.1, and Astropy 8.0.1. The recorded environment is in `analysis/environment.json`.

## Commands

From the repository root:

```powershell
python paper\analysis\reproduce.py > paper\logs\reproduce.txt
python paper\analysis\robustness.py > paper\logs\robustness.txt
python paper\analysis\supplement.py
python paper\analysis\verify_sources.py > paper\logs\sources.txt
python -m pytest -q --junitxml=paper\logs\tests.xml
```

`reproduce.py` regenerates the machine-readable reproduction output and the primary figures. `robustness.py` runs the preprocessing and model-sensitivity checks. `supplement.py` writes the tabular appendices. `verify_sources.py` checks the cached FITS manifest and source metadata. The project test suite currently contains 201 tests; test success establishes software consistency for covered cases, not astrophysical validity.

## Important provenance

The numerical inputs and outputs used in the manuscript are retained in `paper/analysis/results.json`, `paper/analysis/robustness.json`, and `paper/tables/`. FITS filenames, quarters, row counts, and SHA-256 digests are in `paper/tables/fits_manifest.csv`. Catalog and MAST query material is in `paper/sources/`. Figures are generated in `paper/figures/` from the cached observations and saved analysis tables.

The original campaign output remains in `results/real_nasa_discoveries.json`; it is preserved for comparison and is not treated as independent evidence. The analysis scripts explicitly document the preprocessing variants and local transit fits used to test the campaign claims.
