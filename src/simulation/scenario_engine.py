"""
Scenario simulation engine.

Applies APR shocks, demand elasticity, and PD sensitivity adjustments
to a loan portfolio DataFrame and returns a comparison metrics dict.
"""
from __future__ import annotations

import logging
from copy import deepcopy

import numpy as np
import pandas as pd

from src.simulation.scenario_config import ScenarioConfig
from src.metrics.metric_definitions import compute_all_metrics
from config.settings import DEMAND_SENSITIVITY_MAP, PD_SENSITIVITY_MAP

logger = logging.getLogger(__name__)


def run_scenario(
    df: pd.DataFrame,
    scenario: ScenarioConfig,
) -> dict:
    """
    Apply scenario assumptions to the portfolio and compute metrics.

    Returns
    -------
    dict with keys:
        - 'baseline': dict of baseline metrics
        - 'scenario': dict of post-shock metrics
        - 'delta': dict of absolute changes
        - 'delta_pct': dict of relative changes
        - 'scenario_df': modified DataFrame
        - 'segment_impact': DataFrame with per-segment impacts
    """
    baseline_metrics = compute_all_metrics(df)

    # ── Clone DataFrame for mutation ──────────────────────────────────────────
    sdf = df.copy()
    apr_shock = scenario.apr_shock_pp  # in percentage points

    # ── Identify affected loans ────────────────────────────────────────────────
    affected_mask = pd.Series(True, index=sdf.index)
    if scenario.exclude_grades:
        affected_mask &= ~sdf["grade"].isin(scenario.exclude_grades)
    if scenario.exclude_income_bands:
        affected_mask &= ~sdf["income_band"].isin(scenario.exclude_income_bands)

    # ── 1. Apply APR shock (additive, percentage points) ──────────────────────
    sdf.loc[affected_mask, "int_rate"] = sdf.loc[affected_mask, "int_rate"] + apr_shock
    sdf["int_rate"] = sdf["int_rate"].clip(0, 100)

    # ── 2. Demand sensitivity → application volume shrink ─────────────────────
    demand_drop = DEMAND_SENSITIVITY_MAP.get(scenario.demand_sensitivity, 0.05)
    vol_reduction = abs(apr_shock) * demand_drop   # fraction of apps lost

    if vol_reduction > 0 and apr_shock > 0:
        # Randomly drop some applications (those affected by rate hike)
        n_drop = int(affected_mask.sum() * vol_reduction)
        drop_idx = sdf[affected_mask & ~sdf["funded"]].sample(
            n=min(n_drop, (affected_mask & ~sdf["funded"]).sum()),
            random_state=42,
        ).index
        sdf = sdf.drop(index=drop_idx)
        logger.info("Demand shock: removed %d applications", len(drop_idx))

    # ── 3. PD sensitivity → higher default probability ─────────────────────────
    pd_delta_per_pp = PD_SENSITIVITY_MAP.get(scenario.pd_sensitivity, 0.015)
    pd_uplift = abs(apr_shock) * pd_delta_per_pp
    if pd_uplift > 0 and apr_shock > 0:
        affected_in_sdf = affected_mask[affected_mask.index.isin(sdf.index)]
        sdf.loc[affected_in_sdf[affected_in_sdf].index, "pd_score"] = (
            sdf.loc[affected_in_sdf[affected_in_sdf].index, "pd_score"] + pd_uplift
        ).clip(0, 0.99)

    sdf = sdf.reset_index(drop=True)

    # ── 4. Re-derive revenue with new APR ─────────────────────────────────────
    rng = np.random.default_rng(42)
    funded_mask = sdf["funded"] == True
    sdf.loc[funded_mask, "interest_revenue"] = (
        sdf.loc[funded_mask, "loan_amnt"] *
        (sdf.loc[funded_mask, "int_rate"] / 100) *
        (sdf.loc[funded_mask, "term"] / 12) *
        rng.uniform(0.55, 0.95, size=funded_mask.sum())
    ).round(2)

    # ── 5. Re-derive charge-offs from updated PD ──────────────────────────────
    rand_vals = rng.random(size=len(sdf))
    funded_mask = sdf["funded"] == True
    sdf = sdf.copy()
    sdf["charged_off"] = funded_mask.values & (rand_vals < sdf["pd_score"].values)

    # ── 6. Re-derive DPD flags ─────────────────────────────────────────────────
    sdf["dpd30"] = funded_mask.values & ~sdf["charged_off"].values & (rng.random(len(sdf)) < sdf["pd_score"].values * 1.8)
    sdf["dpd60"] = sdf["dpd30"].values & (rng.random(len(sdf)) < 0.50)
    sdf["dpd90"] = sdf["dpd60"].values & (rng.random(len(sdf)) < 0.45)

    scenario_metrics = compute_all_metrics(sdf)

    # ── Delta calculations ─────────────────────────────────────────────────────
    delta = {k: scenario_metrics.get(k, 0) - baseline_metrics.get(k, 0)
             for k in baseline_metrics}
    delta_pct = {
        k: (delta[k] / baseline_metrics[k]) if baseline_metrics.get(k) else 0.0
        for k in delta
    }

    # ── Segment-level impact ───────────────────────────────────────────────────
    segment_impact = _build_segment_impact(df, sdf, scenario.group_by)

    return {
        "baseline": baseline_metrics,
        "scenario": scenario_metrics,
        "delta": delta,
        "delta_pct": delta_pct,
        "scenario_df": sdf,
        "segment_impact": segment_impact,
        "config": scenario.model_dump(),
    }


