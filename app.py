"""
Agentic Credit Analytics Command Center
========================================
Main Streamlit application entry point.

Run with:
    streamlit run app.py
"""
from __future__ import annotations

import logging
import sys
import os
from pathlib import Path

# ── Ensure project root is on sys.path ────────────────────────────────────────
ROOT = Path(__file__).resolve().parent
if str(ROOT) not in sys.path:
    sys.path.insert(0, str(ROOT))

from dotenv import load_dotenv
load_dotenv(ROOT / ".env")

import streamlit as st
import pandas as pd
import plotly.graph_objects as go

from config.settings import APP_TITLE, DASHBOARD_TABS
from src.utils.logging import setup_logging
from src.data.load_data import load_loans
from src.metrics.metric_definitions import compute_all_metrics
from src.metrics.cohort_metrics import build_cohort_table, grade_segment_summary, delinquency_progression
from src.agents.orchestrator import OrchestratorAgent
from src.ui.charts import (
    funnel_chart, time_series_chart, cohort_heatmap,
    revenue_waterfall, scenario_delta_bar, grade_rar_chart,
    delinquency_time_series, apr_distribution,
)
from src.ui.components import (
    kpi_row, recommendation_card, agent_trace_table,
    scenario_config_card, segment_table, _fmt,
)

setup_logging(logging.WARNING)
logger = logging.getLogger(__name__)

# ═══════════════════════════════════════════════════════════════════════════════
# Page config
# ═══════════════════════════════════════════════════════════════════════════════
st.set_page_config(
    page_title=APP_TITLE,
    page_icon="📊",
    layout="wide",
    initial_sidebar_state="collapsed",
)

# ── Custom CSS ─────────────────────────────────────────────────────────────────
st.markdown("""
<style>
@import url('https://fonts.googleapis.com/css2?family=JetBrains+Mono:wght@300;400;500&family=Space+Grotesk:wght@300;400;500;600;700&display=swap');

html, body, [class*="css"] {
    font-family: 'Space Grotesk', sans-serif;
}

.stApp {
    background-color: #0D1117;
    color: #C9D1D9;
}

.main-header {
    background: linear-gradient(135deg, #1A2332 0%, #0D1117 100%);
    border-bottom: 1px solid #21262D;
    padding: 16px 24px 12px;
    margin-bottom: 0;
}

.main-header h1 {
    font-family: 'JetBrains Mono', monospace;
    font-size: 1.4rem;
    font-weight: 500;
    color: #58A6FF;
    letter-spacing: -0.5px;
    margin: 0;
}

.main-header p {
    font-size: 0.75rem;
    color: #6E7681;
    margin: 2px 0 0;
}

.copilot-header {
    font-family: 'JetBrains Mono', monospace;
    font-size: 0.85rem;
    color: #58A6FF;
    border-bottom: 1px solid #21262D;
    padding-bottom: 8px;
    margin-bottom: 12px;
}

.metric-card {
    background: #161B22;
    border: 1px solid #21262D;
    border-radius: 6px;
    padding: 12px;
}

.stMetric {
    background: #161B22 !important;
    border: 1px solid #21262D !important;
    border-radius: 6px !important;
    padding: 10px 14px !important;
}

.stMetric label {
    color: #8B949E !important;
    font-size: 0.72rem !important;
    text-transform: uppercase;
    letter-spacing: 0.5px;
}

.stMetric [data-testid="stMetricValue"] {
    color: #E6EDF3 !important;
    font-family: 'JetBrains Mono', monospace !important;
    font-size: 1.3rem !important;
}

.stTabs [data-baseweb="tab-list"] {
    background-color: #161B22;
    border-bottom: 1px solid #21262D;
}

.stTabs [data-baseweb="tab"] {
    color: #8B949E;
    font-size: 0.8rem;
    padding: 8px 16px;
}

.stTabs [aria-selected="true"] {
    color: #58A6FF !important;
    border-bottom: 2px solid #58A6FF !important;
}

.chat-message-user {
    background: #1C2B3A;
    border: 1px solid #1A73E8;
    border-radius: 8px;
    padding: 10px 14px;
    margin: 6px 0;
    font-size: 0.85rem;
}

.chat-message-ai {
    background: #161B22;
    border: 1px solid #21262D;
    border-left: 3px solid #0F9D58;
    border-radius: 8px;
    padding: 10px 14px;
    margin: 6px 0;
    font-size: 0.85rem;
}

.status-badge {
    display: inline-block;
    padding: 2px 8px;
    border-radius: 12px;
    font-size: 0.7rem;
    font-family: 'JetBrains Mono', monospace;
}

.badge-green { background: #0F3D24; color: #3FB950; border: 1px solid #238636; }
.badge-red { background: #3D1A1A; color: #F85149; border: 1px solid #DA3633; }
.badge-yellow { background: #3D2E00; color: #E3B341; border: 1px solid #9E6A03; }

div[data-testid="stVerticalBlock"] > div:has(> div[data-testid="stChatInput"]) {
    position: sticky;
    bottom: 0;
    background: #0D1117;
    padding-top: 8px;
}
</style>
""", unsafe_allow_html=True)

