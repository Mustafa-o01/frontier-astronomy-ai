#!/usr/bin/env python
"""Standalone programmatic zero-error test runner for Frontier Astronomy AI Discovery Suite.

Executes the comprehensive 4-Tier test suite:
  - Tier 1: Feature Coverage (>=55 tests across all 11 features)
  - Tier 2: Boundary & Corner Cases (>=55 tests across all 11 features)
  - Tier 3: Pairwise & Cross-Feature Integration (>=11 workflows)
  - Tier 4: Real-World Benchmark Acceptance Scenarios (6 scenarios)

Total minimum threshold: >= 127 tests.

Usage:
    python run_tests.py [--tier {1,2,3,4,all}] [-v] [--tb {short,auto,line,native}]
"""

from __future__ import annotations

import argparse
import sys
import time
from pathlib import Path
import pytest


PROJECT_ROOT = Path(__file__).resolve().parent
TESTS_DIR = PROJECT_ROOT / "tests"


class TestMetricsCollector:
    """Pytest plugin to collect detailed execution statistics across tiers."""

    def __init__(self) -> None:
        self.passed: int = 0
        self.failed: int = 0
        self.skipped: int = 0
        self.errors: int = 0
        self.tier_counts: dict[str, dict[str, int]] = {
            "tier1": {"passed": 0, "failed": 0, "skipped": 0},
            "tier2": {"passed": 0, "failed": 0, "skipped": 0},
            "tier3": {"passed": 0, "failed": 0, "skipped": 0},
            "tier4": {"passed": 0, "failed": 0, "skipped": 0},
            "other": {"passed": 0, "failed": 0, "skipped": 0},
        }

    def pytest_runtest_logreport(self, report: pytest.TestReport) -> None:
        if report.when == "call":
            tier_key = "other"
            if "test_tier1" in report.nodeid:
                tier_key = "tier1"
            elif "test_tier2" in report.nodeid:
                tier_key = "tier2"
            elif "test_tier3" in report.nodeid:
                tier_key = "tier3"
            elif "test_tier4" in report.nodeid:
                tier_key = "tier4"

            if report.passed:
                self.passed += 1
                self.tier_counts[tier_key]["passed"] += 1
            elif report.failed:
                self.failed += 1
                self.tier_counts[tier_key]["failed"] += 1
            elif report.skipped:
                self.skipped += 1
                self.tier_counts[tier_key]["skipped"] += 1
        elif report.failed and report.when in ("setup", "teardown"):
            self.errors += 1


def build_parser() -> argparse.ArgumentParser:
    """Construct command-line argument parser for run_tests."""
    parser = argparse.ArgumentParser(
        prog="run_tests.py",
        description="Frontier Astronomy AI Discovery Suite Programmatic Test Runner",
    )
    parser.add_argument(
        "--tier",
        choices=["1", "2", "3", "4", "all"],
        default="all",
        help="Specify which verification tier to execute (default: all)",
    )
    parser.add_argument(
        "-v",
        "--verbose",
        action="store_true",
        help="Enable verbose test output",
    )
    parser.add_argument(
        "--tb",
        default="short",
        choices=["short", "auto", "line", "native", "no"],
        help="Traceback formatting style (default: short)",
    )
    return parser


def print_summary_table(collector: TestMetricsCollector, elapsed_seconds: float) -> None:
    """Render a clean summary banner of test suite execution metrics."""
    total_tests = collector.passed + collector.failed + collector.skipped
    width = 76
    line_eq = "=" * width
    line_dash = "-" * width

    print("\n" + line_eq)
    print(" FRONTIER ASTRONOMY AI DISCOVERY SUITE - 4-TIER TEST EXECUTION REPORT")
    print(line_eq)
    print(f" {'Verification Tier':<40} | {'Pass':<6} | {'Fail':<6} | {'Skip':<6} | {'Total':<6}")
    print(line_dash)

    tier_labels = [
        ("tier1", "Tier 1: Feature Coverage (>=55)", collector.tier_counts["tier1"]),
        ("tier2", "Tier 2: Boundary & Corner Cases (>=55)", collector.tier_counts["tier2"]),
        ("tier3", "Tier 3: Cross-Feature Integration (>=11)", collector.tier_counts["tier3"]),
        ("tier4", "Tier 4: Real-World Benchmarks (>=6)", collector.tier_counts["tier4"]),
    ]

    for key, label, counts in tier_labels:
        tot = counts["passed"] + counts["failed"] + counts["skipped"]
        print(f" {label:<40} | {counts['passed']:<6} | {counts['failed']:<6} | {counts['skipped']:<6} | {tot:<6}")

    print(line_dash)
    print(f" {'TOTAL AGGREGATED ASSERTIONS':<40} | {collector.passed:<6} | {collector.failed:<6} | {collector.skipped:<6} | {total_tests:<6}")
    print(line_eq)
    print(f" Execution Elapsed Time : {elapsed_seconds:.2f} seconds")
    print(f" Minimum Required Threshold: >= 127 tests | Discovered: {total_tests} tests")

    if collector.failed == 0 and collector.errors == 0 and collector.passed >= 127:
        print(" VERDICT: ALL TIERS PASSED (100% SUCCESS, 0 ERRORS) - READY FOR DEPLOYMENT")
    elif collector.failed == 0 and collector.errors == 0:
        print(" VERDICT: PASSING (0 ERRORS, All executed tests passed)")
    else:
        print(f" VERDICT: FAILED ({collector.failed} failures, {collector.errors} setup/teardown errors)")
    print(line_eq + "\n")


def main(argv: list[str] | None = None) -> int:
    """Programmatic entry point for test runner."""
    parser = build_parser()
    args = parser.parse_args(argv)

    pytest_args = ["-q", f"--tb={args.tb}"]
    if args.verbose:
        pytest_args.append("-v")

    if args.tier == "1":
        pytest_args.append(str(TESTS_DIR / "test_tier1_features.py"))
    elif args.tier == "2":
        pytest_args.append(str(TESTS_DIR / "test_tier2_boundaries.py"))
    elif args.tier == "3":
        pytest_args.append(str(TESTS_DIR / "test_tier3_integration.py"))
    elif args.tier == "4":
        pytest_args.append(str(TESTS_DIR / "test_tier4_benchmarks.py"))
    else:
        pytest_args.append(str(TESTS_DIR))

    collector = TestMetricsCollector()
    t_start = time.perf_counter()
    exit_code = pytest.main(pytest_args, plugins=[collector])
    elapsed = time.perf_counter() - t_start

    print_summary_table(collector, elapsed)
    return int(exit_code)


if __name__ == "__main__":
    sys.exit(main())
