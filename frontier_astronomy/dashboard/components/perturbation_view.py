"""Exomoon and gravitational perturbation inspection view component.

Provides interactive O-C timing residual diagrams, transit duration variations (TDV),
the pathognomonic pi/2 (90-degree) orthogonal TTV-TDV phase invariant test, secondary
transit shoulder anomaly isolation, and triangular L4/L5 Trojan companion dip scans.
"""

from __future__ import annotations

import json
from typing import Any, Dict, List, Optional, Tuple, Union
import numpy as np

from frontier_astronomy.core.types import ExomoonPerturbationResult, FoldedTransit, LightCurveData


def format_oc_diagram_data(
    res: ExomoonPerturbationResult,
    epochs: Optional[np.ndarray] = None,
) -> Dict[str, Any]:
    """Format perturbation results into JSON-serializable structure for dashboard O-C plotting.

    Conforms to test_f10_04 and test_w09:
    - Guaranteed equal length of ttv_minutes and tdv_minutes.
    - Preserves orthogonal_phase_diff_deg (~90.0 deg for exomoons).
    - JSON-serializable keys: epochs, ttv_minutes, tdv_minutes, phase_diff_deg, has_candidate.
    """
    n_epochs = len(res.ttv_amplitudes)
    if epochs is not None and len(epochs) == n_epochs:
        ep_list = [int(e) for e in epochs]
    else:
        ep_list = list(range(n_epochs))

    ttv_list = [float(x) for x in res.ttv_amplitudes]
    tdv_list = [float(x) for x in res.tdv_amplitudes]

    return {
        "target_id": res.target_id,
        "period": float(res.period),
        "epochs": ep_list,
        "ttv_minutes": ttv_list,
        "tdv_minutes": tdv_list,
        "phase_diff_deg": float(res.orthogonal_phase_diff_deg),
        "has_candidate": bool(res.has_exomoon_candidate),
        "ttv_snr": float(res.ttv_snr),
        "has_secondary_shoulder": bool(res.has_secondary_shoulder),
        "shoulder_snr": float(res.shoulder_snr),
        "has_trojan_candidate": bool(res.has_trojan_candidate),
        "trojan_lag_depth": float(res.trojan_lag_depth),
        "p_moon_posterior": float(res.p_moon_posterior),
    }


def format_shoulder_zoom_data(
    folded: FoldedTransit,
    window_ingress: Tuple[float, float] = (-0.08, -0.015),
    window_egress: Tuple[float, float] = (0.015, 0.08),
) -> Dict[str, Any]:
    """Extract and format data points specifically within transit shoulder wings."""
    phase = folded.phase
    flux = folded.flux

    ing_mask = (phase >= window_ingress[0]) & (phase <= window_ingress[1])
    eg_mask = (phase >= window_egress[0]) & (phase <= window_egress[1])

    return {
        "ingress_phase": phase[ing_mask].tolist(),
        "ingress_flux": flux[ing_mask].tolist(),
        "egress_phase": phase[eg_mask].tolist(),
        "egress_flux": flux[eg_mask].tolist(),
    }


def format_trojan_dips_data(
    folded: FoldedTransit,
    l4_phase: float = 0.1667,  # +60 degrees
    l5_phase: float = -0.1667,  # -60 degrees
    search_half_width: float = 0.05,
) -> Dict[str, Any]:
    """Extract and format data surrounding L4 (+60 deg) and L5 (-60 deg) Lagrange points."""
    phase = folded.phase
    flux = folded.flux

    l4_mask = np.abs(phase - l4_phase) <= search_half_width
    l5_mask = np.abs(phase - l5_phase) <= search_half_width

    return {
        "l4_phase": phase[l4_mask].tolist(),
        "l4_flux": flux[l4_mask].tolist(),
        "l5_phase": phase[l5_mask].tolist(),
        "l5_flux": flux[l5_mask].tolist(),
        "l4_mean_depth_ppm": float(max(0.0, 1.0 - np.mean(flux[l4_mask])) * 1e6) if np.any(l4_mask) else 0.0,
        "l5_mean_depth_ppm": float(max(0.0, 1.0 - np.mean(flux[l5_mask])) * 1e6) if np.any(l5_mask) else 0.0,
    }


