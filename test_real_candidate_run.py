"""Test multi-quarter fetch and detection on real Kepler candidate KIC 7582691."""
import re
import requests
from pathlib import Path
import numpy as np

from frontier_astronomy.ingestion.fits_reader import read_fits_light_curve
from frontier_astronomy.core.preprocessing import preprocess_light_curve
from frontier_astronomy.core.types import LightCurveData
from frontier_astronomy.dust_tail.detector import detect_dust_tail
from frontier_astronomy.perturbations import detect_perturbations

def fetch_real_kepler_candidate_data(kepid: int, max_quarters: int = 3) -> LightCurveData:
    kic_str = f"{kepid:09d}"
    prefix = kic_str[:4]
    base_url = f"https://archive.stsci.edu/missions/kepler/lightcurves/{prefix}/{kic_str}/"
    
    r = requests.get(base_url, timeout=15)
    r.raise_for_status()
    fits_files = re.findall(r'href="(kplr[0-9\-]+_llc\.fits)"', r.text)
    
    cache_dir = Path("data/cache/real_kepler")
    cache_dir.mkdir(parents=True, exist_ok=True)
    
    selected_files = fits_files[:max_quarters]
    times = []
    fluxes = []
    flux_errs = []
    qualities = []
    ra = 0.0
    dec = 0.0
    meta = {}
    
    for fname in selected_files:
        fpath = cache_dir / fname
        if not fpath.exists():
            print(f"Downloading {fname}...")
            resp = requests.get(base_url + fname, timeout=30)
            resp.raise_for_status()
            with open(fpath, "wb") as f:
                f.write(resp.content)
        lc = read_fits_light_curve(fpath, target_id=f"KIC {kepid}")
        times.append(lc.time)
        fluxes.append(lc.flux)
        flux_errs.append(lc.flux_err)
        qualities.append(lc.quality)
        ra = lc.ra
        dec = lc.dec
        meta.update(lc.metadata)
        
    all_time = np.concatenate(times)
    all_flux = np.concatenate(fluxes)
    all_err = np.concatenate(flux_errs)
    all_qual = np.concatenate(qualities)
    
    order = np.argsort(all_time)
    
    return LightCurveData(
        time=all_time[order],
        flux=all_flux[order],
        flux_err=all_err[order],
        quality=all_qual[order],
        ra=ra,
        dec=dec,
        target_id=f"KIC {kepid}",
        mission="Kepler",
        metadata=meta,
    )

if __name__ == "__main__":
    lc = fetch_real_kepler_candidate_data(7582691, max_quarters=2)
    print(f"Combined light curve: {len(lc.time)} cadences over {lc.time[-1] - lc.time[0]:.1f} days")
    
    lc_clean = preprocess_light_curve(lc, strict_quality=True, clip_outliers=True, detrend=True)
    print(f"Preprocessed: {len(lc_clean.time)} cadences")
    
    # Candidate parameters from NASA table: period = 0.259819659 d, t0 = 131.85061
    period = 0.259819659
    t0 = 131.85061
    
    print("\nRunning Dust Tail Detector...")
    dust_res = detect_dust_tail(lc_clean, period=period, t0=t0)
    print(f"Delta-BIC: {dust_res.delta_bic:+.2f}")
    print(f"Asymmetry alpha: {dust_res.asymmetry_parameter:.4f}")
    print(f"Is Dust Tail: {dust_res.is_asymmetric_dust_tail}")
    print(f"LRT p-value: {dust_res.lrt_p_value:.2e}")
    
    print("\nRunning Exomoon & Trojan Perturbation Detector...")
    pert_res = detect_perturbations(lc_clean, period=period, t0=t0)
    print(f"TTV SNR: {pert_res.ttv_snr:.2f}")
    print(f"P(Moon): {pert_res.p_moon_posterior*100:.1f}%")
    print(f"Is Exomoon: {pert_res.has_exomoon_candidate}")
