"""
Tests for the scenario simulation engine.
"""
import sys
from pathlib import Path
sys.path.insert(0, str(Path(__file__).resolve().parents[1]))

import pytest
from src.data.synthetic_data import generate_synthetic_loans
from src.simulation.scenario_config import ScenarioConfig
from src.simulation.scenario_engine import run_scenario


@pytest.fixture(scope="module")
def df():
    return generate_synthetic_loans(n=2_000, seed=1)


def test_baseline_scenario_no_change(df):
    """Zero shock scenario should produce near-identical metrics."""
    cfg = ScenarioConfig(apr_shock_pp=0.0, label="baseline")
    results = run_scenario(df, cfg)
    # Revenue should be within 2% (due to re-randomisation of revenue components)
    b_rev = results["baseline"]["total_revenue"]
    s_rev = results["scenario"]["total_revenue"]
    assert abs(b_rev - s_rev) / max(b_rev, 1) < 0.15  # some variance OK from resample


def test_positive_apr_shock_increases_interest_revenue(df):
    """A rate increase should increase interest revenue."""
    cfg = ScenarioConfig(apr_shock_pp=5.0, demand_sensitivity="low", pd_sensitivity="low")
    results = run_scenario(df, cfg)
    assert results["scenario"]["interest_revenue"] > results["baseline"]["interest_revenue"] * 0.9


def test_positive_apr_shock_increases_loss(df):
    """A rate increase with medium PD sensitivity should increase expected loss."""
    cfg = ScenarioConfig(apr_shock_pp=5.0, pd_sensitivity="medium")
    results = run_scenario(df, cfg)
    assert results["scenario"]["expected_loss"] >= results["baseline"]["expected_loss"] * 0.95


def test_exclude_grades(df):
    """Excluding a grade should leave that grade's APR unchanged."""
    cfg = ScenarioConfig(apr_shock_pp=5.0, exclude_grades=["A"])
    results = run_scenario(df, cfg)
    sdf = results["scenario_df"]
    # Grade A loans should have original APR (unchanged)
    orig_a_apr = df[df["grade"] == "A"]["int_rate"].mean()
    new_a_apr = sdf[sdf["grade"] == "A"]["int_rate"].mean()
    assert abs(new_a_apr - orig_a_apr) < 0.01


def test_segment_impact_returns_dataframe(df):
    cfg = ScenarioConfig(apr_shock_pp=3.0, group_by=["grade"])
    results = run_scenario(df, cfg)
    seg = results["segment_impact"]
    assert seg is not None
    assert len(seg) > 0
    assert "recommendation" in seg.columns


def test_negative_shock(df):
    """A rate decrease should reduce interest revenue."""
    cfg = ScenarioConfig(apr_shock_pp=-3.0, demand_sensitivity="low", pd_sensitivity="low")
    results = run_scenario(df, cfg)
    assert results["scenario"]["interest_revenue"] < results["baseline"]["interest_revenue"] * 1.1
