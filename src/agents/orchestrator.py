"""
Root Orchestrator Agent.

Receives user question and coordinates the full multi-agent pipeline:
  1. QuestionInterpreter  → intent + ScenarioConfig
  2. MetricAgent          → metric resolution
  3. DataAgent            → load & filter portfolio
  4. SimulationAgent      → run scenario (if applicable)
  5. ValidationAgent      → consistency check
  6. VisualizationAgent   → chart directives
  7. RecommendationAgent  → executive summary
"""
from __future__ import annotations

import logging
from typing import Any

import pandas as pd

from src.agents.base_agent import AgentTrace
from src.agents.question_interpreter import QuestionInterpreterAgent
from src.agents.metric_agent import MetricAgent
from src.agents.data_agent import DataAgent
from src.agents.simulation_agent import SimulationAgent
from src.agents.validation_agent import ValidationAgent
from src.agents.visualization_agent import VisualizationAgent
from src.agents.recommendation_agent import RecommendationAgent
from src.metrics.metric_definitions import compute_all_metrics
from src.metrics.cohort_metrics import build_cohort_table, grade_segment_summary

logger = logging.getLogger(__name__)


class OrchestratorAgent:
    """
    Coordinates all sub-agents and aggregates their outputs into a
    single response dict that the Streamlit UI consumes.
    """

    def __init__(self) -> None:
        self.interpreter = QuestionInterpreterAgent()
        self.metric_agent = MetricAgent()
        self.data_agent = DataAgent()
        self.simulation_agent = SimulationAgent()
        self.validation_agent = ValidationAgent()
        self.viz_agent = VisualizationAgent()
        self.rec_agent = RecommendationAgent()

        self.traces: list[AgentTrace] = []

    def run(self, question: str) -> dict[str, Any]:
        """
        Full pipeline execution.

        Parameters
        ----------
        question : str
            Raw natural-language question from the executive.

        Returns
        -------
        dict with keys:
            - traces: list of AgentTrace dicts
            - recommendation: str
            - target_tab: str
            - simulation_results: dict | None
            - scenario_config: ScenarioConfig
            - baseline_metrics: dict
            - cohort_table: pd.DataFrame | None
            - segment_impact: pd.DataFrame | None
            - validation_summary: str
        """
        self.traces = []

        # ── Step 1: Interpret question ─────────────────────────────────────────
        interp_result = self.interpreter.run({"question": question})
        self._collect_trace(interp_result)
        if not interp_result["success"]:
            return self._error_response("QuestionInterpreter failed", interp_result)

        intent_type = interp_result["intent_type"]
        scenario_config = interp_result["scenario_config"]
        entities = interp_result.get("entities", {})

        # ── Step 2: Metric resolution ──────────────────────────────────────────
        metric_result = self.metric_agent.run({
            "metrics": entities.get("metrics", [])
        })
        self._collect_trace(metric_result)

        # ── Step 3: Load data ──────────────────────────────────────────────────
        data_result = self.data_agent.run({"entities": entities})
        self._collect_trace(data_result)
        if not data_result["success"]:
            return self._error_response("DataAgent failed", data_result)

        df: pd.DataFrame = data_result["df"]

        # ── Step 4: Baseline metrics ───────────────────────────────────────────
        baseline_metrics = compute_all_metrics(df)

        # ── Step 5: Simulation (if scenario) ──────────────────────────────────
        simulation_results = None
        if intent_type in ("scenario_simulation", "segment_recommendation") and scenario_config.apr_shock_pp != 0:
            sim_result = self.simulation_agent.run({
                "df": df,
                "scenario_config": scenario_config,
            })
            self._collect_trace(sim_result)
            if sim_result["success"]:
                simulation_results = sim_result["simulation_results"]

        # ── Step 6: Cohort table ───────────────────────────────────────────────
        cohort_table = None
        if intent_type in ("cohort_analysis", "general_question"):
            try:
                cohort_table = build_cohort_table(df, metric_col="dpd30")
            except Exception as exc:
                logger.warning("Cohort table build failed: %s", exc)

        # ── Step 7: Validation ─────────────────────────────────────────────────
        val_metrics = simulation_results["scenario"] if simulation_results else baseline_metrics
        val_result = self.validation_agent.run({
            "metrics": val_metrics,
            "scenario_config": scenario_config.model_dump(),
        })
        self._collect_trace(val_result)

        # ── Step 8: Visualization directives ──────────────────────────────────
        viz_result = self.viz_agent.run({"intent_type": intent_type})
        self._collect_trace(viz_result)

        # ── Step 9: Build analysis context for recommendation ──────────────────
        analysis_context = self._build_analysis_context(
            baseline_metrics, simulation_results, intent_type, scenario_config
        )

        # ── Step 10: Recommendation ────────────────────────────────────────────
        rec_result = self.rec_agent.run({
            "question": question,
            "intent_type": intent_type,
            "analysis_context": analysis_context,
        })
        self._collect_trace(rec_result)

        # ── Segment impact ─────────────────────────────────────────────────────
        segment_impact = None
        if simulation_results:
            segment_impact = simulation_results.get("segment_impact")

        grade_summary = grade_segment_summary(df)

        return {
            "success": True,
            "question": question,
            "intent_type": intent_type,
            "traces": [t.to_dict() for t in self.traces],
            "recommendation": rec_result.get("recommendation", ""),
            "target_tab": viz_result.get("target_tab", "Overview"),
            "chart_directives": viz_result.get("chart_directives", []),
            "simulation_results": simulation_results,
            "scenario_config": scenario_config,
            "baseline_metrics": baseline_metrics,
            "cohort_table": cohort_table,
            "segment_impact": segment_impact,
            "grade_summary": grade_summary,
            "validation_summary": val_result.get("validation_summary", ""),
            "validation_passed": val_result.get("validation_passed", True),
        }

    def _collect_trace(self, result: dict) -> None:
        trace = result.get("trace")
        if trace:
            self.traces.append(trace)

    def _build_analysis_context(
        self,
        baseline: dict,
        simulation: dict | None,
        intent_type: str,
        scenario_config: Any,
    ) -> str:
        lines = [
            f"Portfolio: {baseline.get('n_funded', 0):,.0f} funded accounts, "
            f"${baseline.get('booked_balance', 0)/1e6:.1f}M booked balance",
            f"Total Revenue: ${baseline.get('total_revenue', 0)/1e6:.2f}M | "
            f"Net Revenue: ${baseline.get('net_revenue', 0)/1e6:.2f}M",
            f"Write-off Rate: {baseline.get('writeoff_rate', 0)*100:.2f}% | "
            f"30-DPD Rate: {baseline.get('dpd30_rate', 0)*100:.2f}%",
        ]

        if simulation:
            delta = simulation.get("delta", {})
            lines += [
                "",
                f"SCENARIO: APR +{scenario_config.apr_shock_pp:.1f}pp",
                f"Revenue delta: ${delta.get('total_revenue', 0)/1e3:+.0f}K",
                f"Net revenue delta: ${delta.get('net_revenue', 0)/1e3:+.0f}K",
                f"Expected loss delta: ${delta.get('expected_loss', 0)/1e3:+.0f}K",
                f"Write-off rate delta: {delta.get('writeoff_rate', 0)*100:+.2f}pp",
            ]

        return "\n".join(lines)

    def _error_response(self, msg: str, result: dict) -> dict:
        return {
            "success": False,
            "error": msg,
            "traces": [t.to_dict() for t in self.traces],
            "recommendation": f"⚠️ Analysis failed: {result.get('error', msg)}",
            "target_tab": "Overview",
            "chart_directives": [],
            "simulation_results": None,
            "baseline_metrics": {},
            "cohort_table": None,
            "segment_impact": None,
            "grade_summary": None,
            "validation_summary": "",
            "validation_passed": False,
        }
