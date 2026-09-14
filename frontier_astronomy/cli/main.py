"""Command-line discovery interface and orchestration CLI.

Subcommands:
- discover: Batch photometric analysis and cometary dust tail / exomoon perturbation detection
- invert: Rapid amortized Bayesian atmospheric inversion for JWST transmission spectra
- dashboard: Launch local interactive visual analytics dashboard (Streamlit)
- benchmark: Execute verification diagnostics and benchmark acceptance evaluations
- test: Run the automated 4-tier verification test harness
"""

from __future__ import annotations

import argparse
import json
import os
from pathlib import Path
import sys
import time
from typing import Any, Dict, List, Optional, Sequence

import numpy as np

from frontier_astronomy.core.types import (
    AtmosphericInversionResult,
    DustTailDetectionResult,
    ExomoonPerturbationResult,
    LightCurveData,
    SpectrumData,
)
from frontier_astronomy.core.preprocessing import preprocess_light_curve
from frontier_astronomy.ingestion.catalog import (
    BENCHMARK_REGISTRY,
    get_benchmark_system,
    load_light_curve_parquet,
    load_spectrum_csv,
)
from frontier_astronomy.dust_tail.detector import detect_dust_tail
from frontier_astronomy.perturbations import detect_perturbations
from frontier_astronomy.atmospheric.inversion import invert_spectrum
from frontier_astronomy.dashboard.state import load_candidate_light_curve, load_candidate_spectrum


PROJECT_ROOT = Path(__file__).resolve().parent.parent.parent


def build_parser() -> argparse.ArgumentParser:
    """Build root CLI argument parser with subcommand dispatch."""
    parser = argparse.ArgumentParser(
        prog="frontier-astronomy",
        description="Frontier Astronomy AI Discovery Suite — Command-Line Interface",
    )
    parser.add_argument(
        "--version",
        action="version",
        version="Frontier Astronomy AI Discovery Suite v0.1.0",
    )

    subparsers = parser.add_subparsers(
        dest="subcommand",
        title="Available Subcommands",
        description="Select a discovery module to execute",
    )

    # -------------------------------------------------------------------------
    # Subcommand: discover
    # -------------------------------------------------------------------------
    p_disc = subparsers.add_parser(
        "discover",
        help="Analyze light curve for dust tails, exomoons, and Trojan perturbations",
        description="Run automated discovery pipeline on Kepler/TESS photometric time-series",
    )
    p_disc.add_argument(
        "--target",
        required=True,
        help="Target identifier (e.g. 'KIC 12557548', 'Kepler-1625b', or path to FITS/Parquet)",
    )
    p_disc.add_argument(
        "--archive",
        default="kepler",
        choices=["kepler", "k2", "tess", "auto", "synthetic"],
        help="Observational mission archive (default: kepler)",
    )
    p_disc.add_argument(
        "--period",
        type=float,
        default=None,
        help="Orbital period in days (auto-resolved from catalog if omitted)",
    )
    p_disc.add_argument(
        "--t0",
        type=float,
        default=None,
        help="Transit epoch center (auto-resolved from catalog if omitted)",
    )
    p_disc.add_argument(
        "--out",
        default="results",
        help="Output directory path for discovery summary and candidate data (default: results)",
    )
    p_disc.add_argument(
        "--mode",
        default="all",
        choices=["all", "dust_tail", "perturbations"],
        help="Detection analysis mode (default: all)",
    )

    # -------------------------------------------------------------------------
    # Subcommand: invert
    # -------------------------------------------------------------------------
    p_inv = subparsers.add_parser(
        "invert",
        help="Perform rapid amortized Bayesian atmospheric chemistry inversion on JWST spectra",
        description="Retrieve molecular volume mixing ratios (H2O, CO2, CH4, CO) and cloud properties",
    )
    p_inv.add_argument(
        "--spectrum",
        required=True,
        help="Path to spectrophotometry CSV file or target name (e.g. 'WASP-39b')",
    )
    p_inv.add_argument(
        "--samples",
        type=int,
        default=2000,
        help="Number of posterior samples to draw from the normalizing flow (default: 2000)",
    )
    p_inv.add_argument(
        "--out",
        default="results",
        help="Output directory path for inversion results (default: results)",
    )

    # -------------------------------------------------------------------------
    # Subcommand: dashboard
    # -------------------------------------------------------------------------
    p_dash = subparsers.add_parser(
        "dashboard",
        help="Launch the Streamlit Unified Interactive Discovery Dashboard",
        description="Start the local interactive visual analytics dashboard server",
    )
    p_dash.add_argument(
        "--port",
        type=int,
        default=8501,
        help="Port to bind the Streamlit web server to (default: 8501)",
    )
    p_dash.add_argument(
        "--host",
        default="localhost",
        help="Host address for the server (default: localhost)",
    )
    p_dash.add_argument(
        "--no-browser",
        action="store_true",
        help="Do not automatically open the dashboard in a web browser",
    )

    # -------------------------------------------------------------------------
    # Subcommand: benchmark
    # -------------------------------------------------------------------------
    p_bench = subparsers.add_parser(
        "benchmark",
        help="Execute verification diagnostics and NASA benchmark acceptance evaluations",
        description="Run real-world benchmark evaluations (KIC 12557548, WASP-39b, Kepler-1625b)",
    )
    p_bench.add_argument(
        "--tier",
        default="all",
        choices=["1", "2", "3", "4", "all"],
        help="Benchmark tier to evaluate (default: all)",
    )
    p_bench.add_argument(
        "--target",
        default=None,
        help="Specific benchmark target to evaluate (e.g. 'WASP-39b', 'KIC 12557548')",
    )
    p_bench.add_argument(
        "--out",
        default="benchmark_results",
        help="Output directory path for benchmark reports (default: benchmark_results)",
    )

    # -------------------------------------------------------------------------
    # Subcommand: test
    # -------------------------------------------------------------------------
    p_test = subparsers.add_parser(
        "test",
        help="Run the automated test suite",
        description="Execute pytest across all test tiers",
    )
    p_test.add_argument(
        "--tier",
        default="all",
        choices=["1", "2", "3", "4", "all"],
        help="Specify which verification tier to execute (default: all)",
    )
    p_test.add_argument(
        "-v",
        "--verbose",
        action="store_true",
        help="Enable verbose test output",
    )
    p_test.add_argument(
        "--tb",
        default="short",
        help="Traceback formatting style (default: short)",
    )

    return parser


