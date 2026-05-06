"""
Visualization Agent — decides which dashboard tab to highlight and
prepares chart-ready data payloads.
"""
from __future__ import annotations

from src.agents.base_agent import BaseAgent

INTENT_TO_TAB = {
    "scenario_simulation": "Scenario Lab",
    "cohort_analysis": "Cohort",
    "funnel_analysis": "Funnel",
    "time_series_analysis": "Time Series",
    "segment_recommendation": "Scenario Lab",
    "general_question": "Overview",
}


class VisualizationAgent(BaseAgent):
    name = "VisualizationAgent"

    def _run(self, payload: dict) -> dict:
        intent_type = payload.get("intent_type", "general_question")
        target_tab = INTENT_TO_TAB.get(intent_type, "Overview")

        chart_directives: list[dict] = []

        if intent_type == "scenario_simulation":
            chart_directives = [
                {"chart": "revenue_waterfall", "tab": "Scenario Lab"},
                {"chart": "scenario_delta_bar", "tab": "Scenario Lab"},
                {"chart": "segment_impact_table", "tab": "Scenario Lab"},
            ]
        elif intent_type == "cohort_analysis":
            chart_directives = [
                {"chart": "cohort_heatmap", "tab": "Cohort"},
                {"chart": "delinquency_progression", "tab": "Cohort"},
            ]
        elif intent_type == "funnel_analysis":
            chart_directives = [
                {"chart": "funnel_chart", "tab": "Funnel"},
                {"chart": "funnel_kpis", "tab": "Funnel"},
            ]
        elif intent_type == "time_series_analysis":
            chart_directives = [
                {"chart": "time_series_revenue", "tab": "Time Series"},
                {"chart": "time_series_delinquency", "tab": "Time Series"},
            ]
        elif intent_type == "segment_recommendation":
            chart_directives = [
                {"chart": "segment_impact_table", "tab": "Scenario Lab"},
                {"chart": "rar_by_grade", "tab": "Scenario Lab"},
            ]

        return {
            "target_tab": target_tab,
            "chart_directives": chart_directives,
        }
