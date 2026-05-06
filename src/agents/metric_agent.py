"""
Metric Definition Agent.

Maps business language to standardised metric keys and protects
against LLM hallucination by always resolving through the registry.
"""
from __future__ import annotations

from src.agents.base_agent import BaseAgent
from src.metrics.metric_definitions import METRIC_REGISTRY, resolve_metric


class MetricAgent(BaseAgent):
    name = "MetricAgent"

    def _run(self, payload: dict) -> dict:
        requested = payload.get("metrics", [])
        resolved = []
        unknown = []

        for m in requested:
            mdef = resolve_metric(m)
            if mdef:
                resolved.append({
                    "key": mdef.key,
                    "label": mdef.label,
                    "unit": mdef.unit,
                    "category": mdef.category,
                })
            else:
                unknown.append(m)

        # If nothing resolved, return all metrics grouped by category
        if not resolved:
            resolved = [
                {"key": k, "label": v.label, "unit": v.unit, "category": v.category}
                for k, v in METRIC_REGISTRY.items()
                if k == v.key  # deduplicate aliases
            ]

        return {
            "resolved_metrics": resolved,
            "unknown_metrics": unknown,
            "n_resolved": len(resolved),
        }
