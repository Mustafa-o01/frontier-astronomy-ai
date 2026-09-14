"""2D Localized Residual Anomaly Heatmap component.

Bins photometric residuals across transit epoch and orbital phase into a 2D matrix,
revealing orbit-to-orbit cometary dust clumping, depth variability, and transit timing
distortions at high signal-to-noise.
"""

from __future__ import annotations

from typing import Any, Dict, List, Optional, Tuple, Union
import numpy as np

from frontier_astronomy.core.types import LightCurveData
from frontier_astronomy.core.preprocessing import epoch_split, phase_fold


def compute_residual_heatmap(
    light_curve: LightCurveData,
    period: float,
    t0: float,
    n_phase_bins: int = 25,
    phase_range: Tuple[float, float] = (-0.2, 0.2),
    max_epochs: Optional[int] = None,
    baseline_flux: float = 1.0,
) -> Tuple[np.ndarray, np.ndarray, np.ndarray]:
    """Compute 2D matrix of flux residuals: rows = transit epoch, cols = orbital phase.

    Conforms to test_f10_03, test_f10_b04, and test_w08:
    - 2D binning of flux residuals across transit epoch and orbital phase.
    - Handles single epoch gracefully (yielding 1 x n_phase_bins array).
    - Guarantees zero NaNs in returned heatmap matrix.
    - Near phase 0, transit troughs exhibit negative residuals.
    """
    epochs = epoch_split(light_curve.time, period=period, t0=t0)
    phases = phase_fold(light_curve.time, period=period, t0=t0)
    residuals = light_curve.flux - baseline_flux

    unique_epochs = np.unique(epochs)
    if max_epochs is not None and len(unique_epochs) > max_epochs:
        unique_epochs = unique_epochs[:max_epochs]

    if len(unique_epochs) == 0:
        return np.zeros((0, n_phase_bins)), np.array([]), np.linspace(phase_range[0], phase_range[1], n_phase_bins)

    phase_edges = np.linspace(phase_range[0], phase_range[1], n_phase_bins + 1)
    phase_centers = 0.5 * (phase_edges[:-1] + phase_edges[1:])
    heatmap = np.zeros((len(unique_epochs), n_phase_bins), dtype=np.float64)

    for row_idx, ep in enumerate(unique_epochs):
        ep_mask = epochs == ep
        p_ep = phases[ep_mask]
        r_ep = residuals[ep_mask]

        for col_idx in range(n_phase_bins):
            p_mask = (p_ep >= phase_edges[col_idx]) & (p_ep < phase_edges[col_idx + 1])
            if np.any(p_mask):
                heatmap[row_idx, col_idx] = float(np.mean(r_ep[p_mask]))
            else:
                heatmap[row_idx, col_idx] = 0.0

    # Ensure hermetic non-NaN guarantee
    heatmap = np.nan_to_num(heatmap, nan=0.0)

    return heatmap, unique_epochs, phase_centers


def build_heatmap_figure(
    heatmap: np.ndarray,
    epochs: np.ndarray,
    phase_centers: np.ndarray,
    target_id: str = "Candidate",
    title: Optional[str] = None,
    colorscale: str = "RdBu",
) -> Any:
    """Build interactive Plotly 2D heatmap figure."""
    try:
        import plotly.graph_objects as go

        if heatmap.size == 0 or len(epochs) == 0:
            fig = go.Figure()
            fig.update_layout(
                title=title or f"2D Anomaly Heatmap — {target_id} (No In-Transit Epochs Available)",
                template="plotly_dark",
                height=450,
                annotations=[
                    dict(
                        text="No valid in-transit epochs found for the selected phase range.<br>Try adjusting the phase range or selecting another target.",
                        xref="paper",
                        yref="paper",
                        x=0.5,
                        y=0.5,
                        showarrow=False,
                        font=dict(size=14, color="#94a3b8"),
                    )
                ],
            )
            return fig

        # Symmetric color scale centered at 0.0
        vmax = max(1e-4, float(np.percentile(np.abs(heatmap), 98)))
        vmin = -vmax

        fig = go.Figure(
            data=go.Heatmap(
                z=heatmap,
                x=phase_centers,
                y=epochs,
                colorscale=colorscale,
                zmin=vmin,
                zmax=vmax,
                colorbar=dict(
                    title=dict(text="Flux Residual (ΔF)", side="right"),
                    tickformat=".3f",
                ),
                hoverongaps=False,
                hovertemplate="Epoch: %{y}<br>Phase φ: %{x:.3f}<br>Residual: %{z:.4f}<extra></extra>",
            )
        )

        fig.add_vline(x=0.0, line_width=1.5, line_dash="dash", line_color="#00e5ff")

        fig.update_layout(
            title=title or f"2D Anomaly Heatmap (Epoch vs Phase) — {target_id}",
            xaxis_title="Orbital Phase φ",
            yaxis_title="Transit Epoch Number",
            template="plotly_dark",
            height=520,
            margin=dict(l=50, r=40, t=50, b=40),
        )
        return fig

    except ImportError:
        return {
            "heatmap": heatmap.tolist(),
            "epochs": epochs.tolist(),
            "phase_centers": phase_centers.tolist(),
            "target_id": target_id,
        }


