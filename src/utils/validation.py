"""
Cross-metric consistency validation utilities.
Used by the Validation Agent.
"""
from __future__ import annotations

import math
from dataclasses import dataclass, field


@dataclass
class ValidationResult:
    passed: bool = True
    issues: list[str] = field(default_factory=list)
    warnings: list[str] = field(default_factory=list)

    def fail(self, msg: str) -> None:
        self.passed = False
        self.issues.append(msg)

    def warn(self, msg: str) -> None:
        self.warnings.append(msg)

    def summary(self) -> str:
        lines = []
        if self.passed:
            lines.append("✅ All validation checks passed.")
        else:
            lines.append(f"❌ {len(self.issues)} validation issue(s) found.")
        for issue in self.issues:
            lines.append(f"  • FAIL: {issue}")
        for w in self.warnings:
            lines.append(f"  ⚠ WARN: {w}")
        return "\n".join(lines)


def validate_metrics(metrics: dict[str, float]) -> ValidationResult:
    """
    Run consistency checks on a computed metrics dict.
    """
    vr = ValidationResult()

    def _get(key: str) -> float:
        return metrics.get(key, float("nan"))

    # 1. Funnel counts must be logically ordered
    n_app = _get("n_applications")
    n_appr = _get("n_approved")
    n_fund = _get("n_funded")

    if not math.isnan(n_appr) and not math.isnan(n_app) and n_appr > n_app:
        vr.fail(f"n_approved ({n_appr:.0f}) > n_applications ({n_app:.0f})")
    if not math.isnan(n_fund) and not math.isnan(n_appr) and n_fund > n_appr:
        vr.fail(f"n_funded ({n_fund:.0f}) > n_approved ({n_appr:.0f})")

    # 2. Revenue components must sum to total revenue
    components = ["interest_revenue", "interchange_revenue", "fee_revenue", "late_fee_revenue"]
    comp_sum = sum(_get(c) for c in components if not math.isnan(_get(c)))
    total_rev = _get("total_revenue")
    if not math.isnan(total_rev) and not math.isnan(comp_sum):
        if abs(comp_sum - total_rev) / max(total_rev, 1) > 0.05:
            vr.fail(
                f"Revenue components sum ({comp_sum:,.0f}) does not match "
                f"total_revenue ({total_rev:,.0f}). Difference > 5%."
            )

    # 3. Write-off rate = write-off accounts / funded accounts
    wo_rate = _get("writeoff_rate")
    wo_count = _get("writeoff_count")
    if not math.isnan(wo_rate) and not math.isnan(n_fund) and n_fund > 0:
        implied = wo_count / n_fund
        if abs(implied - wo_rate) > 0.01:
            vr.warn(
                f"writeoff_rate ({wo_rate:.4f}) ≠ writeoff_count/n_funded "
                f"({implied:.4f}). May indicate rounding."
            )

    # 4. No negative counts or rates
    for key in ["n_applications", "n_approved", "n_funded", "writeoff_count"]:
        val = _get(key)
        if not math.isnan(val) and val < 0:
            vr.fail(f"{key} is negative ({val}).")

    for key in ["approval_rate", "funding_rate", "writeoff_rate", "dpd30_rate", "dpd90_rate", "loss_rate"]:
        val = _get(key)
        if not math.isnan(val) and (val < 0 or val > 1):
            vr.warn(f"{key} = {val:.4f} is outside [0,1].")

    # 5. Net revenue should be less than total revenue
    net_rev = _get("net_revenue")
    if not math.isnan(net_rev) and not math.isnan(total_rev) and net_rev > total_rev:
        vr.warn(f"net_revenue ({net_rev:,.0f}) > total_revenue ({total_rev:,.0f}). Check loss subtraction.")

    return vr


def validate_scenario_config(config: dict) -> ValidationResult:
    """
    Validate a scenario config dict for common mistakes.
    """
    vr = ValidationResult()

    apr_shock = config.get("apr_shock_pp", 0)
    if abs(apr_shock) > 20:
        vr.warn(f"apr_shock_pp={apr_shock} is very large. Did you mean percentage POINTS?")

    lgd = config.get("lgd", 0.60)
    if lgd < 0 or lgd > 1:
        vr.fail(f"lgd={lgd} is outside [0,1].")

    return vr