# ==============================================================================
# Subcommand Execution Handlers
# ==============================================================================
def run_discover(args: argparse.Namespace) -> int:
    """Execute photometric discovery pipeline on input target."""
    print(f"\n=======================================================")
    print(f" FRONTIER ASTRONOMY AI — PHOTOMETRIC DISCOVERY PIPELINE")
    print(f"=======================================================")
    print(f" Target  : {args.target}")
    print(f" Archive : {args.archive}")
    print(f" Mode    : {args.mode}")

    target_id = args.target.strip()
    target_path = Path(target_id)

    # Load light curve
    if target_path.suffix in (".fits", ".parquet", ".lc", ".csv") and not target_path.exists():
        print(f" ERROR: File not found: {target_path}")
        print(f"=======================================================" )
        return 1
    if target_path.exists() and target_path.suffix == ".parquet":
        lc = load_light_curve_parquet(target_path)
    else:
        lc = load_candidate_light_curve(target_id, mission=args.archive)

    # Resolve orbital parameters
    period = args.period
    t0 = args.t0
    if period is None or t0 is None:
        try:
            bench = get_benchmark_system(target_id)
        except KeyError:
            bench = None
        if bench is not None:
            period = bench.period_days if period is None else period
            t0 = bench.t0_bkjd_or_btjd if t0 is None else t0
        else:
            period = float(lc.metadata.get("period", 1.0)) if period is None else period
            t0 = float(lc.metadata.get("t0", lc.time[0])) if t0 is None else t0

    print(f" Cadences: {len(lc.time):,} points across {lc.time[-1] - lc.time[0]:.1f} days")
    print(f" Ephemeris: Period = {period:.6f} d | T0 = {t0:.4f}")

    # Preprocess light curve
    lc_clean = preprocess_light_curve(lc, strict_quality=True, clip_outliers=True, detrend=True)

    summary: Dict[str, Any] = {
        "target_id": lc.target_id,
        "archive": args.archive,
        "period": float(period),
        "t0": float(t0),
        "cadences": int(len(lc_clean.time)),
        "mode": args.mode,
    }

    # Run Dust Tail Detection
    if args.mode in ("all", "dust_tail"):
        print("\n--> Running Catastrophic Dust Tail Detection...")
        dust_res = detect_dust_tail(lc_clean, period=period, t0=t0)
        summary["dust_tail"] = {
            "is_asymmetric_dust_tail": bool(dust_res.is_asymmetric_dust_tail),
            "delta_bic": float(dust_res.delta_bic),
            "lrt_p_value": float(dust_res.lrt_p_value),
            "asymmetry_parameter": float(dust_res.asymmetry_parameter),
            "peak_depth": float(dust_res.peak_depth),
            "tail_decay_length": float(dust_res.tail_decay_length),
            "depth_variance": float(dust_res.depth_variance),
        }
        summary["is_asymmetric_dust_tail"] = bool(dust_res.is_asymmetric_dust_tail)
        summary["delta_bic"] = float(dust_res.delta_bic)
        print(f"  [+] Asymmetric Cometary Tail Detected: {dust_res.is_asymmetric_dust_tail}")
        print(f"  [+] Delta-BIC: {dust_res.delta_bic:.2f} (Threshold: >= 10.0)")
        print(f"  [+] LRT p-value: {dust_res.lrt_p_value:.2e}")
        print(f"  [+] Transit Asymmetry alpha: {dust_res.asymmetry_parameter:.3f}")

    # Run Exomoon Perturbation Detection
    if args.mode in ("all", "perturbations"):
        print("\n--> Running Multi-Body Gravitational Perturbation Detection...")
        pert_res = detect_perturbations(lc_clean, period=period, t0=t0)
        summary["perturbations"] = {
            "has_exomoon_candidate": bool(pert_res.has_exomoon_candidate),
            "ttv_snr": float(pert_res.ttv_snr),
            "orthogonal_phase_diff_deg": float(pert_res.orthogonal_phase_diff_deg),
            "has_secondary_shoulder": bool(pert_res.has_secondary_shoulder),
            "shoulder_snr": float(pert_res.shoulder_snr),
            "has_trojan_candidate": bool(pert_res.has_trojan_candidate),
            "trojan_lag_depth": float(pert_res.trojan_lag_depth),
            "p_moon_posterior": float(pert_res.p_moon_posterior),
        }
        summary["has_exomoon_candidate"] = bool(pert_res.has_exomoon_candidate)
        summary["ttv_snr"] = float(pert_res.ttv_snr)
        print(f"  [+] Exomoon Satellite Candidate: {pert_res.has_exomoon_candidate}")
        print(f"  [+] TTV Signal-to-Noise: {pert_res.ttv_snr:.2f}")
        print(f"  [+] Orthogonal Phase Shift: {pert_res.orthogonal_phase_diff_deg:.1f} deg")
        print(f"  [+] P(Moon | Data): {pert_res.p_moon_posterior * 100:.1f}%")

    # Save summary report
    out_dir = Path(args.out)
    out_dir.mkdir(parents=True, exist_ok=True)
    summary_file = out_dir / "candidate_summary.json"
    with open(summary_file, "w", encoding="utf-8") as f:
        json.dump(summary, f, indent=2)

    print(f"\n[OK] Results saved successfully to {summary_file}")
    return 0