def _build_segment_impact(
    baseline_df: pd.DataFrame,
    scenario_df: pd.DataFrame,
    group_by: list[str],
) -> pd.DataFrame:
    """Build per-segment impact summary for recommendation table."""
    rows = []

    primary = group_by[0] if group_by else "grade"
    if primary not in baseline_df.columns:
        primary = "grade"

    for segment_val in baseline_df[primary].unique():
        b_seg = baseline_df[baseline_df[primary] == segment_val]
        s_seg = scenario_df[scenario_df[primary] == segment_val] if primary in scenario_df.columns else pd.DataFrame()

        if s_seg.empty:
            continue

        b_funded = b_seg[b_seg["funded"] == True]
        s_funded = s_seg[s_seg["funded"] == True]

        b_rev = b_funded["interest_revenue"].sum()
        s_rev = s_funded["interest_revenue"].sum() if len(s_funded) else 0
        b_loss = (b_funded["pd_score"] * 0.60 * b_funded["loan_amnt"]).sum()
        s_loss = (s_funded["pd_score"] * 0.60 * s_funded["loan_amnt"]).sum() if len(s_funded) else 0

        b_wo = b_funded["charged_off"].mean() if len(b_funded) else 0
        s_wo = s_funded["charged_off"].mean() if len(s_funded) else 0

        rows.append({
            "segment": segment_val,
            "dimension": primary,
            "baseline_n_funded": len(b_funded),
            "scenario_n_funded": len(s_funded),
            "baseline_revenue": round(b_rev, 0),
            "scenario_revenue": round(s_rev, 0),
            "revenue_delta": round(s_rev - b_rev, 0),
            "revenue_delta_pct": round((s_rev - b_rev) / b_rev * 100 if b_rev else 0, 2),
            "baseline_loss": round(b_loss, 0),
            "scenario_loss": round(s_loss, 0),
            "loss_delta_pct": round((s_loss - b_loss) / b_loss * 100 if b_loss else 0, 2),
            "baseline_writeoff_rate": round(b_wo * 100, 2),
            "scenario_writeoff_rate": round(s_wo * 100, 2),
            "net_revenue_delta": round((s_rev - s_loss) - (b_rev - b_loss), 0),
            "recommendation": _recommend_action(s_wo - b_wo, (s_rev - b_rev) / b_rev if b_rev else 0),
        })

    return pd.DataFrame(rows).sort_values("net_revenue_delta", ascending=False)


def _recommend_action(delta_wo: float, delta_rev_pct: float) -> str:
    if delta_wo > 0.05 and delta_rev_pct < 0.05:
        return "⛔ Exclude from rate increase"
    elif delta_wo > 0.03:
        return "⚠️  Monitor closely"
    elif delta_rev_pct > 0.10:
        return "✅ Apply rate increase"
    else:
        return "✅ Apply with caution"
