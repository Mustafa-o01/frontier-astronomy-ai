"""Command-line interface subpackage for Frontier Astronomy AI.

Exports:
- main: Primary CLI programmatic entry point
- build_parser: Argparse parser builder
- run_discover: Photometric dust tail and perturbation discovery handler
- run_invert: Amortized Bayesian atmospheric chemistry inversion handler
- run_dashboard: Streamlit visual analytics launcher
- run_benchmark: Verification diagnostics and benchmark evaluations
- run_test: Automated test suite runner
"""

from __future__ import annotations

from frontier_astronomy.cli.main import (
    build_parser,
    main,
    run_benchmark,
    run_dashboard,
    run_discover,
    run_invert,
    run_test,
)

__all__ = [
    "main",
    "build_parser",
    "run_discover",
    "run_invert",
    "run_dashboard",
    "run_benchmark",
    "run_test",
]