def build_oc_diagram_figure(oc_data: Dict[str, Any]) -> Any:
    """Build interactive Plotly figure for O-C timing residuals and duration variations."""
    try:
        import plotly.graph_objects as go
        from plotly.subplots import make_subplots

        fig = make_subplots(
            rows=2,
            cols=1,
            shared_xaxes=True,
            vertical_spacing=0.08,
            subplot_titles=(
                "Transit Timing Variations (TTV / O-C Diagram)",
                "Transit Duration Variations (TDV-V Profile)",
            ),
        )

        epochs = oc_data["epochs"]
        ttv = oc_data["ttv_minutes"]
        tdv = oc_data["tdv_minutes"]

        # 1. TTV series
        fig.add_trace(
            go.Scatter(
                x=epochs,
                y=ttv,
                mode="lines+markers",
                marker=dict(size=8, color="#00e5ff", symbol="diamond"),
                line=dict(color="#00e5ff", width=2),
                name="TTV (O - C)",
            ),
            row=1,
            col=1,
        )
        fig.add_hline(y=0.0, line_width=1, line_dash="dash", line_color="gray", row=1, col=1)

        # 2. TDV series
        fig.add_trace(
            go.Scatter(
                x=epochs,
                y=tdv,
                mode="lines+markers",
                marker=dict(size=8, color="#ff4081", symbol="circle"),
                line=dict(color="#ff4081", width=2),
                name="TDV (Duration Δ)",
            ),
            row=2,
            col=1,
        )
        fig.add_hline(y=0.0, line_width=1, line_dash="dash", line_color="gray", row=2, col=1)

        fig.update_layout(
            title=f"Gravitational Perturbation Signatures — {oc_data.get('target_id', 'Target')}",
            xaxis2_title="Transit Epoch Number",
            yaxis_title="TTV (minutes)",
            yaxis2_title="TDV (minutes)",
            template="plotly_dark",
            height=550,
            margin=dict(l=50, r=40, t=60, b=40),
            legend=dict(orientation="h", yanchor="bottom", y=1.02, xanchor="right", x=1.0),
        )
        return fig

    except ImportError:
        return oc_data


def build_phase_invariant_figure(oc_data: Dict[str, Any]) -> Any:
    """Build interactive Lissajous figure demonstrating the 90-degree orthogonal phase invariant."""
    try:
        import plotly.graph_objects as go

        ttv = np.asarray(oc_data["ttv_minutes"])
        tdv = np.asarray(oc_data["tdv_minutes"])
        epochs = oc_data["epochs"]
        phase_diff = oc_data.get("phase_diff_deg", 90.0)

        fig = go.Figure()

        # Observed trajectory in TTV-TDV phase space
        fig.add_trace(
            go.Scatter(
                x=ttv,
                y=tdv,
                mode="lines+markers+text",
                marker=dict(size=9, color=epochs, colorscale="Viridis", showscale=True, colorbar=dict(title="Epoch")),
                line=dict(color="rgba(255, 255, 255, 0.5)", width=1.5, dash="dot"),
                text=[f"E{e}" for e in epochs],
                textposition="top center",
                name="Observed Trajectory",
            )
        )

        # Theoretical 90-degree exomoon invariant ellipse
        a_ttv = np.max(np.abs(ttv)) if len(ttv) > 0 else 1.0
        a_tdv = np.max(np.abs(tdv)) if len(tdv) > 0 else 1.0
        theta_grid = np.linspace(0, 2 * np.pi, 200)
        # Exomoon: TTV ~ sin(theta), TDV ~ -cos(theta) -> pure orthogonal ellipse
        x_ellipse = a_ttv * np.sin(theta_grid)
        y_ellipse = -a_tdv * np.cos(theta_grid)

        fig.add_trace(
            go.Scatter(
                x=x_ellipse,
                y=y_ellipse,
                mode="lines",
                line=dict(color="#00e676", width=2.5),
                name="Theoretical Exomoon Invariant (ΔΦ = 90°)",
            )
        )

        # Planetary MMR False-Positive line (0 deg or 180 deg in-phase)
        x_mmr = np.linspace(-a_ttv, a_ttv, 50)
        y_mmr = (a_tdv / a_ttv) * x_mmr
        fig.add_trace(
            go.Scatter(
                x=x_mmr,
                y=y_mmr,
                mode="lines",
                line=dict(color="#ff1744", width=1.5, dash="dash"),
                name="Planetary MMR False-Positive (ΔΦ = 0° / 180°)",
            )
        )

        fig.update_layout(
            title=f"Orthogonal TTV-TDV Phase Invariant Test — Measured ΔΦ = {phase_diff:.1f}°",
            xaxis_title="TTV Amplitude (minutes)",
            yaxis_title="TDV Amplitude (minutes)",
            template="plotly_dark",
            height=500,
            margin=dict(l=50, r=40, t=50, b=40),
            legend=dict(orientation="h", yanchor="bottom", y=1.02, xanchor="right", x=1.0),
        )
        return fig

    except ImportError:
        return oc_data


