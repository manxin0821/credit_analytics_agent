"""
Question Interpreter Agent.

Converts a natural-language question into:
  - structured intent (intent_type, entities, metrics_requested)
  - a ScenarioConfig if a scenario is implied
"""
from __future__ import annotations

import json
import logging

from src.agents.base_agent import BaseAgent
from src.simulation.scenario_config import ScenarioConfig
from src.utils.llm_client import chat_completion, extract_json

logger = logging.getLogger(__name__)

INTENT_TYPES = [
    "scenario_simulation",
    "cohort_analysis",
    "funnel_analysis",
    "time_series_analysis",
    "segment_recommendation",
    "general_question",
]

SYSTEM_PROMPT = """You are a financial analytics AI specialising in consumer lending / credit analytics.

Your task: Convert a user's natural-language question into a structured JSON response.

Rules:
1. "APR" means Annual Percentage Rate (interest rate). "5pp" or "5 percentage points" means ADDITIVE +5 (not multiply by 1.05).
2. All rates must be in decimal form for percentage fields (e.g. 0.05 = 5%).
3. Respond ONLY with valid JSON matching this schema — no extra text.

JSON Schema:
{
  "intent_type": "<one of: scenario_simulation | cohort_analysis | funnel_analysis | time_series_analysis | segment_recommendation | general_question>",
  "question_summary": "<concise restatement of the question>",
  "entities": {
    "metrics": ["<list of metric keys>"],
    "dimensions": ["<grade | term | income_band | vintage_month | etc>"],
    "time_filter": "<optional ISO date range>",
    "segment_filter": "<optional filter expression>"
  },
  "scenario_config": {
    "apr_shock_pp": 0,
    "scope": "all_loans",
    "lgd": 0.60,
    "demand_sensitivity": "medium",
    "pd_sensitivity": "low",
    "group_by": ["grade", "term", "income_band"],
    "metrics": [],
    "exclude_grades": [],
    "exclude_income_bands": [],
    "label": "Scenario"
  }
}
"""


class QuestionInterpreterAgent(BaseAgent):
    name = "QuestionInterpreter"

    def _run(self, payload: dict) -> dict:
        question = payload.get("question", "")
        if not question:
            raise ValueError("No question provided")

        messages = [
            {"role": "system", "content": SYSTEM_PROMPT},
            {"role": "user", "content": question},
        ]

        raw = chat_completion(messages, temperature=0.1, json_mode=False)
        logger.debug("Interpreter raw response: %s", raw[:300])

        try:
            parsed = extract_json(raw)
        except ValueError:
            logger.warning("JSON extraction failed, falling back to defaults")
            parsed = _default_interpretation(question)

        # Build ScenarioConfig from parsed scenario_config section
        scenario_data = parsed.get("scenario_config", {})
        try:
            scenario = ScenarioConfig(**scenario_data)
        except Exception:
            scenario = ScenarioConfig()

        return {
            "intent_type": parsed.get("intent_type", "general_question"),
            "question_summary": parsed.get("question_summary", question),
            "entities": parsed.get("entities", {}),
            "scenario_config": scenario,
            "raw_parsed": parsed,
        }


def _default_interpretation(question: str) -> dict:
    q_lower = question.lower()
    intent = "general_question"
    if any(w in q_lower for w in ["apr", "rate increase", "shock", "what if", "increase by"]):
        intent = "scenario_simulation"
    elif any(w in q_lower for w in ["cohort", "vintage", "early", "deterioration"]):
        intent = "cohort_analysis"
    elif any(w in q_lower for w in ["segment", "exclude", "which"]):
        intent = "segment_recommendation"
    elif any(w in q_lower for w in ["funnel", "application", "approval", "funding"]):
        intent = "funnel_analysis"

    return {
        "intent_type": intent,
        "question_summary": question,
        "entities": {"metrics": [], "dimensions": ["grade"]},
        "scenario_config": {"apr_shock_pp": 0},
    }
