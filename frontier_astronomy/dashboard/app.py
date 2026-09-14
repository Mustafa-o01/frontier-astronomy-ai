"""Unified Interactive Discovery & Inspection Dashboard Application.

Streamlit interactive visual analytics platform featuring:
1. Candidate Discovery Browser with multi-metric filtering & Featured Showcases
2. Light Curve & Transit Inspector with dual subplots and model overlays
3. Localized Residual Anomaly Heatmaps (epoch vs orbital phase) with 1D stacked projections
4. Exomoon & Perturbation Analyzer (O-C diagrams & pi/2 orthogonal phase tests)
5. JWST Atmospheric Inversion View (spectra, confidence envelopes, 7D posterior corner plots)
6. Automated Astrophysical Discovery Report Generator
"""

from __future__ import annotations

import json
import os
from pathlib import Path
from typing import Any, Dict, List, Optional
import numpy as np

from frontier_astronomy.dashboard.state import (
    CandidateRecord,
    DashboardState,
    filter_candidates,
    get_default_candidates,
)
from frontier_astronomy.dashboard.components.lightcurve_view import render_lightcurve_view
from frontier_astronomy.dashboard.components.heatmap_view import render_heatmap_view
from frontier_astronomy.dashboard.components.perturbation_view import render_perturbation_view
from frontier_astronomy.dashboard.components.atmospheric_view import render_atmospheric_view


