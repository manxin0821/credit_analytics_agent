"""
Validation Agent — checks metric consistency and scenario config sanity.
"""
from __future__ import annotations

from src.agents.base_agent import BaseAgent
from src.utils.validation import validate_metrics, validate_scenario_config, ValidationResult


class ValidationAgent(BaseAgent):
    name = "ValidationAgent"

    def _run(self, payload: dict) -> dict:
        metrics: dict = payload.get("metrics", {})
        scenario_config: dict = payload.get("scenario_config", {})

        metric_vr: ValidationResult = validate_metrics(metrics)
        scenario_vr: ValidationResult = validate_scenario_config(scenario_config)

        combined_passed = metric_vr.passed and scenario_vr.passed
        issues = metric_vr.issues + scenario_vr.issues
        warnings = metric_vr.warnings + scenario_vr.warnings

        return {
            "validation_passed": combined_passed,
            "issues": issues,
            "warnings": warnings,
            "metric_validation": metric_vr,
            "scenario_validation": scenario_vr,
            "validation_summary": (
                metric_vr.summary() + "\n\nScenario config:\n" + scenario_vr.summary()
            ),
        }