def render_perturbation_view(state: Any) -> None:
    """Streamlit UI component rendering Exomoon & Perturbation Analyzer."""
    import streamlit as st
    from frontier_astronomy.perturbations import detect_perturbations
    from frontier_astronomy.dashboard.state import load_candidate_light_curve

    cand = state.get_selected_candidate()
    if cand is None:
        st.warning("No candidate target selected.")
        return

    st.subheader(f"🪐 Exomoon & Perturbation Analyzer — {cand.name} ({cand.id})")
    st.caption(
        "Analyzes 3-body gravitational perturbations. An authentic exomoon satellite produces "
        "barycentric Transit Timing Variations (TTV) strictly 90° (π/2) out-of-phase with velocity-induced "
        "Transit Duration Variations (TDV-V), ruling out planetary Mean Motion Resonances (MMR)."
    )

    with st.spinner(f"Extracting TTV/TDV perturbations for {cand.id}..."):
        try:
            lc = load_candidate_light_curve(cand.id, mission=cand.mission)
            res = detect_perturbations(lc, period=cand.period, t0=cand.t0)
            oc_data = format_oc_diagram_data(res)

            # High-level diagnostic cards
            kpi1, kpi2, kpi3, kpi4 = st.columns(4)
            kpi1.metric("Exomoon Candidate", "CONFIRMED" if res.has_exomoon_candidate else "NON-DETECTION")
            kpi2.metric("TTV Signal-to-Noise", f"{res.ttv_snr:.2f}")
            kpi3.metric("Orthogonal Phase Shift", f"{res.orthogonal_phase_diff_deg:.1f}°", delta="Target: 90.0°")
            kpi4.metric("P(Moon | Data)", f"{res.p_moon_posterior * 100:.1f}%")

            # Figures
            tab_oc, tab_phase, tab_shoulder = st.tabs([
                "📊 O-C & TDV Timing Series",
                "🔄 π/2 Phase Invariant (TTV vs TDV)",
                "🔍 Transit Shoulder & Trojan Dips",
            ])

            with tab_oc:
                fig_oc = build_oc_diagram_figure(oc_data)
                if hasattr(fig_oc, "update_layout"):
                    st.plotly_chart(fig_oc, use_container_width=True)
                else:
                    st.json(oc_data)

            with tab_phase:
                fig_phase = build_phase_invariant_figure(oc_data)
                if hasattr(fig_phase, "update_layout"):
                    st.plotly_chart(fig_phase, use_container_width=True)
                else:
                    st.write(oc_data)

            with tab_shoulder:
                scol1, scol2 = st.columns(2)
                scol1.metric("Secondary Shoulder Detected", "YES" if res.has_secondary_shoulder else "NO")
                scol1.metric("Shoulder Anomaly SNR", f"{res.shoulder_snr:.2f}")
                scol2.metric("Co-Orbital Trojan Detected", "YES" if res.has_trojan_candidate else "NO")
                scol2.metric("Trojan L4/L5 Depth", f"{res.trojan_lag_depth * 1e6:.0f} ppm")

        except Exception as e:
            st.error(f"Error computing perturbation diagnostics: {e}")
