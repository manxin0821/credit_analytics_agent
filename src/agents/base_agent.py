"""
Base agent class providing common infrastructure for all agents.
"""
from __future__ import annotations

import logging
import time
from abc import ABC, abstractmethod
from dataclasses import dataclass, field
from typing import Any


@dataclass
class AgentTrace:
    """Execution trace entry for a single agent run."""
    agent_name: str
    input_summary: str
    output_summary: str
    duration_ms: float
    success: bool
    error: str | None = None
    metadata: dict = field(default_factory=dict)

    def to_dict(self) -> dict:
        return {
            "agent": self.agent_name,
            "input": self.input_summary,
            "output": self.output_summary,
            "duration_ms": round(self.duration_ms, 1),
            "success": self.success,
            "error": self.error,
            **self.metadata,
        }


class BaseAgent(ABC):
    """
    Abstract base for all agents in the system.

    Subclasses implement `_run(payload)` and return an output dict.
    The `run()` method wraps execution with timing, logging, and error handling.
    """

    name: str = "BaseAgent"

    def __init__(self) -> None:
        self.logger = logging.getLogger(f"agent.{self.name}")
        self._last_trace: AgentTrace | None = None

    def run(self, payload: Any) -> dict:
        """
        Execute the agent and return results with a trace.

        Always returns a dict with at least:
          - 'success': bool
          - 'trace': AgentTrace
        """
        start = time.perf_counter()
        self.logger.info("[%s] Starting", self.name)
        try:
            result = self._run(payload)
            elapsed = (time.perf_counter() - start) * 1000
            trace = AgentTrace(
                agent_name=self.name,
                input_summary=self._summarise_input(payload),
                output_summary=self._summarise_output(result),
                duration_ms=elapsed,
                success=True,
            )
            self._last_trace = trace
            self.logger.info("[%s] Done in %.0f ms", self.name, elapsed)
            return {"success": True, "trace": trace, **result}
        except Exception as exc:
            elapsed = (time.perf_counter() - start) * 1000
            self.logger.exception("[%s] Failed: %s", self.name, exc)
            trace = AgentTrace(
                agent_name=self.name,
                input_summary=self._summarise_input(payload),
                output_summary="",
                duration_ms=elapsed,
                success=False,
                error=str(exc),
            )
            self._last_trace = trace
            return {"success": False, "trace": trace, "error": str(exc)}

    @abstractmethod
    def _run(self, payload: Any) -> dict:
        ...

    def _summarise_input(self, payload: Any) -> str:
        if isinstance(payload, str):
            return payload[:120]
        if isinstance(payload, dict):
            keys = list(payload.keys())
            return f"dict({', '.join(keys[:5])})"
        return str(type(payload).__name__)

    def _summarise_output(self, result: dict) -> str:
        keys = [k for k in result if k != "trace"]
        return f"keys={keys[:5]}"
