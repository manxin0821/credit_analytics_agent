"""
Canonical metric definitions registry.

Agents reference this module to resolve business metric names to
standardised computation functions, preventing LLM hallucination.
"""
from __future__ import annotations

from dataclasses import dataclass, field
from typing import Callable, Optional
import pandas as pd


@dataclass
class MetricDef:
    """Descriptor for a single metric."""
    key: str
    label: str
    unit: str                    # count | usd | pct | ratio
    category: str                # funnel | revenue | loss | cohort
    compute: Callable[[pd.DataFrame], float]
    description: str = ""
    aliases: list[str] = field(default_factory=list)


# ── Helper shortcuts ──────────────────────────────────────────────────────────

def _funded(df: pd.DataFrame) -> pd.DataFrame:
    return df[df["funded"] == True]


def _safe_div(a: float, b: float) -> float:
    return a / b if b else 0.0


# ── Funnel metrics ────────────────────────────────────────────────────────────

METRIC_REGISTRY: dict[str, MetricDef] = {}


def _reg(m: MetricDef) -> MetricDef:
    METRIC_REGISTRY[m.key] = m
    for alias in m.aliases:
        METRIC_REGISTRY[alias] = m
    return m


_reg(MetricDef(
    key="n_applications",
    label="Number of Applications",
    unit="count",
    category="funnel",
    compute=lambda df: float(len(df)),
    aliases=["applications", "app_count"],
))

_reg(MetricDef(
    key="n_approved",
    label="Number of Approved",
    unit="count",
    category="funnel",
    compute=lambda df: float(df["approved"].sum()),
    aliases=["approved_count"],
))

_reg(MetricDef(
    key="approval_rate",
    label="Approval Rate",
    unit="pct",
    category="funnel",
    compute=lambda df: _safe_div(float(df["approved"].sum()), len(df)),
    aliases=["apr_rate"],
))

_reg(MetricDef(
    key="n_funded",
    label="Number of Funded Accounts",
    unit="count",
    category="funnel",
    compute=lambda df: float(df["funded"].sum()),
    aliases=["funded_count"],
))

_reg(MetricDef(
    key="funding_rate",
    label="Funding Rate",
    unit="pct",
    category="funnel",
    compute=lambda df: _safe_div(float(df["funded"].sum()), float(df["approved"].sum())),
))

_reg(MetricDef(
    key="booked_balance",
    label="Booked Balance",
    unit="usd",
    category="funnel",
    compute=lambda df: float(_funded(df)["loan_amnt"].sum()),
))

_reg(MetricDef(
    key="avg_funded_amount",
    label="Average Funded Amount",
    unit="usd",
    category="funnel",
    compute=lambda df: float(_funded(df)["loan_amnt"].mean()) if df["funded"].any() else 0.0,
))

_reg(MetricDef(
    key="avg_apr",
    label="Average APR",
    unit="pct",
    category="funnel",
    compute=lambda df: float(_funded(df)["int_rate"].mean()) if df["funded"].any() else 0.0,
    aliases=["average_apr", "mean_apr"],
))

# ── Revenue metrics ───────────────────────────────────────────────────────────

_reg(MetricDef(
    key="interest_revenue",
    label="Interest Revenue",
    unit="usd",
    category="revenue",
    compute=lambda df: float(_funded(df)["interest_revenue"].sum()),
))

_reg(MetricDef(
    key="interchange_revenue",
    label="Interchange Revenue",
    unit="usd",
    category="revenue",
    compute=lambda df: float(_funded(df)["interchange_revenue"].sum()),
))

_reg(MetricDef(
    key="fee_revenue",
    label="Fee Revenue",
    unit="usd",
    category="revenue",
    compute=lambda df: float(_funded(df)["origination_fee"].sum()),
))

_reg(MetricDef(
    key="late_fee_revenue",
    label="Late Fee Revenue",
    unit="usd",
    category="revenue",
    compute=lambda df: float(df.get("late_fee_revenue", pd.Series(0.0)).sum()),
))

_reg(MetricDef(
    key="total_revenue",
    label="Total Revenue",
    unit="usd",
    category="revenue",
    compute=lambda df: (
        float(_funded(df)["interest_revenue"].sum()) +
        float(_funded(df)["interchange_revenue"].sum()) +
        float(_funded(df)["origination_fee"].sum()) +
        float(df.get("late_fee_revenue", pd.Series(0.0)).sum())
    ),
    aliases=["revenue"],
))