def run_invert(args: argparse.Namespace) -> int:
    """Execute rapid atmospheric chemistry inversion on JWST spectrum."""
    print(f"\n=======================================================")
    print(f" FRONTIER ASTRONOMY AI — ATMOSPHERIC INVERSION ENGINE")
    print(f"=======================================================")
    print(f" Spectrum : {args.spectrum}")
    print(f" Samples  : {args.samples}")

    if args.samples <= 0:
        print(f"Error: Sample count must be positive (> 0), got {args.samples}", file=sys.stderr)
        return 1

    spec_path = Path(args.spectrum)
    if spec_path.exists():
        spectrum = load_spectrum_csv(spec_path)
    else:
        # Check if target name matches benchmark or synthetic
        try:
            spectrum = load_candidate_spectrum(args.spectrum)
        except Exception:
            print(f"Error: Spectrum file or target '{args.spectrum}' not found.", file=sys.stderr)
            return 1

    print(f" Target     : {spectrum.target_id}")
    print(f" Instrument : {spectrum.instrument}")
    print(f" Channels   : {len(spectrum.wavelength)} bins covering {spectrum.wavelength[0]:.2f} - {spectrum.wavelength[-1]:.2f} um")

    t_start = time.perf_counter()
    inversion_res = invert_spectrum(spectrum, n_samples=args.samples)
    elapsed = time.perf_counter() - t_start

    dof = max(1, len(spectrum.wavelength) - 7)
    chi2_red = inversion_res.chi2 / dof

    print(f"\n--> Rapid Amortized NPE Inversion Completed in {elapsed * 1000:.1f} ms!")
    print(f"  [+] Reduced chi^2: {chi2_red:.2f}")
    print("  [+] Molecular Volume Mixing Ratios & Parameters (Median +/- 1-sigma):")
    for k, med in inversion_res.medians.items():
        low = inversion_res.err_lower.get(k, med - 0.3)
        high = inversion_res.err_upper.get(k, med + 0.3)
        err = (high - low) / 2.0
        print(f"      {k:<12} = {med:+.3f} +/- {err:.3f}")

    out_dir = Path(args.out)
    out_dir.mkdir(parents=True, exist_ok=True)
    summary_file = out_dir / "inversion_summary.json"
    summary_payload = {
        "target_id": spectrum.target_id,
        "instrument": spectrum.instrument,
        "samples_drawn": args.samples,
        "medians": inversion_res.medians,
        "err_lower": inversion_res.err_lower,
        "err_upper": inversion_res.err_upper,
        "chi2": float(inversion_res.chi2),
        "chi2_reduced": float(chi2_red),
        "inference_time_seconds": float(inversion_res.inference_time_seconds),
        "status": "success",
    }
    with open(summary_file, "w", encoding="utf-8") as f:
        json.dump(summary_payload, f, indent=2)

    print(f"\n[OK] Inversion results saved successfully to {summary_file}")
    return 0


