"""Light curve and transit profile inspection view component.

Provides raw time-series visualization, phase folding, inverse-variance binning,
and comparative model overlays (symmetric planetary baseline vs cometary dust tail
vs exomoon mutual perturbations).
"""

from __future__ import annotations

from typing import Any, Dict, List, Optional, Tuple, Union
import numpy as np

from frontier_astronomy.core.types import FoldedTransit, LightCurveData
from frontier_astronomy.core.preprocessing import (
    fold_light_curve,
    inverse_variance_bin,
    phase_fold,
)
from frontier_astronomy.core.math_utils import symmetric_trapezoid_transit
from frontier_astronomy.dust_tail.extinction_model import (
    cometary_extinction_profile,
    compute_asymmetry_parameter,
)
from frontier_astronomy.dashboard.state import decimate_time_series


def format_lightcurve_plot_data(
    lc: LightCurveData,
    period: Optional[float] = None,
    t0: Optional[float] = None,
    max_display_points: int = 5000,
    n_phase_bins: int = 100,
    overlay_models: bool = True,
    transit_depth: Optional[float] = None,
) -> Dict[str, Any]:
    """Format raw time series, folded phase profile, binned points, and model overlays.

    Conforms to test_f10_02_transit_profile_model_overlay_formatting:
    - Folds light curve into FoldedTransit where len(phase) == len(flux).
    - Decimates raw time series if len(time) > max_display_points.
    - Generates symmetric, cometary dust tail, and exomoon overlays.
    """
    p = float(period) if period is not None else float(lc.metadata.get("period", 1.0))
    t_zero = float(t0) if t0 is not None else float(lc.metadata.get("t0", lc.time[0]))

    # 1. Decimated raw time-series for fast UI rendering
    t_raw, f_raw, fe_raw = decimate_time_series(
        lc.time, lc.flux, lc.flux_err, max_points=max_display_points
    )

    # 2. Phase fold full cadences
    folded = fold_light_curve(lc, period=p, t0=t_zero)
    phase = folded.phase
    flux = folded.flux
    flux_err = folded.flux_err

    # 3. Inverse-variance binning
    bin_centers, bin_flux, bin_err, _ = inverse_variance_bin(
        phase, flux, flux_err, n_bins=n_phase_bins
    )

    # Filter out empty bins
    valid_bins = ~np.isnan(bin_flux)
    bin_centers = bin_centers[valid_bins]
    bin_flux = bin_flux[valid_bins]
    bin_err = bin_err[valid_bins]

    # 4. Model Overlays
    # Infer or extract transit depth
    if transit_depth is not None:
        depth = float(transit_depth)
    else:
        # Measure empirical depth near phase 0
        in_transit = np.abs(phase) < 0.05
        if np.any(in_transit):
            depth = float(max(0.0005, 1.0 - np.percentile(flux[in_transit], 5)))
        else:
            depth = 0.01

    model_phase_grid = np.linspace(-0.5, 0.5, 500)

    # Model A: Symmetric Mandel-Agol / trapezoidal baseline
    y_symmetric = symmetric_trapezoid_transit(
        phase=model_phase_grid,
        period=p,
        depth=depth * 0.85,
        duration_phase=0.06,
        ingress_ratio=0.25,
    )

    # Model B: Asymmetric Cometary Dust Tail Model
    y_dust_tail = cometary_extinction_profile(
        model_phase_grid,
        depth=depth,
        sigma_ing=0.005,
        lambda_tail=0.045,
        alpha=1.0,
        phi_offset=0.012,
        f_scat=0.0008,
        phi_scat=-0.02,
        sigma_scat=0.007,
    )

    # Model C: Exomoon Perturbed Transit Profile (Primary + secondary dip)
    y_exomoon = np.ones_like(model_phase_grid)
    # Primary planetary dip
    y_exomoon -= depth * np.exp(-0.5 * (model_phase_grid / 0.018) ** 2)
    # Auxiliary exomoon shoulder dip shifted by +0.025 phase
    y_exomoon -= (depth * 0.15) * np.exp(-0.5 * ((model_phase_grid - 0.025) / 0.009) ** 2)

    # Compute asymmetry parameter
    asymmetry_val = compute_asymmetry_parameter(
        bin_centers, bin_flux, baseline=1.0, phase_window=(-0.15, 0.15)
    )

    return {
        "target_id": lc.target_id,
        "period": p,
        "t0": t_zero,
        "folded": folded,
        "raw_time": t_raw,
        "raw_flux": f_raw,
        "raw_flux_err": fe_raw,
        "folded_phase": phase,
        "folded_flux": flux,
        "binned_phase": bin_centers,
        "binned_flux": bin_flux,
        "binned_err": bin_err,
        "model_phase": model_phase_grid,
        "model_symmetric": y_symmetric,
        "model_dust_tail": y_dust_tail,
        "model_exomoon": y_exomoon,
        "asymmetry_parameter": float(asymmetry_val),
        "peak_depth": float(depth),
    }


