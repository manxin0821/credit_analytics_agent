"""
Recommendation Agent — generates executive-ready summaries using DeepSeek.
"""
from __future__ import annotations

import logging

from src.agents.base_agent import BaseAgent
from src.utils.llm_client import chat_completion

logger = logging.getLogger(__name__)

RECOMMENDATION_SYSTEM = """You are a Chief Credit Officer at a consumer lending firm.
You communicate in crisp, executive-ready language.

Given simulation results or analytical findings, produce a structured recommendation with:
1. **Executive Summary** (2-3 sentences max)
2. **Key Drivers** (bullet list, max 4 items)
3. **Risks** (bullet list, max 3 items)
4. **Recommended Action** (1 clear sentence)

Be specific with numbers. Use ↑ ↓ symbols for changes. Do NOT repeat the input data verbatim.
Format your response in clean Markdown.
"""


class RecommendationAgent(BaseAgent):
    name = "RecommendationAgent"

    def _run(self, payload: dict) -> dict:
        context = payload.get("analysis_context", "")
        question = payload.get("question", "")
        intent_type = payload.get("intent_type", "general_question")

        user_prompt = f"""
Question: {question}
Intent: {intent_type}

Analysis Context:
{context}

Generate an executive recommendation.
"""
        messages = [
            {"role": "system", "content": RECOMMENDATION_SYSTEM},
            {"role": "user", "content": user_prompt},
        ]

        recommendation = chat_completion(messages, temperature=0.3)

        return {
            "recommendation": recommendation,
            "intent_type": intent_type,
        }

    def _summarise_output(self, result: dict) -> str:
        rec = result.get("recommendation", "")
        return rec[:150] + "…" if len(rec) > 150 else rec