_reg(MetricDef(
    key="expected_loss",
    label="Expected Loss",
    unit="usd",
    category="loss",
    compute=lambda df: float((_funded(df)["pd_score"] * 0.60 * _funded(df)["loan_amnt"]).sum()),
    aliases=["el"],
))

_reg(MetricDef(
    key="actual_loss",
    label="Actual Loss",
    unit="usd",
    category="loss",
    compute=lambda df: float(_funded(df).loc[_funded(df)["charged_off"], "loan_amnt"].sum() * 0.60),
))

_reg(MetricDef(
    key="net_revenue",
    label="Net Revenue",
    unit="usd",
    category="revenue",
    compute=lambda df: (
        METRIC_REGISTRY["total_revenue"].compute(df) -
        METRIC_REGISTRY["actual_loss"].compute(df)
    ),
))

_reg(MetricDef(
    key="risk_adjusted_revenue",
    label="Risk-Adjusted Revenue",
    unit="usd",
    category="revenue",
    compute=lambda df: (
        METRIC_REGISTRY["total_revenue"].compute(df) -
        METRIC_REGISTRY["expected_loss"].compute(df)
    ),
    aliases=["rar"],
))

# ── Loss / delinquency metrics ────────────────────────────────────────────────

for _dpd_days, _col in [(30, "dpd30"), (60, "dpd60"), (90, "dpd90")]:
    _d = _dpd_days
    _c = _col

    _reg(MetricDef(
        key=f"dpd{_d}_count",
        label=f"{_d} DPD Account Count",
        unit="count",
        category="loss",
        compute=(lambda df, c=_c: float(_funded(df)[c].sum())),
        aliases=[f"{_d}_dpd_count"],
    ))

    _reg(MetricDef(
        key=f"dpd{_d}_rate",
        label=f"{_d} DPD Rate",
        unit="pct",
        category="loss",
        compute=(lambda df, c=_c: _safe_div(
            float(_funded(df)[c].sum()), float(df["funded"].sum())
        )),
        aliases=[f"{_d}_dpd_rate", f"dpd_{_d}_rate"],
    ))

_reg(MetricDef(
    key="writeoff_count",
    label="Write-Off Account Count",
    unit="count",
    category="loss",
    compute=lambda df: float(_funded(df)["charged_off"].sum()),
    aliases=["write_off_count", "chargeoff_count"],
))

_reg(MetricDef(
    key="writeoff_rate",
    label="Write-Off Rate",
    unit="pct",
    category="loss",
    compute=lambda df: _safe_div(
        float(_funded(df)["charged_off"].sum()), float(df["funded"].sum())
    ),
    aliases=["write_off_rate", "chargeoff_rate"],
))

_reg(MetricDef(
    key="writeoff_amount",
    label="Write-Off Amount",
    unit="usd",
    category="loss",
    compute=lambda df: float(_funded(df).loc[_funded(df)["charged_off"], "loan_amnt"].sum()),
))

_reg(MetricDef(
    key="writeoff_amount_rate",
    label="Write-Off Amount Rate",
    unit="pct",
    category="loss",
    compute=lambda df: _safe_div(
        float(_funded(df).loc[_funded(df)["charged_off"], "loan_amnt"].sum()),
        float(_funded(df)["loan_amnt"].sum()),
    ),
))

_reg(MetricDef(
    key="loss_rate",
    label="Loss Rate",
    unit="pct",
    category="loss",
    compute=lambda df: _safe_div(
        METRIC_REGISTRY["actual_loss"].compute(df),
        METRIC_REGISTRY["booked_balance"].compute(df),
    ),
))


def resolve_metric(name: str) -> Optional[MetricDef]:
    """Resolve a metric name (or alias) to a MetricDef. Returns None if unknown."""
    return METRIC_REGISTRY.get(name.lower().strip())


def compute_all_metrics(df: pd.DataFrame) -> dict[str, float]:
    """Compute every registered metric and return as a flat dict."""
    results: dict[str, float] = {}
    seen_keys: set[str] = set()
    for key, mdef in METRIC_REGISTRY.items():
        if mdef.key in seen_keys:
            continue
        seen_keys.add(mdef.key)
        try:
            results[mdef.key] = mdef.compute(df)
        except Exception as exc:
            results[mdef.key] = float("nan")
            import logging
            logging.getLogger(__name__).warning("Metric %s failed: %s", mdef.key, exc)
    return results