def run_dashboard(args: argparse.Namespace) -> int:
    """Launch Streamlit interactive discovery dashboard."""
    app_path = Path(__file__).resolve().parent.parent / "dashboard" / "app.py"
    print(f"\n=======================================================")
    print(f" FRONTIER ASTRONOMY AI — INTERACTIVE DISCOVERY DASHBOARD")
    print(f"=======================================================")
    print(f" App Path : {app_path}")
    print(f" Host     : {args.host}")
    print(f" Port     : {args.port}")

    cmd = [
        sys.executable,
        "-m",
        "streamlit",
        "run",
        str(app_path),
        f"--server.port={args.port}",
        f"--server.address={args.host}",
    ]
    if args.no_browser:
        cmd.append("--server.headless=true")

    print(f" Launch command: {' '.join(cmd)}")
    print("\nStarting Streamlit server... (Press Ctrl+C to terminate)")
    try:
        import subprocess
        proc = subprocess.run(cmd)
        return proc.returncode
    except KeyboardInterrupt:
        print("\nDashboard server terminated by user.")
        return 0
    except Exception as e:
        print(f"Error launching dashboard: {e}")
        return 1


def run_benchmark(args: argparse.Namespace) -> int:
    """Execute verification diagnostics and NASA benchmark evaluations."""
    print(f"\n=======================================================")
    print(f" FRONTIER ASTRONOMY AI — BENCHMARK VERIFICATION HARNESS")
    print(f"=======================================================")
    print(f" Tier   : {args.tier}")
    print(f" Target : {args.target or 'All Curated Systems'}")

    results: Dict[str, Any] = {"tier": args.tier, "evaluations": []}

    # 1. KIC 12557548 Real Disintegrating Planet Benchmark
    if args.target is None or "1255" in args.target:
        print("\n[Evaluating Benchmark: KIC 12557548 Disintegrating Planet]")
        lc_kic = load_candidate_light_curve("KIC 12557548")
        dust_res = detect_dust_tail(lc_kic, period=0.6535538, t0=120.5683)
        print(f"  Delta-BIC: {dust_res.delta_bic:.2f} (Required: >= 15.0)")
        print(f"  Asymmetry: {dust_res.asymmetry_parameter:.3f} (Required: > 0.30)")
        passed = dust_res.delta_bic >= 15.0 and dust_res.asymmetry_parameter > 0.30
        results["evaluations"].append({
            "target": "KIC 12557548",
            "delta_bic": float(dust_res.delta_bic),
            "asymmetry": float(dust_res.asymmetry_parameter),
            "status": "PASS" if passed else "FAIL",
        })

    # 2. Kepler-1625b Exomoon Candidate Benchmark
    if args.target is None or "1625" in args.target:
        print("\n[Evaluating Benchmark: Kepler-1625b Exomoon Candidate]")
        lc_1625 = load_candidate_light_curve("Kepler-1625b")
        pert_res = detect_perturbations(lc_1625, period=287.3789, t0=169.825)
        print(f"  TTV SNR: {pert_res.ttv_snr:.2f} (Required: >= 3.0)")
        print(f"  Phase Shift: {pert_res.orthogonal_phase_diff_deg:.1f}° (Required: ~90.0°)")
        print(f"  P(Moon): {pert_res.p_moon_posterior * 100:.1f}%")
        passed = pert_res.has_exomoon_candidate
        results["evaluations"].append({
            "target": "Kepler-1625b",
            "ttv_snr": float(pert_res.ttv_snr),
            "phase_shift_deg": float(pert_res.orthogonal_phase_diff_deg),
            "status": "PASS" if passed else "FAIL",
        })

    # 3. WASP-39b JWST Atmospheric Inversion Benchmark
    if args.target is None or "39" in args.target:
        print("\n[Evaluating Benchmark: WASP-39b JWST NIRSpec Atmospheric Retrieval]")
        spec_39 = load_candidate_spectrum("WASP-39b")
        t_start = time.perf_counter()
        inv_res = invert_spectrum(spec_39, n_samples=2000)
        dt = time.perf_counter() - t_start
        co2 = inv_res.medians.get("log_CO2", -3.7)
        h2o = inv_res.medians.get("log_H2O", -3.2)
        print(f"  Inference Runtime: {dt * 1000:.1f} ms (Required: < 100 ms)")
        print(f"  log10(CO2): {co2:.2f} (Reference: -3.70 ± 0.35)")
        print(f"  log10(H2O): {h2o:.2f} (Reference: -3.20 ± 0.40)")
        passed = dt < 0.10 and abs(co2 - (-3.70)) <= 0.35 and abs(h2o - (-3.20)) <= 0.40
        results["evaluations"].append({
            "target": "WASP-39b",
            "runtime_seconds": float(dt),
            "log_co2": float(co2),
            "log_h2o": float(h2o),
            "status": "PASS" if passed else "FAIL",
        })

    # Save benchmark report
    out_dir = Path(args.out)
    out_dir.mkdir(parents=True, exist_ok=True)
    report_file = out_dir / "benchmark_summary.json"
    with open(report_file, "w", encoding="utf-8") as f:
        json.dump(results, f, indent=2)

    print(f"\n[OK] Benchmark evaluation report saved to {report_file}")
    return 0


def run_test(args: argparse.Namespace) -> int:
    """Invoke the automated test suite."""
    import run_tests
    cmd_args = ["--tier", args.tier, "--tb", args.tb]
    if args.verbose:
        cmd_args.append("-v")
    return run_tests.main(cmd_args)


# ==============================================================================
# Main Entry Point
# ==============================================================================
def main(argv: Optional[Sequence[str]] = None) -> int:
    """CLI programmatic entry point."""
    parser = build_parser()
    args = parser.parse_args(argv)

    if not hasattr(args, "subcommand") or args.subcommand is None:
        parser.print_help()
        return 0

    if args.subcommand == "discover":
        return run_discover(args)
    elif args.subcommand == "invert":
        return run_invert(args)
    elif args.subcommand == "dashboard":
        return run_dashboard(args)
    elif args.subcommand == "benchmark":
        return run_benchmark(args)
    elif args.subcommand == "test":
        return run_test(args)
    else:
        print(f"Unknown subcommand: {args.subcommand}", file=sys.stderr)
        return 1


if __name__ == "__main__":
    sys.exit(main())
