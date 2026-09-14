## 2026-09-13T22:17:51Z

You are explorer_survey_2, the Data Archives Explorer for the Frontier Astronomy AI Discovery Suite project.
Your working directory: G:\frontier_astronomy_ai\.agents\explorer_survey_2
Project root: G:\frontier_astronomy_ai
Original user request: G:\frontier_astronomy_ai\ORIGINAL_REQUEST.md

You MUST read G:\frontier_astronomy_ai\ORIGINAL_REQUEST.md first.

Your objective:
Investigate the data ingestion sources, NASA public archives, APIs, benchmark systems, and astronomical data processing tools:
1. NASA Kepler, K2, and TESS Archive Data:
   - Light curve data structures: Target Pixel Files (TPF), LightCurve files (LC), Simple Aperture Photometry (SAP_FLUX), Pre-search Data Conditioning (PDCSAP_FLUX), quality flags, time systems (BJD-2454833, BTJD).
   - Ingestion pipelines using lightkurve, astroquery.mast, or direct NASA MAST API queries.
   - Real benchmark target systems:
     * Disintegrating rocky bodies: KIC 12557548 (Kepler-1520b), K2-22b (EPIC 201637175), KOI-2700b (Kepler), WD 1145+017.
     * Exomoon & multi-body perturbation benchmarks: Kepler-1625b (Teachey & Kipping candidate), Kepler-1708b, Kepler-9 / Kepler-89 (known multi-planet TTV benchmarks).
   - Preprocessing, detrending, and normalization strategies: outlier removal, stellar flare filtering, Savitzky-Golay / spline detrending, phase-folding, binning.
2. NASA JWST Transmission Spectroscopy Data:
   - Observation modes: NIRSpec PRISM, NIRSpec G395H, NIRISS SOSS, MIRI LRS transmission spectra.
   - Public JWST Early Release Science (ERS) / GTO transmission spectra (e.g., WASP-39b NIRSpec PRISM spectrum with prominent CO2 at 4.3 um, H2O at 1.4/1.8/2.7 um; WASP-96b NIRISS spectrum).
   - Ingestion format: wavelength (um), transit depth (Rp/R*)^2 or transit depth in ppm / percent, photometric error/uncertainties.
   - Benchmark synthetic and real spectra archives (MAST, Zenodo, literature tables).
3. Robust Hermetic / Fallback Data Architecture:
   - Seamless hybrid ingestion: live fetch from NASA MAST when connected, accompanied by high-fidelity local bundled benchmark data & deterministic synthetic generators for reliable, offline-capable verification.
   - Storage and caching strategy (e.g., FITS, Parquet, CSV, NumPy npz/HDF5) under G:\frontier_astronomy_ai\data/.

Deliverables:
Write your comprehensive analysis and data ingestion design to:
- G:\frontier_astronomy_ai\.agents\explorer_survey_2\analysis.md
- G:\frontier_astronomy_ai\.agents\explorer_survey_2\handoff.md
And send a completion message back to the orchestrator.
