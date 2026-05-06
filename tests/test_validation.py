"""
Tests for the validation utilities.
"""
import sys
from pathlib import Path
sys.path.insert(0, str(Path(__file__).resolve().parents[1]))

from src.utils.validation import validate_metrics, validate_scenario_config


def test_valid_metrics_passes():
    metrics = {
        "n_applications": 10000.0,
        "n_approved": 7000.0,
        "n_funded": 6000.0,
        "approval_rate": 0.70,
        "funding_rate": 0.857,
        "total_revenue": 5_000_000.0,
        "interest_revenue": 4_000_000.0,
        "interchange_revenue": 600_000.0,
        "fee_revenue": 300_000.0,
        "late_fee_revenue": 100_000.0,
        "writeoff_count": 300.0,
        "writeoff_rate": 0.05,
        "net_revenue": 4_200_000.0,
        "actual_loss": 800_000.0,
    }
    vr = validate_metrics(metrics)
    assert vr.passed


def test_funnel_violation():
    metrics = {
        "n_applications": 5000.0,
        "n_approved": 6000.0,  # MORE than applications!
        "n_funded": 4000.0,
    }
    vr = validate_metrics(metrics)
    assert not vr.passed
    assert any("n_approved" in issue for issue in vr.issues)


def test_negative_count():
    metrics = {"n_applications": -100.0, "n_approved": 0.0, "n_funded": 0.0}
    vr = validate_metrics(metrics)
    assert not vr.passed


def test_invalid_lgd():
    vr = validate_scenario_config({"lgd": 1.5})
    assert not vr.passed


def test_large_apr_warns():
    vr = validate_scenario_config({"apr_shock_pp": 50.0})
    assert len(vr.warnings) > 0
