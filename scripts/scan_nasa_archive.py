"""Frontier Astronomy AI - Real NASA Candidate Discovery Pipeline.

Ingests real Kepler observational light curves from the NASA MAST / STScI archive
for unconfirmed KOI candidates, runs catastrophic dust tail detection and photodynamic
exomoon / Trojan perturbation detection, and compiles an automated discovery scorecard.
"""

from __future__ import annotations

import json
import re
import sys
import time
from pathlib import Path
from typing import Any, Dict, List, Optional
import numpy as np
import requests

from frontier_astronomy.core.types import LightCurveData
from frontier_astronomy.core.preprocessing import preprocess_light_curve
from frontier_astronomy.dust_tail.detector import detect_dust_tail
from frontier_astronomy.perturbations import detect_perturbations
from frontier_astronomy.ingestion.fits_reader import read_fits_light_curve

CACHE_DIR = Path("data/cache/real_kepler")
CACHE_DIR.mkdir(parents=True, exist_ok=True)


def fetch_kepler_candidate_light_curve(
    kepid: int,
    max_quarters: int = 3,
    timeout: float = 20.0,
) -> Optional[LightCurveData]:
    """Download and assemble real Kepler long-cadence light curve from STScI archive."""
    kic_str = f"{kepid:09d}"
    prefix = kic_str[:4]
    base_url = f"https://archive.stsci.edu/missions/kepler/lightcurves/{prefix}/{kic_str}/"

    try:
        r = requests.get(base_url, timeout=timeout)
        if r.status_code != 200:
            return None
        fits_files = re.findall(r'href="(kplr[0-9\-]+_llc\.fits)"', r.text)
        if not fits_files:
            return None
    except Exception as err:
        print(f"    [!] Error accessing archive for KIC {kepid}: {err}")
        return None

    selected_files = fits_files[:max_quarters]
    times, fluxes, flux_errs, qualities = [], [], [], []
    ra, dec, meta = 0.0, 0.0, {}

    for fname in selected_files:
        dest_path = CACHE_DIR / fname
        if not dest_path.exists() or dest_path.stat().st_size == 0:
            try:
                resp = requests.get(base_url + fname, timeout=timeout)
                resp.raise_for_status()
                with open(dest_path, "wb") as f:
                    f.write(resp.content)
            except Exception as e:
                print(f"    [!] Failed to download {fname}: {e}")
                continue

        try:
            lc = read_fits_light_curve(dest_path, target_id=f"KIC {kepid}")
            times.append(lc.time)
            fluxes.append(lc.flux)
            flux_errs.append(lc.flux_err)
            qualities.append(lc.quality)
            ra = lc.ra
            dec = lc.dec
            meta.update(lc.metadata)
        except Exception as e:
            print(f"    [!] Failed to parse FITS {fname}: {e}")
            continue

    if not times:
        return None

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


def scan_candidate(candidate_meta: Dict[str, Any], max_quarters: int = 3) -> Optional[Dict[str, Any]]:
    """Execute end-to-end multi-modal scan on a real NASA KOI candidate."""
    kepid = int(candidate_meta["kepid"])
    koi_name = candidate_meta.get("kepoi_name", f"KIC {kepid}")
    period = float(candidate_meta["koi_period"])
    t0 = float(candidate_meta["koi_time0bk"])
    depth_ppm = float(candidate_meta.get("koi_depth") or 0.0)

    t0_scan = time.perf_counter()
    print(f"--> Ingesting KIC {kepid} ({koi_name}) | P={period:.4f}d | Depth={depth_ppm:.0f}ppm...", end="", flush=True)

    lc = fetch_kepler_candidate_light_curve(kepid, max_quarters=max_quarters)
    if lc is None or len(lc.time) < 100:
        print(" [SKIP: No archive data]")
        return None

    # Preprocessing
    lc_clean = preprocess_light_curve(lc, strict_quality=True, clip_outliers=True, detrend=True)
    if len(lc_clean.time) < 50:
        print(" [SKIP: Insufficient valid cadences after quality filter]")
        return None

    # 1. Catastrophic Disintegration & Dust Tail Scan
    dust_res = detect_dust_tail(lc_clean, period=period, t0=t0)

    # 2. Exomoon & Trojan Gravitational Perturbation Scan
    pert_res = detect_perturbations(lc_clean, period=period, t0=t0)

    elapsed = time.perf_counter() - t0_scan

    # Interpret physical classification
    anomalies = []
    if dust_res.is_asymmetric_dust_tail and dust_res.delta_bic >= 10.0:
        anomalies.append(f"EVAPORATING CRUST / DUST TAIL (dBIC={dust_res.delta_bic:+.1f}, alpha={dust_res.asymmetry_parameter:.2f})")
    elif dust_res.delta_bic >= 5.0 and dust_res.asymmetry_parameter > 0.25:
        anomalies.append(f"MILD ASYMMETRY (dBIC={dust_res.delta_bic:+.1f})")

    if pert_res.has_exomoon_candidate and pert_res.p_moon_posterior >= 0.85:
        anomalies.append(f"EXOMOON ORBITAL PERTURBATION (P={pert_res.p_moon_posterior*100:.1f}%, TTV SNR={pert_res.ttv_snr:.1f})")
    elif pert_res.ttv_snr >= 4.0:
        anomalies.append(f"STRONG TTV OSCILLATION (SNR={pert_res.ttv_snr:.1f})")

    if pert_res.has_trojan_candidate:
        anomalies.append("CO-ORBITAL TROJAN COMPANION")

    verdict = " + ".join(anomalies) if anomalies else "Symmetric Planet Transit (Standard)"

    print(f" DONE ({elapsed:.2f}s) -> {verdict}")

    return {
        "kepid": kepid,
        "koi_name": koi_name,
        "period_days": period,
        "t0_bkjd": t0,
        "catalog_depth_ppm": depth_ppm,
        "cadences": len(lc_clean.time),
        "baseline_days": float(lc_clean.time[-1] - lc_clean.time[0]),
        "dust_tail": {
            "is_detected": bool(dust_res.is_asymmetric_dust_tail),
            "delta_bic": float(dust_res.delta_bic),
            "asymmetry_alpha": float(dust_res.asymmetry_parameter),
            "lrt_p_value": float(dust_res.lrt_p_value),
            "tail_decay_length": float(dust_res.tail_decay_length),
            "depth_variance": float(dust_res.depth_variance),
        },
        "perturbations": {
            "is_exomoon_candidate": bool(pert_res.has_exomoon_candidate),
            "p_moon_posterior": float(pert_res.p_moon_posterior),
            "ttv_snr": float(pert_res.ttv_snr),
            "orthogonal_phase_diff_deg": float(pert_res.orthogonal_phase_diff_deg),
            "is_trojan_candidate": bool(pert_res.has_trojan_candidate),
        },
        "verdict": verdict,
        "runtime_seconds": float(elapsed),
    }


