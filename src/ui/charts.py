"""
Plotly chart factory functions for the Streamlit dashboard.
All functions return plotly Figure objects.
"""
from __future__ import annotations

from typing import Optional

import numpy as np
import pandas as pd
import plotly.express as px
import plotly.graph_objects as go
from plotly.subplots import make_subplots

# ── Colour palette ─────────────────────────────────────────────────────────────
PALETTE = {
    "primary": "#1A73E8",
    "success": "#0F9D58",
    "danger": "#EA4335",
    "warning": "#F4B400",
    "neutral": "#9AA0A6",
    "bg": "#0D1117",
    "card": "#161B22",
    "text": "#C9D1D9",
}

GRADE_COLORS = {
    "A": "#0F9D58", "B": "#4CAF50", "C": "#F4B400",
    "D": "#FF9800", "E": "#F44336", "F": "#9C27B0", "G": "#607D8B",
}


def _dark_layout(fig: go.Figure, title: str = "") -> go.Figure:
    fig.update_layout(
        title=dict(text=title, font=dict(color=PALETTE["text"], size=14)),
        paper_bgcolor=PALETTE["bg"],
        plot_bgcolor=PALETTE["bg"],
        font=dict(color=PALETTE["text"], family="JetBrains Mono, monospace"),
        margin=dict(l=40, r=20, t=50, b=40),
        xaxis=dict(gridcolor="#21262D", linecolor="#30363D"),
        yaxis=dict(gridcolor="#21262D", linecolor="#30363D"),
    )
    return fig


def funnel_chart(metrics: dict) -> go.Figure:
    stages = ["Applications", "Approved", "Funded"]
    values = [
        metrics.get("n_applications", 0),
        metrics.get("n_approved", 0),
        metrics.get("n_funded", 0),
    ]
    fig = go.Figure(go.Funnel(
        y=stages,
        x=values,
        textposition="inside",
        textinfo="value+percent initial",
        marker=dict(color=[PALETTE["primary"], PALETTE["success"], PALETTE["warning"]]),
    ))
    _dark_layout(fig, "Application → Funding Funnel")
    return fig


def time_series_chart(df: pd.DataFrame, metric_cols: list[str], date_col: str = "application_month") -> go.Figure:
    if date_col not in df.columns:
        return go.Figure()

    monthly = df.groupby(date_col).agg({c: "sum" for c in metric_cols if c in df.columns}).reset_index()
    monthly = monthly.sort_values(date_col)

    fig = go.Figure()
    colors = [PALETTE["primary"], PALETTE["success"], PALETTE["danger"], PALETTE["warning"]]
    for i, col in enumerate(metric_cols):
        if col in monthly.columns:
            fig.add_trace(go.Scatter(
                x=monthly[date_col].astype(str),
                y=monthly[col],
                name=col.replace("_", " ").title(),
                line=dict(color=colors[i % len(colors)], width=2),
                mode="lines+markers",
                marker=dict(size=4),
            ))
    _dark_layout(fig, "Portfolio Time Series")
    fig.update_layout(legend=dict(bgcolor="rgba(0,0,0,0)", bordercolor="#30363D"))
    return fig


def cohort_heatmap(pivot_df: pd.DataFrame) -> go.Figure:
    if pivot_df is None or pivot_df.empty:
        return go.Figure()

    z = pivot_df.values.astype(float) * 100   # convert to %
    fig = go.Figure(go.Heatmap(
        z=z,
        x=[c.replace("MOB ", "M") for c in pivot_df.columns],
        y=[str(i) for i in pivot_df.index],
        colorscale="RdYlGn_r",
        zmin=0, zmax=20,
        text=np.round(z, 1),
        texttemplate="%{text}%",
        colorbar=dict(title="30-DPD %", tickfont=dict(color=PALETTE["text"])),
    ))
    _dark_layout(fig, "30-DPD Rate Cohort Heatmap (Vintage × MOB)")
    fig.update_layout(
        xaxis_title="Months on Book",
        yaxis_title="Vintage Month",
        height=500,
    )
    return fig


