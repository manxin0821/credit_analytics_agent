"""
Scenario Simulation Agent.
"""
from __future__ import annotations

import pandas as pd

from src.agents.base_agent import BaseAgent
from src.simulation.scenario_engine import run_scenario
from src.simulation.scenario_config import ScenarioConfig


class SimulationAgent(BaseAgent):
    name = "SimulationAgent"

    def _run(self, payload: dict) -> dict:
        df: pd.DataFrame = payload["df"]
        scenario: ScenarioConfig = payload.get("scenario_config", ScenarioConfig())

        results = run_scenario(df, scenario)

        # Build a human-readable summary of key deltas
        delta = results["delta"]
        delta_pct = results["delta_pct"]

        summary_lines = [
            f"APR shock: +{scenario.apr_shock_pp:.1f}pp",
            f"Total revenue delta: {delta.get('total_revenue', 0):+,.0f} "
            f"({delta_pct.get('total_revenue', 0)*100:+.1f}%)",
            f"Net revenue delta: {delta.get('net_revenue', 0):+,.0f} "
            f"({delta_pct.get('net_revenue', 0)*100:+.1f}%)",
            f"Expected loss delta: {delta.get('expected_loss', 0):+,.0f} "
            f"({delta_pct.get('expected_loss', 0)*100:+.1f}%)",
            f"Write-off rate delta: {delta.get('writeoff_rate', 0)*100:+.2f}pp",
            f"30-DPD rate delta: {delta.get('dpd30_rate', 0)*100:+.2f}pp",
        ]

        return {
            "simulation_results": results,
            "scenario_summary": "\n".join(summary_lines),
            "scenario_label": scenario.label,
        }

    def _summarise_output(self, result: dict) -> str:
        return result.get("scenario_summary", "")[:200]
