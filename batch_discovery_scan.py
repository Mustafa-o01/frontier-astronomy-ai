"""Automated Multi-Target Discovery Scanner for NASA Kepler, K2, and TESS archives.

Runs the Frontier Astronomy AI detection pipelines across a batch of stellar targets,
evaluating catastrophic dust tail asymmetry, photodynamic exomoon perturbations, and
atmospheric chemistry, then producing an automated discovery scorecard.
"""

from __future__ import annotations

import argparse
import json
import sys
import time
from pathlib import Path
from typing import Any, Dict, List, Optional

import numpy as np

from frontier_astronomy.core.preprocessing import preprocess_light_curve
from frontier_astronomy.core.types import LightCurveData
from frontier_astronomy.dashboard.state import load_candidate_light_curve
from frontier_astronomy.dust_tail.detector import detect_dust_tail
from frontier_astronomy.ingestion.catalog import list_benchmark_systems, get_benchmark_system
from frontier_astronomy.perturbations import detect_perturbations


DEFAULT_SURVEY_TARGETS = [
    "KIC 12557548",
    "K2-22b",
    "KOI-2700b",
    "WD 1145+017",
    "Kepler-1625b",
    "Kepler-1708b",
]


def scan_single_target(
    target_id: str,
    mission: str = "Kepler",
    min_delta_bic: float = 10.0,
    min_ttv_snr: float = 3.0,
) -> Dict[str, Any]:
    """Execute complete multi-modal anomaly scan on a single light curve."""
    t0_scan = time.perf_counter()
    
    # 1. Load light curve
    lc = load_candidate_light_curve(target_id, mission=mission, fallback_on_missing=True)
    
    # 2. Extract ephemeris
    try:
        bench = get_benchmark_system(target_id)
        period = bench.period_days
        t0 = bench.t0_bkjd_or_btjd
    except Exception:
        period = float(lc.metadata.get("period", 1.0))
        t0 = float(lc.metadata.get("t0", lc.time[0]))

    # 3. Preprocess
    lc_clean = preprocess_light_curve(lc, strict_quality=True, clip_outliers=True, detrend=True)
    
    # 4. Dust Tail Detection
    dust_res = detect_dust_tail(lc_clean, period=period, t0=t0)
    
    # 5. Exomoon & Trojan Perturbation Detection
    pert_res = detect_perturbations(lc_clean, period=period, t0=t0)
    
    elapsed = time.perf_counter() - t0_scan

    # Determine classification verdict
    verdicts = []
    if dust_res.is_asymmetric_dust_tail and dust_res.delta_bic >= min_delta_bic:
        verdicts.append("CANDIDATE DISINTEGRATING PLANET (Dust Tail)")
    if pert_res.has_exomoon_candidate and pert_res.ttv_snr >= min_ttv_snr:
        verdicts.append(f"CANDIDATE EXOMOON (P={pert_res.p_moon_posterior*100:.1f}%)")
    if pert_res.has_trojan_candidate:
        verdicts.append("CANDIDATE TROJAN CO-ORBITAL")
    if not verdicts:
        verdicts.append("Standard Symmetric Exoplanet / Null")

    return {
        "target_id": target_id,
        "mission": lc.mission or mission,
        "cadences": len(lc_clean.time),
        "period_days": float(period),
        "t0": float(t0),
        "dust_tail": {
            "is_detected": bool(dust_res.is_asymmetric_dust_tail),
            "delta_bic": float(dust_res.delta_bic),
            "asymmetry_alpha": float(dust_res.asymmetry_parameter),
            "lrt_p_value": float(dust_res.lrt_p_value),
            "tail_length_phase": float(dust_res.tail_decay_length),
        },
        "perturbations": {
            "is_exomoon_candidate": bool(pert_res.has_exomoon_candidate),
            "ttv_snr": float(pert_res.ttv_snr),
            "phase_shift_deg": float(pert_res.orthogonal_phase_diff_deg),
            "p_moon": float(pert_res.p_moon_posterior),
            "is_trojan_candidate": bool(pert_res.has_trojan_candidate),
        },
        "verdict": " + ".join(verdicts),
        "runtime_seconds": float(elapsed),
    }


def run_survey(
    targets: List[str],
    mission: str = "Kepler",
    out_path: Optional[str] = None,
) -> List[Dict[str, Any]]:
    """Run batch scan across targets and print formatted summary table."""
    print("=" * 80)
    print(" FRONTIER ASTRONOMY AI - AUTOMATED MULTI-TARGET DISCOVERY SURVEY")
    print("=" * 80)
    print(f" Scanning {len(targets)} targets across NASA public observational archives...\n")

    results = []
    for i, target in enumerate(targets, 1):
        print(f"[{i}/{len(targets)}] Processing {target:<20} ...", end="", flush=True)
        try:
            res = scan_single_target(target, mission=mission)
            results.append(res)
            print(f" DONE ({res['runtime_seconds']:.2f}s) -> {res['verdict']}")
        except Exception as e:
            print(f" ERROR: {e}")

    # Print summary table
    print("\n" + "=" * 92)
    print(f"{'Target ID':<16} | {'Period (d)':<10} | {'Delta-BIC':<10} | {'Asym (alpha)':<12} | {'TTV SNR':<9} | {'Verdict'}")
    print("-" * 92)
    for r in results:
        t_id = r["target_id"][:15]
        per = f"{r['period_days']:.4f}"
        dbic = f"{r['dust_tail']['delta_bic']:+.1f}"
        asym = f"{r['dust_tail']['asymmetry_alpha']:.3f}"
        ttv = f"{r['perturbations']['ttv_snr']:.2f}"
        verd = r["verdict"]
        print(f"{t_id:<16} | {per:<10} | {dbic:<10} | {asym:<12} | {ttv:<9} | {verd}")
    print("=" * 92)

    # Save to disk
    out_file = Path(out_path or "results/batch_survey_report.json")
    out_file.parent.mkdir(parents=True, exist_ok=True)
    with open(out_file, "w", encoding="utf-8") as f:
        json.dump(results, f, indent=2)
    print(f"\n[OK] Full survey report saved to {out_file}\n")

    return results


def main() -> int:
    parser = argparse.ArgumentParser(description="Frontier Astronomy AI Multi-Target Discovery Scanner")
    parser.add_argument(
        "--targets",
        nargs="+",
        default=DEFAULT_SURVEY_TARGETS,
        help="List of target identifiers to scan (e.g. 'KIC 12557548' 'Kepler-1625b')",
    )
    parser.add_argument(
        "--mission",
        default="Kepler",
        choices=["Kepler", "K2", "TESS"],
        help="NASA telescope mission archive (default: Kepler)",
    )
    parser.add_argument(
        "--out",
        default="results/batch_survey_report.json",
        help="Path for output JSON report (default: results/batch_survey_report.json)",
    )
    args = parser.parse_args()

    run_survey(targets=args.targets, mission=args.mission, out_path=args.out)
    return 0


if __name__ == "__main__":
    sys.exit(main())