def render_heatmap_view(state: Any) -> None:
    """Streamlit UI component rendering Localized Residual Anomaly Heatmap."""
    import streamlit as st
    import plotly.graph_objects as go
    from frontier_astronomy.dashboard.state import load_candidate_light_curve

    cand = state.get_selected_candidate()
    if cand is None:
        st.warning("No candidate target selected.")
        return

    st.subheader(f"🗺️ Localized Residual Anomaly Heatmap — {cand.name} ({cand.id})")
    st.caption(
        "2D matrix showing photometric residuals across each observed transit epoch vs orbital phase. "
        "Asymmetric cometary dust clouds appear as extended troughs lagging the central transit axis (φ = 0)."
    )

    col1, col2, col3, col4 = st.columns(4)
    with col1:
        n_bins = st.slider("Phase Bins", 15, 60, 30, 5)
    with col2:
        max_ep = st.slider("Max Epochs", 5, 100, 25, 5)
    with col3:
        phase_span = st.slider("Phase Span (±)", 0.05, 0.30, 0.18, 0.01)
    with col4:
        c_scale = st.selectbox("Colormap", ["RdBu", "Viridis", "Plasma", "Inferno", "Turbo"], index=0)

    with st.spinner(f"Computing 2D residual matrix for {cand.id}..."):
        try:
            lc = load_candidate_light_curve(cand.id, mission=cand.mission)
            heatmap, epochs, phase_centers = compute_residual_heatmap(
                lc,
                period=cand.period,
                t0=cand.t0,
                n_phase_bins=n_bins,
                phase_range=(-phase_span, phase_span),
                max_epochs=max_ep,
            )

            fig = build_heatmap_figure(heatmap, epochs, phase_centers, target_id=cand.id, colorscale=c_scale)
            if hasattr(fig, "update_layout"):
                st.plotly_chart(fig, use_container_width=True)
            else:
                st.write(fig)

            # Metrics & Diagnostics row below heatmap
            m1, m2, m3, m4 = st.columns(4)
            m1.metric("Observed Epochs", f"{len(epochs)}")
            if len(epochs) > 0 and heatmap.shape[0] > 0 and heatmap.shape[1] > 0:
                mid_col = len(phase_centers) // 2
                mean_center_depth = float(np.mean(heatmap[:, mid_col]))
                var_depth = float(np.var(np.min(heatmap, axis=1))) if len(epochs) > 1 else 0.0
                mean_profile = np.mean(heatmap, axis=0)
                asym_est = float(np.mean(mean_profile[mid_col:]) - np.mean(mean_profile[:mid_col]))
            else:
                mean_center_depth = 0.0
                var_depth = 0.0
                mean_profile = np.zeros(len(phase_centers))
                asym_est = 0.0

            m2.metric("Mean In-Transit Residual", f"{mean_center_depth * 1e6:,.0f} ppm")
            m3.metric("Transit Depth Variance", f"{var_depth * 1e6:.2f} ppm²")
            m4.metric("Egress vs Ingress Drift", f"{asym_est * 1e6:+,.0f} ppm")

            # 1D Stacked Epoch-Averaged Residual Profile
            if len(epochs) > 0:
                with st.expander("📈 View 1D Stacked Epoch-Averaged Profile (Asymmetry Diagnostic)", expanded=True):
                    fig_1d = go.Figure()
                    fig_1d.add_trace(
                        go.Scatter(
                            x=phase_centers,
                            y=mean_profile,
                            mode="lines+markers",
                            line=dict(color="#00f2fe", width=2.5),
                            marker=dict(size=5, color="#00f2fe"),
                            name="Stacked Epoch Mean",
                        )
                    )
                    fig_1d.add_hline(y=0.0, line_dash="dash", line_color="gray")
                    fig_1d.add_vline(x=0.0, line_dash="dot", line_color="#ff1744", annotation_text="Center φ = 0")
                    fig_1d.update_layout(
                        title=f"1D Stacked Average Residual Profile across {len(epochs)} Epochs",
                        xaxis_title="Orbital Phase φ",
                        yaxis_title="Mean Residual Flux (ΔF)",
                        template="plotly_dark",
                        height=280,
                        margin=dict(l=40, r=40, t=40, b=30),
                    )
                    st.plotly_chart(fig_1d, use_container_width=True)

        except Exception as e:
            st.error(f"Error computing residual anomaly heatmap: {e}")
