"""Dashboard interactive components subpackage.

Exports modular visual analytics views for:
1. Light curves and transit profiles with multi-model overlays
2. 2D localized residual anomaly heatmaps (epoch vs orbital phase)
3. Exomoon & perturbation analyzers (O-C diagrams and pi/2 phase tests)
4. JWST atmospheric inversion spectra, credible envelopes, and corner plots
"""

from __future__ import annotations

from frontier_astronomy.dashboard.components.lightcurve_view import (
    build_lightcurve_figure,
    format_lightcurve_plot_data,
    render_lightcurve_view,
)
from frontier_astronomy.dashboard.components.heatmap_view import (
    build_heatmap_figure,
    compute_residual_heatmap,
    render_heatmap_view,
)
from frontier_astronomy.dashboard.components.perturbation_view import (
    build_oc_diagram_figure,
    build_phase_invariant_figure,
    format_oc_diagram_data,
    format_shoulder_zoom_data,
    format_trojan_dips_data,
    render_perturbation_view,
)
from frontier_astronomy.dashboard.components.atmospheric_view import (
    PARAM_LABELS,
    PARAM_NAMES,
    build_corner_plot_figure,
    build_spectrum_fit_figure,
    format_atmospheric_plot_data,
    render_atmospheric_view,
)

__all__ = [
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
    "PARAM_NAMES",
    "PARAM_LABELS",
]