# ═══════════════════════════════════════════════════════════════════════════════
# Session state initialisation
# ═══════════════════════════════════════════════════════════════════════════════
if "chat_history" not in st.session_state:
    st.session_state.chat_history = []
if "agent_traces" not in st.session_state:
    st.session_state.agent_traces = []
if "last_result" not in st.session_state:
    st.session_state.last_result = None
if "active_tab" not in st.session_state:
    st.session_state.active_tab = "Overview"
if "scenario_results" not in st.session_state:
    st.session_state.scenario_results = None

# ═══════════════════════════════════════════════════════════════════════════════
# Data & metrics (cached)
# ═══════════════════════════════════════════════════════════════════════════════
@st.cache_data(show_spinner="Loading portfolio data…")
def _load_data():
    return load_loans()

@st.cache_data(show_spinner="Computing baseline metrics…")
def _get_baseline_metrics(_df_hash):
    df = load_loans()
    return compute_all_metrics(df)

@st.cache_data(show_spinner="Building cohort table…")
def _get_cohort_table(_df_hash):
    df = load_loans()
    return build_cohort_table(df, metric_col="dpd30")

@st.cache_data(show_spinner="Computing grade summary…")
def _get_grade_summary(_df_hash):
    df = load_loans()
    return grade_segment_summary(df)

df = _load_data()
df_hash = len(df)   # simple hash for cache invalidation
baseline = _get_baseline_metrics(df_hash)
cohort_tbl = _get_cohort_table(df_hash)
grade_summary_df = _get_grade_summary(df_hash)

# ═══════════════════════════════════════════════════════════════════════════════
# Header
# ═══════════════════════════════════════════════════════════════════════════════
st.markdown(f"""
<div class="main-header">
    <h1>📊 {APP_TITLE}</h1>
    <p>Multi-Agent AI | {len(df):,} loans | ${baseline.get('booked_balance', 0)/1e6:.1f}M booked balance</p>
</div>
""", unsafe_allow_html=True)

st.markdown("<br>", unsafe_allow_html=True)

# ═══════════════════════════════════════════════════════════════════════════════
# Main layout: dashboard (75%) | copilot (25%)
# ═══════════════════════════════════════════════════════════════════════════════
dash_col, cop_col = st.columns([3, 1])