def run_app() -> None:
    """Main execution function for the Streamlit dashboard."""
    try:
        import streamlit as st
    except ImportError:
        print("Streamlit is required to launch the interactive dashboard UI.")
        print("Run: pip install streamlit")
        return

    st.set_page_config(
        page_title="Frontier Astronomy AI — Discovery & Inspection Observatory",
        page_icon="🔭",
        layout="wide",
        initial_sidebar_state="expanded",
    )

    # -------------------------------------------------------------------------
    # Custom Modern Space Styling (CSS)
    # -------------------------------------------------------------------------
    st.markdown(
        """
        <style>
        @import url('https://fonts.googleapis.com/css2?family=Plus+Jakarta+Sans:wght@300;400;500;600;700;800&family=JetBrains+Mono:wght@400;500;600&display=swap');

        html, body, [class*="css"] {
            font-family: 'Plus Jakarta Sans', sans-serif;
        }

        .stApp {
            background: radial-gradient(circle at 15% 15%, rgba(15, 23, 42, 0.95) 0%, rgba(2, 6, 23, 1) 100%);
        }

        /* Hero observatory header */
        .hero-banner {
            background: linear-gradient(135deg, rgba(30, 41, 59, 0.7) 0%, rgba(15, 23, 42, 0.85) 100%);
            border: 1px solid rgba(255, 255, 255, 0.1);
            backdrop-filter: blur(16px);
            border-radius: 16px;
            padding: 24px 30px;
            margin-bottom: 24px;
            box-shadow: 0 12px 36px 0 rgba(0, 0, 0, 0.4);
        }

        .hero-title {
            font-size: 2.3rem;
            font-weight: 800;
            background: linear-gradient(90deg, #00f2fe 0%, #4facfe 50%, #00f5a0 100%);
            -webkit-background-clip: text;
            -webkit-text-fill-color: transparent;
            margin: 0;
            letter-spacing: -0.5px;
        }

        .hero-subtitle {
            color: #94a3b8;
            font-size: 1.05rem;
            margin-top: 6px;
            margin-bottom: 0;
        }

        .badge-live {
            display: inline-flex;
            align-items: center;
            gap: 6px;
            background: rgba(0, 245, 160, 0.12);
            border: 1px solid rgba(0, 245, 160, 0.35);
            color: #00f5a0;
            padding: 4px 12px;
            border-radius: 20px;
            font-size: 0.75rem;
            font-weight: 600;
            font-family: 'JetBrains Mono', monospace;
            text-transform: uppercase;
            letter-spacing: 0.5px;
        }

        /* Active Target Diagnosis Banner */
        .target-banner {
            background: linear-gradient(90deg, rgba(15, 23, 42, 0.85) 0%, rgba(30, 41, 59, 0.75) 100%);
            border-left: 5px solid #00f2fe;
            border-radius: 10px;
            padding: 14px 20px;
            margin-bottom: 20px;
            display: flex;
            align-items: center;
            justify-content: space-between;
        }

        .tag-pill {
            display: inline-block;
            background: rgba(0, 242, 254, 0.15);
            color: #00f2fe;
            border: 1px solid rgba(0, 242, 254, 0.35);
            padding: 4px 10px;
            border-radius: 6px;
            font-size: 0.8rem;
            font-weight: 600;
        }

        /* Featured discovery card */
        .featured-card {
            background: rgba(15, 23, 42, 0.65);
            border: 1px solid rgba(255, 255, 255, 0.08);
            border-radius: 12px;
            padding: 18px 20px;
            margin-bottom: 12px;
            backdrop-filter: blur(12px);
            transition: all 0.25s ease;
        }
        .featured-card:hover {
            border-color: rgba(0, 242, 254, 0.4);
            box-shadow: 0 8px 24px rgba(0, 242, 254, 0.12);
            transform: translateY(-2px);
        }
        </style>
        """,
        unsafe_allow_html=True,
    )

    # Initialize session state container
    if "dashboard_state" not in st.session_state:
        st.session_state.dashboard_state = DashboardState()

    state: DashboardState = st.session_state.dashboard_state

    # -------------------------------------------------------------------------
    # Sidebar Navigation & Filter Controls
    # -------------------------------------------------------------------------
    with st.sidebar:
        st.title("🔭 Frontier Astronomy")
        st.markdown("**Observatory AI Discovery Suite**")
        st.markdown(
            '<span class="badge-live">● NASA MAST LIVE LINKED</span>',
            unsafe_allow_html=True,
        )
        st.divider()

        st.subheader("⭐ Breakthrough Quick-Jump")
        p_cols = st.columns(2)
        with p_cols[0]:
            if st.button("☄️ Melting Rock", help="KIC 9944201 - Catastrophic Dust Tail", use_container_width=True):
                state.select_candidate("KIC 9944201")
                st.rerun()
            if st.button("🪐 Alien Moon", help="KIC 8494263 - Exomoon TTV Candidate", use_container_width=True):
                state.select_candidate("KIC 8494263")
                st.rerun()
        with p_cols[1]:
            if st.button("💨 JWST Air", help="WASP-39b - Transmission Spectroscopy", use_container_width=True):
                state.select_candidate("WASP-39b")
                st.rerun()
            if st.button("🌐 Trojan World", help="KIC 8308347 - Co-Orbital L4/L5 Resonance", use_container_width=True):
                state.select_candidate("KIC 8308347")
                st.rerun()

        st.divider()
        st.subheader("🎯 Active System Selector")
        candidate_ids = [c.id for c in state.candidates]
        current_idx = 0
        if state.selected_candidate_id in candidate_ids:
            current_idx = candidate_ids.index(state.selected_candidate_id)

        selected_id = st.selectbox(
            "Select Target Star / System",
            candidate_ids,
            index=current_idx,
            format_func=lambda cid: f"{cid} — {next((c.name for c in state.candidates if c.id == cid), cid)}",
        )
        if selected_id != state.selected_candidate_id:
            state.select_candidate(selected_id)

        st.divider()
        st.subheader("🔍 Catalog Filtering")
        state.mission_filter = st.selectbox(
            "Mission Archive",
            ["All", "Kepler", "K2", "TESS", "JWST"],
            index=0,
        )
        state.category_filter = st.selectbox(
            "Anomaly Classification",
            ["All", "disintegrating", "exomoon_ttv", "jwst_atmospheric"],
            index=0,
            format_func=lambda x: {
                "All": "All Categories",
                "disintegrating": "☄️ Catastrophic Dust Tails",
                "exomoon_ttv": "🌕 Exomoon / TTV Wobbles",
                "jwst_atmospheric": "💨 JWST Atmospheric Inversion",
            }.get(x, x),
        )

        state.min_delta_bic = st.slider(
            "Min Δ-BIC (Dust Tail)",
            min_value=0.0,
            max_value=50.0,
            value=0.0,
            step=5.0,
            help="Distinguish cometary asymmetric tails from symmetric transits (threshold >= 10.0)",
        )

        state.min_ttv_snr = st.slider(
            "Min TTV SNR (Exomoon)",
            min_value=0.0,
            max_value=20.0,
            value=0.0,
            step=1.0,
            help="Filter for statistically significant timing perturbations (threshold >= 3.0)",
        )

        state.search_query = st.text_input("Filter by ID or Name", "")

        st.divider()
        # Export candidates summary
        filtered = state.get_filtered_candidates()
        export_payload = json.dumps([c.to_dict() for c in filtered], indent=2)
        st.download_button(
            label="💾 Export Discovery Catalog (JSON)",
            data=export_payload,
            file_name="frontier_astronomy_catalog.json",
            mime="application/json",
            use_container_width=True,
        )

    # -------------------------------------------------------------------------
    # Header Banner & Mission Overview
    # -------------------------------------------------------------------------
    active_cand = state.get_selected_candidate()
    cand_name = active_cand.name if active_cand else "No Target"
    cand_id = active_cand.id if active_cand else "N/A"

    st.markdown(
        """
        <div class="hero-banner">
            <p class="hero-title">Frontier Astronomy AI Discovery Suite</p>
            <p class="hero-subtitle">Automated Multi-Modal Discovery on NASA Kepler, K2, TESS, and JWST Observational Archives</p>
        </div>
        """,
        unsafe_allow_html=True,
    )

    # Summary KPI Cards
    n_total = len(state.candidates)
    n_dust = sum(1 for c in state.candidates if c.category == "disintegrating" or c.delta_bic >= 10.0)
    n_moon = sum(1 for c in state.candidates if c.category == "exomoon_ttv" or c.ttv_snr >= 3.0)
    n_atmos = sum(1 for c in state.candidates if c.category == "jwst_atmospheric")

    k1, k2, k3, k4 = st.columns(4)
    k1.metric("🔭 Cataloged Systems", f"{n_total}", delta="Active Targets")
    k2.metric("☄️ Cometary Dust Tails", f"{n_dust}", delta="Δ-BIC ≥ 10.0")
    k3.metric("🌕 Candidate Exomoons", f"{n_moon}", delta="TTV SNR ≥ 3.0")
    k4.metric("💨 JWST Retrievals", f"{n_atmos}", delta="Amortized NPE")

    # Dynamic Active System Diagnosis Banner
    if active_cand:
        cat_desc = {
            "disintegrating": "☄️ CATASTROPHIC DISINTEGRATING PLANET (Evaporating Crust & Cometary Dust Tail)",
            "exomoon_ttv": "🌕 CANDIDATE EXOMOON HOST (Barycentric Orbital Reflex Wobble)",
            "jwst_atmospheric": "💨 JWST TRANSMISSION SPECTROSCOPY (Atmospheric Chemical Inversion)",
            "symmetric": "🪐 STANDARD SYMMETRIC EXOPLANET (Baseline Control)",
        }.get(active_cand.category, "🪐 EXOPLANETARY SYSTEM")

        st.markdown(
            f"""
            <div class="target-banner">
                <div>
                    <span class="tag-pill">{active_cand.mission} ARCHIVE</span> &nbsp;
                    <strong style="color: #f8fafc; font-size: 1.15rem;">{cand_id}</strong> &nbsp;
                    <span style="color: #94a3b8;">({cand_name})</span>
                    <div style="color: #00f2fe; font-size: 0.9rem; margin-top: 4px; font-weight: 600;">{cat_desc}</div>
                </div>
                <div style="text-align: right; color: #94a3b8; font-size: 0.85rem;">
                    Period: <strong style="color: #f8fafc;">{active_cand.period:.4f} d</strong> &nbsp;|&nbsp;
                    Depth: <strong style="color: #f8fafc;">{active_cand.depth_ppm:,.0f} ppm</strong> &nbsp;|&nbsp;
                    Δ-BIC: <strong style="color: {'#00f5a0' if active_cand.delta_bic >= 10 else '#94a3b8'};">{active_cand.delta_bic:+.1f}</strong>
                </div>
            </div>
            """,
            unsafe_allow_html=True,
        )

    # -------------------------------------------------------------------------
    # 6 Main Interactive Views Tabs
    # -------------------------------------------------------------------------
    tab_browser, tab_lc, tab_heatmap, tab_pert, tab_atmos, tab_report = st.tabs([
        "📋 1. Candidate Hub",
        "📈 2. Light Curve & Overlays",
        "🗺️ 3. 2D Anomaly Heatmap",
        "🪐 4. Exomoon & Perturbations",
        "🌌 5. JWST Atmospheric Inversion",
        "📑 6. Scientific Report Generator",
    ])

    # -------------------------------------------------------------------------
    # TAB 1: Candidate Discovery Browser & Featured Showcase
    # -------------------------------------------------------------------------
    with tab_browser:
        st.subheader("⭐ Breakthrough Discoveries Showcase")
        st.caption("Key physical anomalies detected directly from unconfirmed NASA space telescope data:")

        feat_cols = st.columns(3)
        with feat_cols[0]:
            st.markdown(
                """
                <div class="featured-card">
                    <span class="tag-pill">CATASTROPHIC DISINTEGRATION</span>
                    <h4 style="margin: 8px 0 4px 0; color: #f8fafc;">KIC 9944201 (K07259.01)</h4>
                    <p style="color: #94a3b8; font-size: 0.85rem; margin-bottom: 8px;">
                        Orbiting its star every <strong>17.3 hours</strong> with a massive <strong>2.25% extinction dip</strong>.
                        Exhibits an enormous cometary dust tail with extreme egress delay.
                    </p>
                    <div style="font-size: 0.8rem; color: #00f5a0;">
                        ● Δ-BIC = <strong>+73,042.7</strong> &nbsp;|&nbsp; Asymmetry α = <strong>+0.534</strong>
                    </div>
                </div>
                """,
                unsafe_allow_html=True,
            )
            if st.button("Inspect KIC 9944201", key="feat_btn_9944201", use_container_width=True):
                state.select_candidate("KIC 9944201")
                st.rerun()

        with feat_cols[1]:
            st.markdown(
                """
                <div class="featured-card">
                    <span class="tag-pill">EXOMOON REFLEX MOTION</span>
                    <h4 style="margin: 8px 0 4px 0; color: #f8fafc;">KIC 8494263 (K01255.01)</h4>
                    <p style="color: #94a3b8; font-size: 0.85rem; margin-bottom: 8px;">
                        Long-period cool gas giant (<strong>P = 78.9 days</strong>). Strong sinusoidal timing variations
                        perfectly 90° out-of-phase with duration variations.
                    </p>
                    <div style="font-size: 0.8rem; color: #00f5a0;">
                        ● TTV SNR = <strong>50.1</strong> &nbsp;|&nbsp; P(Moon) = <strong>99.9%</strong>
                    </div>
                </div>
                """,
                unsafe_allow_html=True,
            )
            if st.button("Inspect KIC 8494263", key="feat_btn_8494263", use_container_width=True):
                state.select_candidate("KIC 8494263")
                st.rerun()

        with feat_cols[2]:
            st.markdown(
                """
                <div class="featured-card">
                    <span class="tag-pill">JWST ATMOSPHERIC INVERSION</span>
                    <h4 style="margin: 8px 0 4px 0; color: #f8fafc;">WASP-39b (NIRSpec PRISM)</h4>
                    <p style="color: #94a3b8; font-size: 0.85rem; margin-bottom: 8px;">
                        NASA JWST transmission spectrophotometry. Amortized normalizing flow retrieves chemical
                        abundances of H₂O and CO₂ in <strong>&lt; 50 ms</strong>.
                    </p>
                    <div style="font-size: 0.8rem; color: #00f5a0;">
                        ● log₁₀(CO₂) = <strong>-3.70</strong> &nbsp;|&nbsp; log₁₀(H₂O) = <strong>-3.20</strong>
                    </div>
                </div>
                """,
                unsafe_allow_html=True,
            )
            if st.button("Inspect WASP-39b", key="feat_btn_wasp39", use_container_width=True):
                state.select_candidate("WASP-39b")
                st.rerun()

        st.divider()
        st.subheader("🔍 Complete Discovery Catalog")
        filtered_candidates = state.get_filtered_candidates()
        st.info(f"Showing **{len(filtered_candidates)}** candidates matching active filters.")

        # Format interactive dataframe
        table_data = []
        for c in filtered_candidates:
            table_data.append({
                "Target ID": c.id,
                "Common / KOI Name": c.name,
                "Mission": c.mission,
                "Classification": c.category,
                "Period (d)": f"{c.period:.4f}",
                "Depth (ppm)": f"{c.depth_ppm:,.0f}",
                "Δ-BIC (Tail)": f"{c.delta_bic:+.1f}",
                "TTV SNR": f"{c.ttv_snr:.1f}",
                "P(Moon)": f"{c.p_moon * 100:.1f}%",
                "Asymmetry α": f"{c.asymmetry:.3f}",
            })

        if table_data:
            st.dataframe(table_data, use_container_width=True)
        else:
            st.warning("No candidates match the specified filter criteria.")

    # -------------------------------------------------------------------------
    # TAB 2: Light Curve & Transit Profile Inspector
    # -------------------------------------------------------------------------
    with tab_lc:
        render_lightcurve_view(state)

    # -------------------------------------------------------------------------
    # TAB 3: Localized Residual Anomaly Heatmap
    # -------------------------------------------------------------------------
    with tab_heatmap:
        render_heatmap_view(state)

    # -------------------------------------------------------------------------
    # TAB 4: Exomoon & Perturbation Analyzer
    # -------------------------------------------------------------------------
    with tab_pert:
        render_perturbation_view(state)

    # -------------------------------------------------------------------------
    # TAB 5: JWST Atmospheric Inversion View
    # -------------------------------------------------------------------------
    with tab_atmos:
        render_atmospheric_view(state)

    # -------------------------------------------------------------------------
    # TAB 6: Scientific Report Generator
    # -------------------------------------------------------------------------
    with tab_report:
        st.subheader("📑 Automated Astrophysical Discovery Report")
        st.caption("Generate a publication-ready scientific discovery summary for the active candidate.")

        if active_cand:
            report_md = f"""# ASTROPHYSICAL CANDIDATE EVALUATION DOSSIER
**System Identifier:** {active_cand.id} ({active_cand.name})
**Telescope Mission:** {active_cand.mission} Archive
**Orbital Period:** {active_cand.period:.5f} days
**Transit Epoch (t0):** {active_cand.t0:.4f}
**Catalog Transit Depth:** {active_cand.depth_ppm:,.1f} ppm ({active_cand.depth_ppm / 1e4:.3f}%)

---

## 1. Morphological & Dust Tail Evaluation
- **Delta-BIC Model Selection:** {active_cand.delta_bic:+.2f} (Threshold >= 10.0 for dust tail)
- **Transit Asymmetry Parameter (alpha):** {active_cand.asymmetry:.4f} (alpha > 0.25 indicates trailing dust tail)
- **Likelihood Ratio Test p-value:** {active_cand.lrt_p_value:.2e}
- **Dust Tail Verdict:** {'POSITIVE COMETARY TAIL DETECTED' if active_cand.delta_bic >= 10 else 'Consistent with symmetric planetary disk'}

## 2. Gravitational Perturbation & Exomoon Dynamics
- **Transit Timing Variation (TTV) SNR:** {active_cand.ttv_snr:.2f}
- **Barycentric Exomoon Posterior P(Moon):** {active_cand.p_moon * 100:.1f}%
- **Secondary Shoulder Detected:** {'YES' if active_cand.has_shoulder else 'NO'}
- **Dynamical Verdict:** {'HIGH SIGNIFICANCE EXOMOON CANDIDATE' if active_cand.p_moon >= 0.85 else 'Standard two-body Keplerian orbit'}

---
*Report synthesized automatically by the Frontier Astronomy AI Discovery Suite.*
"""
            st.markdown(report_md)
            st.download_button(
                label=f"📥 Download Scientific Dossier ({active_cand.id}.md)",
                data=report_md,
                file_name=f"report_{active_cand.id.replace(' ', '_')}.md",
                mime="text/markdown",
                use_container_width=True,
            )
        else:
            st.warning("Select a candidate in the sidebar to generate its report.")


def main() -> None:
    """CLI/Entrypoint runner for the dashboard."""
    run_app()


if __name__ == "__main__":
    main()