def main():
    print("=" * 84)
    print("  FRONTIER ASTRONOMY AI - REAL NASA CANDIDATE DISCOVERY CAMPAIGN")
    print("=" * 84)
    print("  Connecting to NASA observational archives (STScI/MAST)...")
    print("  Scanning unconfirmed Kepler Objects of Interest (KOIs) for:")
    print("   1. Evaporating rocky crusts with trailing cometary dust tails")
    print("   2. Multi-body gravitational wobbles & candidate exomoons")
    print("=" * 84 + "\n")

    # Load candidate lists
    with open("data/nasa_candidates_usp.json", "r", encoding="utf-8") as f:
        usp_list = json.load(f)
    with open("data/nasa_candidates_moon.json", "r", encoding="utf-8") as f:
        moon_list = json.load(f)

    # Prioritize targets with highest signal-to-noise
    usp_targets = sorted(usp_list, key=lambda x: x.get("koi_depth") or 0.0, reverse=True)[:10]
    moon_targets = sorted(moon_list, key=lambda x: x.get("koi_depth") or 0.0, reverse=True)[:10]

    all_targets = usp_targets + moon_targets

    results = []
    print(f"Initiating scan across {len(all_targets)} high-priority unconfirmed NASA candidate stars...\n")

    for i, meta in enumerate(all_targets, 1):
        print(f"[{i:02d}/{len(all_targets):02d}] ", end="")
        res = scan_candidate(meta, max_quarters=3)
        if res:
            results.append(res)

    # Format Scorecard Table
    print("\n" + "=" * 105)
    print(" NASA CANDIDATE AI DISCOVERY SCORECARD")
    print("=" * 105)
    header = f"{'Target':<14} | {'Period (d)':<10} | {'Depth (ppm)':<11} | {'Delta-BIC':<10} | {'Asym (alpha)':<12} | {'TTV SNR':<9} | {'P(Moon)':<8} | {'Physical Signal'}"
    print(header)
    print("-" * 105)

    for r in results:
        target_lbl = f"KIC {r['kepid']}"
        period_str = f"{r['period_days']:.4f}"
        depth_str = f"{r['catalog_depth_ppm']:.0f}"
        dbic_str = f"{r['dust_tail']['delta_bic']:+.1f}"
        asym_str = f"{r['dust_tail']['asymmetry_alpha']:.3f}"
        ttv_str = f"{r['perturbations']['ttv_snr']:.1f}"
        pmoon_str = f"{r['perturbations']['p_moon_posterior']*100:.0f}%"
        verdict = r["verdict"]
        print(f"{target_lbl:<14} | {period_str:<10} | {depth_str:<11} | {dbic_str:<10} | {asym_str:<12} | {ttv_str:<9} | {pmoon_str:<8} | {verdict}")

    print("=" * 105)

    # Save discovery catalog
    out_path = Path("results/real_nasa_discoveries.json")
    out_path.parent.mkdir(parents=True, exist_ok=True)
    with open(out_path, "w", encoding="utf-8") as f:
        json.dump(results, f, indent=2)

    print(f"\n[OK] Discovery catalog generated and saved to {out_path}!")


if __name__ == "__main__":
    main()