# ══════════════════════════════════════════════════════
# LEFT: Dashboard
# ══════════════════════════════════════════════════════
with dash_col:
    tabs = st.tabs(DASHBOARD_TABS)

    # ── Tab 0: Overview ────────────────────────────────────────────────────────
    with tabs[0]:
        st.markdown("#### Portfolio Overview")

        # KPIs row 1 — Funnel
        c1, c2, c3, c4, c5 = st.columns(5)
        kpis1 = [
            (c1, "Applications", baseline.get("n_applications", 0), "count"),
            (c2, "Funded Accounts", baseline.get("n_funded", 0), "count"),
            (c3, "Approval Rate", baseline.get("approval_rate", 0), "pct"),
            (c4, "Booked Balance", baseline.get("booked_balance", 0), "usd"),
            (c5, "Avg APR", baseline.get("avg_apr", 0), "apr"),
        ]
        for col, label, val, fmt_type in kpis1:
            with col:
                if fmt_type == "count":
                    st.metric(label, f"{val:,.0f}")
                elif fmt_type == "pct":
                    st.metric(label, f"{val*100:.1f}%")
                elif fmt_type == "usd":
                    st.metric(label, f"${val/1e6:.1f}M")
                elif fmt_type == "apr":
                    st.metric(label, f"{val:.2f}%")

        st.markdown("---")

        # KPIs row 2 — Revenue & Loss
        c1, c2, c3, c4, c5 = st.columns(5)
        with c1:
            st.metric("Total Revenue", f"${baseline.get('total_revenue', 0)/1e6:.2f}M")
        with c2:
            st.metric("Net Revenue", f"${baseline.get('net_revenue', 0)/1e6:.2f}M")
        with c3:
            st.metric("Expected Loss", f"${baseline.get('expected_loss', 0)/1e6:.2f}M")
        with c4:
            st.metric("30-DPD Rate", f"{baseline.get('dpd30_rate', 0)*100:.2f}%")
        with c5:
            st.metric("Write-off Rate", f"{baseline.get('writeoff_rate', 0)*100:.2f}%")

        st.markdown("---")

        # Charts
        col_a, col_b = st.columns(2)
        with col_a:
            st.plotly_chart(
                time_series_chart(df, ["loan_amnt", "interest_revenue"], "application_month"),
                use_container_width=True
            )
        with col_b:
            st.plotly_chart(apr_distribution(df), use_container_width=True)

        st.plotly_chart(grade_rar_chart(grade_summary_df), use_container_width=True)

    # ── Tab 1: Funnel ──────────────────────────────────────────────────────────
    with tabs[1]:
        st.markdown("#### Application & Funding Funnel")

        c1, c2, c3, c4 = st.columns(4)
        with c1: st.metric("Applications", f"{baseline.get('n_applications', 0):,.0f}")
        with c2: st.metric("Approved", f"{baseline.get('n_approved', 0):,.0f}")
        with c3: st.metric("Funded", f"{baseline.get('n_funded', 0):,.0f}")
        with c4: st.metric("Avg Funded Amt", f"${baseline.get('avg_funded_amount', 0):,.0f}")

        col_a, col_b = st.columns([1, 1])
        with col_a:
            st.plotly_chart(funnel_chart(baseline), use_container_width=True)
        with col_b:
            # Grade breakdown funnel
            grade_funded = df[df["funded"] == True].groupby("grade")["funded"].count().reset_index()
            grade_funded.columns = ["Grade", "Funded"]
            st.bar_chart(grade_funded.set_index("Grade")["Funded"])

        # Funnel by grade table
        funnel_by_grade = df.groupby("grade").agg(
            applications=("loan_id", "count"),
            approved=("approved", "sum"),
            funded=("funded", "sum"),
            avg_apr=("int_rate", "mean"),
            avg_loan=("loan_amnt", "mean"),
        ).reset_index()
        funnel_by_grade["approval_rate"] = (funnel_by_grade["approved"] / funnel_by_grade["applications"] * 100).round(1)
        funnel_by_grade["funding_rate"] = (funnel_by_grade["funded"] / funnel_by_grade["approved"] * 100).round(1)
        funnel_by_grade["avg_apr"] = funnel_by_grade["avg_apr"].round(2)
        funnel_by_grade["avg_loan"] = funnel_by_grade["avg_loan"].round(0)
        st.dataframe(funnel_by_grade, use_container_width=True, hide_index=True)

    # ── Tab 2: Cohort ──────────────────────────────────────────────────────────
    with tabs[2]:
        st.markdown("#### Cohort Analysis")

        # Controls
        cohort_col_select = st.selectbox(
            "Cohort dimension",
            ["vintage_month", "application_month", "funding_month", "grade"],
            key="cohort_dim",
        )
        metric_select = st.selectbox(
            "Metric",
            ["dpd30", "dpd60", "dpd90", "charged_off"],
            key="cohort_metric",
        )

        try:
            custom_cohort = build_cohort_table(
                df, cohort_col=cohort_col_select, metric_col=metric_select
            )
            st.plotly_chart(cohort_heatmap(custom_cohort), use_container_width=True)
        except Exception as e:
            st.warning(f"Could not build cohort table: {e}")
            st.plotly_chart(cohort_heatmap(cohort_tbl), use_container_width=True)

        # Delinquency progression by vintage
        dprog = delinquency_progression(df, group_col="vintage_month")
        if not dprog.empty and len(dprog) > 1:
            st.markdown("##### Delinquency Progression by Vintage")
            st.plotly_chart(
                time_series_chart(
                    dprog.rename(columns={"cohort": "application_month"}),
                    ["dpd30_rate", "dpd60_rate", "dpd90_rate", "writeoff_rate"],
                    "application_month",
                ),
                use_container_width=True,
            )

    # ── Tab 3: Time Series ────────────────────────────────────────────────────
    with tabs[3]:
        st.markdown("#### Portfolio Time Series")

        col_a, col_b = st.columns(2)
        with col_a:
            st.plotly_chart(
                time_series_chart(df, ["loan_amnt", "interest_revenue", "origination_fee"], "application_month"),
                use_container_width=True,
            )
        with col_b:
            st.plotly_chart(delinquency_time_series(df), use_container_width=True)

        # Monthly summary table
        monthly_summary = df.groupby("application_month").agg(
            n_applications=("loan_id", "count"),
            n_funded=("funded", "sum"),
            booked_balance=("loan_amnt", lambda x: x[df.loc[x.index, "funded"] == True].sum() if "funded" in df.columns else 0),
            avg_apr=("int_rate", "mean"),
            dpd30_rate=("dpd30", "mean"),
            writeoff_rate=("charged_off", "mean"),
        ).reset_index().sort_values("application_month", ascending=False).head(24)

        st.markdown("##### Monthly Summary (latest 24 months)")
        st.dataframe(monthly_summary, use_container_width=True, hide_index=True)

    # ── Tab 4: Scenario Lab ────────────────────────────────────────────────────
    with tabs[4]:
        st.markdown("#### Scenario Laboratory")

        last = st.session_state.last_result
        sim = st.session_state.scenario_results

        if sim is None:
            st.info("💬 Ask the AI Copilot a scenario question (e.g. *'If APR increases by 5pp, what happens to revenue and loss?'*) to populate this view.")

            # Manual scenario controls
            st.markdown("---")
            st.markdown("**Or configure manually:**")
            col_a, col_b, col_c = st.columns(3)
            with col_a:
                apr_shock = st.slider("APR Shock (pp)", -10.0, 15.0, 5.0, 0.5)
            with col_b:
                demand_sens = st.selectbox("Demand Sensitivity", ["low", "medium", "high"], index=1)
            with col_c:
                pd_sens = st.selectbox("PD Sensitivity", ["low", "medium", "high"], index=0)

            if st.button("▶ Run Scenario", type="primary"):
                from src.simulation.scenario_config import ScenarioConfig
                from src.simulation.scenario_engine import run_scenario

                with st.spinner("Running scenario simulation…"):
                    cfg = ScenarioConfig(
                        apr_shock_pp=apr_shock,
                        demand_sensitivity=demand_sens,
                        pd_sensitivity=pd_sens,
                        label=f"APR +{apr_shock}pp Manual",
                    )
                    results = run_scenario(df, cfg)
                    st.session_state.scenario_results = results
                st.rerun()

        else:
            b = sim["baseline"]
            s = sim["scenario"]
            d = sim["delta"]

            # Summary KPIs
            st.markdown("##### Scenario vs Baseline")
            c1, c2, c3, c4 = st.columns(4)
            with c1:
                delta_rev = d.get("total_revenue", 0)
                st.metric("Total Revenue", f"${s.get('total_revenue',0)/1e6:.2f}M",
                          delta=f"${delta_rev/1e3:+.0f}K",
                          delta_color="normal" if delta_rev >= 0 else "inverse")
            with c2:
                delta_net = d.get("net_revenue", 0)
                st.metric("Net Revenue", f"${s.get('net_revenue',0)/1e6:.2f}M",
                          delta=f"${delta_net/1e3:+.0f}K",
                          delta_color="normal" if delta_net >= 0 else "inverse")
            with c3:
                delta_el = d.get("expected_loss", 0)
                st.metric("Expected Loss", f"${s.get('expected_loss',0)/1e6:.2f}M",
                          delta=f"${delta_el/1e3:+.0f}K",
                          delta_color="inverse" if delta_el >= 0 else "normal")
            with c4:
                delta_wo = d.get("writeoff_rate", 0)
                st.metric("Write-off Rate", f"{s.get('writeoff_rate',0)*100:.2f}%",
                          delta=f"{delta_wo*100:+.2f}pp",
                          delta_color="inverse" if delta_wo >= 0 else "normal")

            col_a, col_b = st.columns(2)
            with col_a:
                st.plotly_chart(revenue_waterfall(b, s), use_container_width=True)
            with col_b:
                st.plotly_chart(scenario_delta_bar(d, sim.get("delta_pct", {})), use_container_width=True)

            # Segment impact table
            seg_impact = sim.get("segment_impact")
            if seg_impact is not None and not seg_impact.empty:
                st.markdown("##### Segment Impact & Recommendations")
                segment_table(seg_impact)

            if st.button("🔄 Clear Scenario"):
                st.session_state.scenario_results = None
                st.rerun()

    # ── Tab 5: Agent Trace ─────────────────────────────────────────────────────
    with tabs[5]:
        st.markdown("#### Agent Execution Trace")
        traces = st.session_state.agent_traces
        if not traces:
            st.info("No agent executions yet. Ask the copilot a question.")
        else:
            agent_trace_table(traces)
            if st.button("Clear Trace Log"):
                st.session_state.agent_traces = []
                st.rerun()

