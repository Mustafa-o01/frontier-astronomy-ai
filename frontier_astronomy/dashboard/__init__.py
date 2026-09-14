"""Frontier Astronomy AI Unified Interactive Discovery & Inspection Dashboard.

Exports:
- run_app: Main Streamlit dashboard launcher
- DashboardState: Session state and caching manager
- CandidateRecord: Discovery candidate data model
- filter_candidates: Multi-parameter candidate query engine
- Component views: lightcurve, heatmap, perturbation, atmospheric
"""

from __future__ import annotations

from frontier_astronomy.dashboard.app import main, run_app
from frontier_astronomy.dashboard.state import (
    CandidateRecord,
    DashboardState,
    decimate_time_series,
    filter_candidates,
    get_default_candidates,
    load_candidate_light_curve,
    load_candidate_spectrum,
)
from frontier_astronomy.dashboard.components import (
    build_corner_plot_figure,
    build_heatmap_figure,
    build_lightcurve_figure,
    build_oc_diagram_figure,
    build_phase_invariant_figure,
    build_spectrum_fit_figure,
    compute_residual_heatmap,
    format_atmospheric_plot_data,
    format_lightcurve_plot_data,
    format_oc_diagram_data,
    format_shoulder_zoom_data,
    format_trojan_dips_data,
    render_atmospheric_view,
    render_heatmap_view,
    render_lightcurve_view,
    render_perturbation_view,
)

__all__ = [
    "run_app",
    "main",
    "DashboardState",
    "CandidateRecord",
    "filter_candidates",
    "get_default_candidates",
    "decimate_time_series",
    "load_candidate_light_curve",
    "load_candidate_spectrum",
    "format_lightcurve_plot_data",
    "build_lightcurve_figure",
    "render_lightcurve_view",
    "compute_residual_heatmap",
    "build_heatmap_figure",
    "render_heatmap_view",
    "format_oc_diagram_data",
    "format_shoulder_zoom_data",
    "format_trojan_dips_data",
    "build_oc_diagram_figure",
    "build_phase_invariant_figure",
    "render_perturbation_view",
    "format_atmospheric_plot_data",
    "build_spectrum_fit_figure",
    "build_corner_plot_figure",
    "render_atmospheric_view",
]
