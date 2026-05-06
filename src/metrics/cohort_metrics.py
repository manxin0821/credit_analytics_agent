"""
Cohort-level metric aggregation utilities.
"""
from __future__ import annotations

import pandas as pd
import numpy as np


def build_cohort_table(
    df: pd.DataFrame,
    cohort_col: str = "vintage_month",
    mob_col: str = "mob",
    metric_col: str = "dpd30",
    aggfunc: str = "mean",
) -> pd.DataFrame:
    """
    Build a cohort × MOB pivot table for heatmap visualisation.

    Parameters
    ----------
    df : pd.DataFrame
    cohort_col : str
        Column that defines the cohort (e.g. 'vintage_month').
    mob_col : str
        Months-on-book column.
    metric_col : str
        Numeric column to aggregate (e.g. 'dpd30', 'charged_off').
    aggfunc : str
        Aggregation function: 'mean', 'sum', 'count'.

    Returns
    -------
    pd.DataFrame  (cohorts as index, MOB buckets as columns)
    """
    funded = df[df["funded"] == True].copy()
    funded["mob_bucket"] = (funded[mob_col] // 3) * 3  # 0,3,6,9,...

    pivot = funded.pivot_table(
        index=cohort_col,
        columns="mob_bucket",
        values=metric_col,
        aggfunc=aggfunc,
    )
    pivot.index.name = "Cohort"
    pivot.columns = [f"MOB {c}" for c in pivot.columns]
    return pivot.sort_index()


def delinquency_progression(
    df: pd.DataFrame,
    group_col: str = "vintage_month",
) -> pd.DataFrame:
    """
    Compute 30/60/90 DPD rates per cohort group.

    Returns a long-format DataFrame suitable for line charts.
    """
    funded = df[df["funded"] == True].copy()
    grp = funded.groupby(group_col)

    result = pd.DataFrame({
        "cohort": grp.groups.keys(),
        "n_funded": grp["funded"].count().values,
        "dpd30_rate": grp["dpd30"].mean().values,
        "dpd60_rate": grp["dpd60"].mean().values,
        "dpd90_rate": grp["dpd90"].mean().values,
        "writeoff_rate": grp["charged_off"].mean().values,
    })
    return result.sort_values("cohort").reset_index(drop=True)


def grade_segment_summary(df: pd.DataFrame) -> pd.DataFrame:
    """
    Aggregated metrics by risk grade.
    """
    funded = df[df["funded"] == True].copy()
    grp = funded.groupby("grade")

    summary = pd.DataFrame({
        "grade": grp.groups.keys(),
        "n_funded": grp["funded"].count().values,
        "avg_apr": grp["int_rate"].mean().values,
        "avg_loan": grp["loan_amnt"].mean().values,
        "booked_balance": grp["loan_amnt"].sum().values,
        "interest_revenue": grp["interest_revenue"].sum().values,
        "expected_loss": (grp["pd_score"].mean() * 0.60 * grp["loan_amnt"].mean() * grp["funded"].count()).values,
        "dpd30_rate": grp["dpd30"].mean().values,
        "dpd90_rate": grp["dpd90"].mean().values,
        "writeoff_rate": grp["charged_off"].mean().values,
    })
    summary["net_revenue"] = summary["interest_revenue"] - summary["expected_loss"]
    summary["rar"] = summary["net_revenue"] / summary["booked_balance"].replace(0, np.nan)
    return summary.sort_values("grade").reset_index(drop=True)
