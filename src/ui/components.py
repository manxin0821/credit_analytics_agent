"""
Reusable Streamlit UI components for the dashboard.
"""
from __future__ import annotations

import streamlit as st
import pandas as pd


def kpi_card(label: str, value: str, delta: str = "", delta_positive: bool = True) -> None:
    """Render a styled KPI card using st.metric."""
    delta_str = delta if delta else None
    st.metric(
        label=label,
        value=value,
        delta=delta_str,
        delta_color="normal" if delta_positive else "inverse",
    )


def kpi_row(metrics: dict, baseline: dict | None = None) -> None:
    """Render a row of KPI cards."""
    items = list(metrics.items())
    cols = st.columns(len(items))
    for col, (label, value) in zip(cols, items):
        with col:
            if baseline and label in baseline:
                base_val = baseline[label]
                if isinstance(value, (int, float)) and isinstance(base_val, (int, float)) and base_val:
                    delta_val = value - base_val
                    delta_pct = delta_val / base_val * 100
                    delta_str = f"{delta_pct:+.1f}%"
                    kpi_card(label, _fmt(value), delta_str, delta_val >= 0)
                else:
                    kpi_card(label, _fmt(value))
            else:
                kpi_card(label, _fmt(value))


def _fmt(val) -> str:
    if isinstance(val, float):
        if val > 1_000_000:
            return f"${val/1e6:.2f}M"
        elif val > 1_000:
            return f"${val/1e3:.1f}K"
        elif val < 1:
            return f"{val*100:.2f}%"
        else:
            return f"{val:,.2f}"
    if isinstance(val, int):
        if val > 1_000_000:
            return f"{val/1e6:.1f}M"
        return f"{val:,}"
    return str(val)


def recommendation_card(recommendation: str) -> None:
    """Render the AI recommendation in a styled card."""
    st.markdown(
        f"""
        <div style="
            background: linear-gradient(135deg, #1A2332 0%, #0D1117 100%);
            border: 1px solid #1A73E8;
            border-left: 4px solid #1A73E8;
            border-radius: 8px;
            padding: 16px;
            margin: 8px 0;
        ">
        {recommendation}
        </div>
        """,
        unsafe_allow_html=True,
    )


def agent_trace_table(traces: list[dict]) -> None:
    """Render agent execution traces as a styled table."""
    if not traces:
        st.info("No agent traces yet. Ask a question to see execution flow.")
        return

    for trace in traces:
        icon = "✅" if trace.get("success") else "❌"
        with st.expander(
            f"{icon} **{trace['agent']}** — {trace['duration_ms']:.0f}ms",
            expanded=False,
        ):
            col1, col2 = st.columns(2)
            with col1:
                st.write("**Input:**", trace.get("input", "—"))
            with col2:
                st.write("**Output:**", trace.get("output", "—"))
            if trace.get("error"):
                st.error(f"Error: {trace['error']}")


def scenario_config_card(scenario_config) -> None:
    """Display current scenario config in the sidebar."""
    if scenario_config is None:
        return
    cfg = scenario_config.model_dump() if hasattr(scenario_config, "model_dump") else scenario_config
    st.json(cfg, expanded=False)


def segment_table(df: pd.DataFrame) -> None:
    """Render segment impact table with conditional formatting."""
    if df is None or df.empty:
        st.info("Run a scenario to see segment impact.")
        return

    display_cols = [
        "segment", "baseline_n_funded", "scenario_n_funded",
        "baseline_revenue", "scenario_revenue", "revenue_delta_pct",
        "baseline_writeoff_rate", "scenario_writeoff_rate",
        "net_revenue_delta", "recommendation",
    ]
    display_cols = [c for c in display_cols if c in df.columns]
    styled = df[display_cols].copy()

    # Format numeric columns
    for col in ["baseline_revenue", "scenario_revenue", "net_revenue_delta"]:
        if col in styled.columns:
            styled[col] = styled[col].apply(lambda x: f"${x:,.0f}")

    for col in ["revenue_delta_pct", "baseline_writeoff_rate", "scenario_writeoff_rate"]:
        if col in styled.columns:
            styled[col] = styled[col].apply(lambda x: f"{x:+.1f}%")

    st.dataframe(styled, use_container_width=True, hide_index=True)