# ══════════════════════════════════════════════════════
# RIGHT: AI Copilot
# ══════════════════════════════════════════════════════
with cop_col:
    st.markdown('<div class="copilot-header">🤖 AI Copilot</div>', unsafe_allow_html=True)

    # ── Chat history ───────────────────────────────────────────────────────────
    chat_container = st.container()
    with chat_container:
        for msg in st.session_state.chat_history[-8:]:  # show last 8 messages
            if msg["role"] == "user":
                st.markdown(
                    f'<div class="chat-message-user">👤 {msg["content"]}</div>',
                    unsafe_allow_html=True,
                )
            else:
                st.markdown(
                    f'<div class="chat-message-ai">{msg["content"]}</div>',
                    unsafe_allow_html=True,
                )

    st.markdown("---")

    # ── Suggestion chips ───────────────────────────────────────────────────────
    suggestions = [
        "APR +5pp: revenue & loss impact?",
        "Which segments to exclude?",
        "Worst vintage cohort?",
        "Why did net revenue decline?",
    ]

    st.markdown('<p style="font-size:0.7rem;color:#6E7681;margin-bottom:4px;">Suggestions:</p>',
                unsafe_allow_html=True)
    cols = st.columns(2)
    for i, sug in enumerate(suggestions):
        with cols[i % 2]:
            if st.button(sug, key=f"sug_{i}", use_container_width=True,
                         help="Click to ask this question"):
                st.session_state._pending_question = sug

    # ── Chat input ─────────────────────────────────────────────────────────────
    user_input = st.chat_input("Ask about your credit portfolio…")

    # Handle suggestion button clicks
    if hasattr(st.session_state, "_pending_question"):
        user_input = st.session_state._pending_question
        del st.session_state._pending_question

    if user_input:
        # Add user message
        st.session_state.chat_history.append({"role": "user", "content": user_input})

        api_key = os.environ.get("DEEPSEEK_API_KEY", "")
        if not api_key:
            err_msg = "⚠️ **DEEPSEEK_API_KEY not set.** Please add it to your `.env` file and restart.\n\n```\nDEEPSEEK_API_KEY=your_key_here\n```"
            st.session_state.chat_history.append({"role": "assistant", "content": err_msg})
            st.rerun()

        with st.spinner("🧠 Agents working…"):
            try:
                orchestrator = OrchestratorAgent()
                result = orchestrator.run(user_input)

                # Store results in session state
                st.session_state.last_result = result
                st.session_state.agent_traces = result.get("traces", [])

                # Store scenario results for Scenario Lab tab
                if result.get("simulation_results"):
                    st.session_state.scenario_results = result["simulation_results"]

                # Build copilot response
                recommendation = result.get("recommendation", "No recommendation generated.")
                validation_summary = result.get("validation_summary", "")
                target_tab = result.get("target_tab", "Overview")

                response_parts = [recommendation]
                if not result.get("validation_passed", True):
                    response_parts.append(f"\n\n⚠️ **Validation Warnings:**\n{validation_summary}")
                response_parts.append(f"\n\n📊 *Dashboard updated → **{target_tab}** tab*")

                response = "\n".join(response_parts)
                st.session_state.chat_history.append({"role": "assistant", "content": response})

            except Exception as exc:
                err = f"❌ Error: {exc}"
                st.session_state.chat_history.append({"role": "assistant", "content": err})
                logger.exception("Orchestrator error: %s", exc)

        st.rerun()

    st.markdown("---")

    # ── Current scenario config ────────────────────────────────────────────────
    last = st.session_state.last_result
    if last and last.get("scenario_config"):
        st.markdown('<p style="font-size:0.72rem;color:#6E7681;text-transform:uppercase;">Scenario Config</p>',
                    unsafe_allow_html=True)
        scenario_config_card(last["scenario_config"])

    # ── Validation status ──────────────────────────────────────────────────────
    if last:
        passed = last.get("validation_passed", True)
        badge = '<span class="status-badge badge-green">✓ Valid</span>' if passed else \
                '<span class="status-badge badge-red">⚠ Issues</span>'
        st.markdown(f"**Data Quality:** {badge}", unsafe_allow_html=True)

    # ── Clear chat ─────────────────────────────────────────────────────────────
    if st.button("🗑 Clear Chat", use_container_width=True):
        st.session_state.chat_history = []
        st.session_state.last_result = None
        st.session_state.agent_traces = []
        st.session_state.scenario_results = None
        st.rerun()
