"""Test downloading and parsing a real Kepler candidate light curve."""
import os
import re
import requests
from pathlib import Path
from frontier_astronomy.ingestion.fits_reader import read_fits_light_curve
from frontier_astronomy.core.preprocessing import preprocess_light_curve

def test_fetch_candidate(kepid: int):
    kic_str = f"{kepid:09d}"
    prefix = kic_str[:4]
    base_url = f"https://archive.stsci.edu/missions/kepler/lightcurves/{prefix}/{kic_str}/"
    print(f"Connecting to: {base_url}")
    
    r = requests.get(base_url, timeout=15)
    r.raise_for_status()
    
    fits_files = re.findall(r'href="(kplr[0-9\-]+_llc\.fits)"', r.text)
    print(f"Found {len(fits_files)} long-cadence FITS files for KIC {kepid}")
    if not fits_files:
        return None
        
    cache_dir = Path("data/cache/real_kepler")
    cache_dir.mkdir(parents=True, exist_ok=True)
    
    first_file = fits_files[0]
    file_url = base_url + first_file
    dest_path = cache_dir / first_file
    
    if not dest_path.exists():
        print(f"Downloading {first_file} ({file_url})...")
        resp = requests.get(file_url, timeout=30)
        resp.raise_for_status()
        with open(dest_path, "wb") as f:
            f.write(resp.content)
        print(f"Saved {len(resp.content)} bytes to {dest_path}")
    else:
        print(f"Using cached {dest_path}")
        
    lc = read_fits_light_curve(dest_path, target_id=f"KIC {kepid}")
    print(f"Loaded LightCurveData: {len(lc.time)} cadences, time range: [{lc.time[0]:.2f}, {lc.time[-1]:.2f}]")
    
    lc_clean = preprocess_light_curve(lc, strict_quality=True, clip_outliers=True, detrend=True)
    print(f"Cleaned LightCurveData: {len(lc_clean.time)} cadences")
    return lc_clean

if __name__ == "__main__":
    test_fetch_candidate(7582691)
