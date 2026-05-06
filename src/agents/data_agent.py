"""
Data Agent — loads and filters the portfolio DataFrame.
"""
from __future__ import annotations

import pandas as pd

from src.agents.base_agent import BaseAgent
from src.data.load_data import load_loans, filter_funded


class DataAgent(BaseAgent):
    name = "DataAgent"

    def _run(self, payload: dict) -> dict:
        df = load_loans()

        # Apply optional filters from intent
        entities = payload.get("entities", {})
        segment_filter = entities.get("segment_filter", "")
        time_filter = entities.get("time_filter", "")

        if time_filter and "application_date" in df.columns:
            try:
                parts = time_filter.split("/")
                if len(parts) == 2:
                    df = df[
                        (df["application_date"] >= parts[0]) &
                        (df["application_date"] <= parts[1])
                    ]
            except Exception:
                pass  # silently skip malformed filters

        available_fields = list(df.columns)
        n_funded = int(df["funded"].sum())
        n_total = len(df)

        return {
            "df": df,
            "funded_df": filter_funded(df),
            "available_fields": available_fields,
            "n_total": n_total,
            "n_funded": n_funded,
        }

    def _summarise_output(self, result: dict) -> str:
        return f"n_total={result.get('n_total')}, n_funded={result.get('n_funded')}"