def build_lightcurve_figure(
    plot_data: Dict[str, Any],
    view_mode: str = "folded",
    active_models: Optional[List[str]] = None,
) -> Any:
    """Build interactive Plotly figure (or Matplotlib fallback) for light curve."""
    try:
        import plotly.graph_objects as go
        from plotly.subplots import make_subplots

        if view_mode == "raw":
            fig = go.Figure()
            fig.add_trace(
                go.Scatter(
                    x=plot_data["raw_time"],
                    y=plot_data["raw_flux"],
                    mode="markers",
                    marker=dict(size=3, color="rgba(70, 130, 180, 0.7)"),
                    name="Observed Flux",
                )
            )
            fig.update_layout(
                title=f"Time Series Photometry — {plot_data['target_id']}",
                xaxis_title="Time (BKJD / BTJD)",
                yaxis_title="Normalized Relative Flux",
                template="plotly_dark",
                hovermode="closest",
                margin=dict(l=40, r=40, t=50, b=40),
            )
            return fig

        # Phase-folded mode with model overlays and residual subplot
        fig = make_subplots(
            rows=2,
            cols=1,
            shared_xaxes=True,
            vertical_spacing=0.08,
            row_heights=[0.75, 0.25],
            subplot_titles=("Detrended Phase-Folded Profile", "Residuals (O - C)"),
        )

        # 1. Raw folded cadences (light background scatter)
        fig.add_trace(
            go.Scatter(
                x=plot_data["folded_phase"],
                y=plot_data["folded_flux"],
                mode="markers",
                marker=dict(size=2.5, color="rgba(120, 140, 160, 0.3)"),
                name="Cadences",
            ),
            row=1,
            col=1,
        )

        # 2. Phase-binned flux with error bars
        fig.add_trace(
            go.Scatter(
                x=plot_data["binned_phase"],
                y=plot_data["binned_flux"],
                error_y=dict(
                    type="data",
                    array=plot_data["binned_err"],
                    visible=True,
                    color="white",
                    thickness=1,
                ),
                mode="markers",
                marker=dict(size=6, color="#00e5ff", symbol="circle"),
                name="Inverse-Var Binned",
            ),
            row=1,
            col=1,
        )

        models = active_models or ["symmetric", "dust_tail", "exomoon"]

        # 3. Model Overlays
        if "symmetric" in models:
            fig.add_trace(
                go.Scatter(
                    x=plot_data["model_phase"],
                    y=plot_data["model_symmetric"],
                    mode="lines",
                    line=dict(color="#ff5252", width=2.5, dash="dash"),
                    name="Symmetric Baseline (Mandel-Agol)",
                ),
                row=1,
                col=1,
            )

        if "dust_tail" in models:
            fig.add_trace(
                go.Scatter(
                    x=plot_data["model_phase"],
                    y=plot_data["model_dust_tail"],
                    mode="lines",
                    line=dict(color="#ffab00", width=3),
                    name="Cometary Dust Tail (Rappaport/Brogi)",
                ),
                row=1,
                col=1,
            )

        if "exomoon" in models:
            fig.add_trace(
                go.Scatter(
                    x=plot_data["model_phase"],
                    y=plot_data["model_exomoon"],
                    mode="lines",
                    line=dict(color="#b388ff", width=2.5, dash="dot"),
                    name="Exomoon Mutual Perturbation",
                ),
                row=1,
                col=1,
            )

        # 4. Residuals panel (Binned Flux - Dust Tail Model interpolated)
        y_model_binned = np.interp(
            plot_data["binned_phase"],
            plot_data["model_phase"],
            plot_data["model_dust_tail"],
        )
        res = plot_data["binned_flux"] - y_model_binned
        fig.add_trace(
            go.Scatter(
                x=plot_data["binned_phase"],
                y=res,
                mode="markers",
                marker=dict(size=5, color="#ffab00"),
                name="Residuals",
            ),
            row=2,
            col=1,
        )
        # Zero residual line
        fig.add_hline(y=0.0, line_width=1, line_dash="solid", line_color="gray", row=2, col=1)

        fig.update_layout(
            title=f"Transit Profile & Model Overlays — {plot_data['target_id']}",
            xaxis2_title="Orbital Phase φ (Transit Center = 0.0)",
            yaxis_title="Normalized Flux",
            yaxis2_title="Flux Δ",
            xaxis_range=[-0.25, 0.25],
            xaxis2_range=[-0.25, 0.25],
            template="plotly_dark",
            legend=dict(orientation="h", yanchor="bottom", y=1.02, xanchor="right", x=1.0),
            margin=dict(l=40, r=40, t=60, b=40),
            height=600,
        )
        return fig

    except ImportError:
        return plot_data