def revenue_waterfall(baseline: dict, scenario: dict) -> go.Figure:
    categories = ["Interest Rev", "Interchange", "Fee Rev", "Late Fees", "Less: Losses", "Net Revenue"]
    b_vals = [
        baseline.get("interest_revenue", 0) / 1e6,
        baseline.get("interchange_revenue", 0) / 1e6,
        baseline.get("fee_revenue", 0) / 1e6,
        baseline.get("late_fee_revenue", 0) / 1e6,
        -baseline.get("actual_loss", 0) / 1e6,
        baseline.get("net_revenue", 0) / 1e6,
    ]
    s_vals = [
        scenario.get("interest_revenue", 0) / 1e6,
        scenario.get("interchange_revenue", 0) / 1e6,
        scenario.get("fee_revenue", 0) / 1e6,
        scenario.get("late_fee_revenue", 0) / 1e6,
        -scenario.get("actual_loss", 0) / 1e6,
        scenario.get("net_revenue", 0) / 1e6,
    ]

    fig = go.Figure()
    fig.add_trace(go.Bar(name="Baseline", x=categories, y=b_vals,
                          marker_color=PALETTE["primary"]))
    fig.add_trace(go.Bar(name="Scenario", x=categories, y=s_vals,
                          marker_color=PALETTE["warning"]))
    _dark_layout(fig, "Revenue Waterfall: Baseline vs Scenario ($M)")
    fig.update_layout(barmode="group")
    return fig


def scenario_delta_bar(delta: dict, delta_pct: dict) -> go.Figure:
    keys = ["total_revenue", "net_revenue", "expected_loss", "actual_loss"]
    labels = ["Total Revenue", "Net Revenue", "Expected Loss", "Actual Loss"]
    vals = [delta.get(k, 0) / 1e3 for k in keys]   # in $K
    colors = [PALETTE["success"] if v >= 0 else PALETTE["danger"] for v in vals]

    fig = go.Figure(go.Bar(
        x=labels,
        y=vals,
        marker_color=colors,
        text=[f"${v:+,.0f}K" for v in vals],
        textposition="outside",
    ))
    _dark_layout(fig, "Scenario Impact: Absolute Delta ($K)")
    fig.update_layout(yaxis_title="Delta ($K)")
    return fig


def grade_rar_chart(grade_df: pd.DataFrame) -> go.Figure:
    if grade_df is None or grade_df.empty:
        return go.Figure()

    fig = go.Figure()
    fig.add_trace(go.Bar(
        x=grade_df["grade"],
        y=grade_df["net_revenue"] / 1e6,
        name="Net Revenue ($M)",
        marker_color=[GRADE_COLORS.get(g, PALETTE["primary"]) for g in grade_df["grade"]],
        yaxis="y",
    ))
    fig.add_trace(go.Scatter(
        x=grade_df["grade"],
        y=grade_df["writeoff_rate"] * 100,
        name="Write-off Rate (%)",
        mode="lines+markers",
        line=dict(color=PALETTE["danger"], width=2),
        marker=dict(size=8),
        yaxis="y2",
    ))
    _dark_layout(fig, "Net Revenue & Write-off Rate by Grade")
    fig.update_layout(
        yaxis=dict(title=dict(text="Net Revenue ($M)", font=dict(color=PALETTE["primary"]))),
        yaxis2=dict(title=dict(text="Write-off Rate (%)", font=dict(color=PALETTE["danger"])),
                    overlaying="y", side="right"),
        legend=dict(bgcolor="rgba(0,0,0,0)"),
    )
    return fig


def delinquency_time_series(df: pd.DataFrame) -> go.Figure:
    monthly = df.groupby("application_month").agg(
        dpd30=("dpd30", "mean"),
        dpd60=("dpd60", "mean"),
        dpd90=("dpd90", "mean"),
        wo=("charged_off", "mean"),
    ).reset_index().sort_values("application_month")

    fig = go.Figure()
    styles = [
        ("dpd30", "30-DPD", PALETTE["warning"]),
        ("dpd60", "60-DPD", "#FF7043"),
        ("dpd90", "90-DPD", PALETTE["danger"]),
        ("wo", "Write-Off", "#7B1FA2"),
    ]
    for col, name, color in styles:
        fig.add_trace(go.Scatter(
            x=monthly["application_month"].astype(str),
            y=monthly[col] * 100,
            name=name,
            line=dict(color=color, width=2),
            mode="lines",
        ))
    _dark_layout(fig, "Delinquency & Write-off Rates by Month (%)")
    fig.update_layout(yaxis_title="Rate (%)")
    return fig


def apr_distribution(df: pd.DataFrame) -> go.Figure:
    funded = df[df["funded"] == True]
    fig = px.histogram(
        funded, x="int_rate", color="grade",
        nbins=40, barmode="stack",
        color_discrete_map=GRADE_COLORS,
        labels={"int_rate": "APR (%)", "count": "Accounts"},
    )
    _dark_layout(fig, "APR Distribution by Grade")
    return fig
