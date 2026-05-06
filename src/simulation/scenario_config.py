"""
Scenario configuration schema (Pydantic v2).
"""
from __future__ import annotations

from typing import Literal, Optional
from pydantic import BaseModel, Field


class ScenarioConfig(BaseModel):
    """
    Fully-typed scenario specification parsed from user natural language.
    """
    apr_shock_pp: float = Field(
        default=0.0,
        description="APR shock in percentage POINTS (additive). +5 means APR increases by 5pp.",
    )
    scope: str = Field(
        default="all_loans",
        description="Scope of scenario: 'all_loans' or a filter expression.",
    )
    lgd: float = Field(
        default=0.60,
        ge=0.0, le=1.0,
        description="Loss Given Default assumption.",
    )
    demand_sensitivity: Literal["low", "medium", "high"] = Field(
        default="medium",
        description="How much higher APR reduces application volume.",
    )
    pd_sensitivity: Literal["low", "medium", "high"] = Field(
        default="low",
        description="How much higher APR increases probability of default.",
    )
    group_by: list[str] = Field(
        default_factory=lambda: ["grade", "term", "income_band"],
        description="Dimensions to break down results by.",
    )
    metrics: list[str] = Field(
        default_factory=lambda: [
            "applications",
            "funding_rate",
            "interest_revenue",
            "expected_loss",
            "net_revenue",
            "dpd30_rate",
            "dpd90_rate",
            "writeoff_rate",
        ],
        description="Metrics to compute in the scenario run.",
    )
    exclude_grades: list[str] = Field(
        default_factory=list,
        description="Risk grades to exclude from the rate increase.",
    )
    exclude_income_bands: list[str] = Field(
        default_factory=list,
        description="Income bands to exclude from the rate increase.",
    )
    label: str = Field(
        default="Scenario",
        description="Human-readable label for this scenario.",
    )

    model_config = {"extra": "allow"}


# ── Default baseline scenario ─────────────────────────────────────────────────
BASELINE_SCENARIO = ScenarioConfig(
    apr_shock_pp=0.0,
    label="Baseline",
)