def render_lightcurve_view(state: Any) -> None:
    """Streamlit UI component rendering the Light Curve & Transit Profile Inspector."""
    import streamlit as st
    from frontier_astronomy.dashboard.state import load_candidate_light_curve

    cand = state.get_selected_candidate()
    if cand is None:
        st.warning("No candidate target selected.")
        return

    st.subheader(f"📈 Light Curve & Transit Inspector — {cand.name} ({cand.id})")

    col1, col2, col3, col4 = st.columns(4)
    col1.metric("Orbital Period", f"{cand.period:.5f} d")
    col2.metric("Transit Epoch (T0)", f"{cand.t0:.4f}")
    col3.metric("Transit Depth", f"{cand.depth_ppm:,.0f} ppm")
    col4.metric("Morphological Asymmetry", f"{cand.asymmetry:.3f}")

    # Controls
    ctrl_col1, ctrl_col2, ctrl_col3 = st.columns([2, 2, 3])
    with ctrl_col1:
        view_mode = st.radio("Display Mode", ["Phase-Folded Profile", "Raw Time-Series"], horizontal=True)
    with ctrl_col2:
        model_options = st.multiselect(
            "Model Overlays",
            ["symmetric", "dust_tail", "exomoon"],
            default=["symmetric", "dust_tail", "exomoon"],
        )
    with ctrl_col3:
        phase_zoom = st.slider("Phase Zoom Window", 0.05, 0.50, 0.25, 0.05)

    # Load light curve
    with st.spinner(f"Loading photometric cadences for {cand.id}..."):
        try:
            lc = load_candidate_light_curve(cand.id, mission=cand.mission)
            plot_data = format_lightcurve_plot_data(
                lc,
                period=cand.period,
                t0=cand.t0,
                transit_depth=cand.depth_ppm / 1e6,
            )
            fig = build_lightcurve_figure(
                plot_data,
                view_mode="raw" if view_mode == "Raw Time-Series" else "folded",
                active_models=model_options,
            )

            if hasattr(fig, "update_layout"):
                if view_mode != "Raw Time-Series":
                    fig.update_layout(xaxis_range=[-phase_zoom, phase_zoom], xaxis2_range=[-phase_zoom, phase_zoom])
                st.plotly_chart(fig, use_container_width=True)
            else:
                st.dataframe(plot_data)

        except Exception as e:
            st.error(f"Error rendering light curve view: {e}")
