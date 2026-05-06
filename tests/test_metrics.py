"""
Unit tests for metric calculations.
"""
import sys
from pathlib import Path
sys.path.insert(0, str(Path(__file__).resolve().parents[1]))

import pandas as pd
import numpy as np
import pytest
from src.data.synthetic_data import generate_synthetic_loans
from src.metrics.metric_definitions import (
    compute_all_metrics, resolve_metric, METRIC_REGISTRY
)


@pytest.fixture(scope="module")
def sample_df():
    return generate_synthetic_loans(n=1_000, seed=0)


def test_all_metrics_compute(sample_df):
    """All metrics in registry should compute without error."""
    metrics = compute_all_metrics(sample_df)
    assert len(metrics) > 10
    for k, v in metrics.items():
        assert isinstance(v, float), f"Metric {k} returned non-float: {type(v)}"


def test_funnel_order(sample_df):
    metrics = compute_all_metrics(sample_df)
    n_app = metrics["n_applications"]
    n_appr = metrics["n_approved"]
    n_fund = metrics["n_funded"]
    assert n_appr <= n_app, "Approved > Applications"
    assert n_fund <= n_appr, "Funded > Approved"


def test_approval_rate_bounds(sample_df):
    metrics = compute_all_metrics(sample_df)
    ar = metrics["approval_rate"]
    assert 0 <= ar <= 1, f"approval_rate out of [0,1]: {ar}"


def test_writeoff_rate_formula(sample_df):
    metrics = compute_all_metrics(sample_df)
    manual_rate = metrics["writeoff_count"] / metrics["n_funded"] if metrics["n_funded"] else 0
    assert abs(metrics["writeoff_rate"] - manual_rate) < 0.01


def test_revenue_components_sum(sample_df):
    metrics = compute_all_metrics(sample_df)
    components = (
        metrics["interest_revenue"] +
        metrics["interchange_revenue"] +
        metrics["fee_revenue"] +
        metrics["late_fee_revenue"]
    )
    total = metrics["total_revenue"]
    assert abs(components - total) / max(total, 1) < 0.05, \
        f"Revenue components ({components:.0f}) don't sum to total ({total:.0f})"


def test_net_revenue_less_than_total(sample_df):
    metrics = compute_all_metrics(sample_df)
    assert metrics["net_revenue"] <= metrics["total_revenue"] + 1  # 1 for float noise


def test_resolve_alias():
    mdef = resolve_metric("applications")
    assert mdef is not None
    assert mdef.key == "n_applications"


def test_resolve_unknown():
    mdef = resolve_metric("nonexistent_metric_xyz")
    assert mdef is None


def test_dpd_hierarchy(sample_df):
    metrics = compute_all_metrics(sample_df)
    # 90 DPD count should be <= 60 DPD <= 30 DPD
    assert metrics["dpd90_count"] <= metrics["dpd60_count"] + 1   # +1 for floating point
    assert metrics["dpd60_count"] <= metrics["dpd30_count"] + 1
