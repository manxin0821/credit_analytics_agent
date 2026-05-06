# Architecture — Agentic Credit Analytics Command Center

## System Overview

The platform is built as a **multi-agent orchestration system** where a Root Orchestrator coordinates specialised sub-agents, each with a single responsibility. This follows the principle of **separation of concerns**: no single agent holds business logic, data access, AND language model calls simultaneously.

---

## Agent Roles

### 1. Root Orchestrator (`orchestrator.py`)
- **Receives** raw natural language from the executive
- **Sequences** sub-agent calls in the correct pipeline order
- **Aggregates** results into a unified response for the UI
- Does NOT call the LLM directly

### 2. Question Interpreter Agent (`question_interpreter.py`)
- **Calls DeepSeek** with a structured system prompt
- Converts question → `intent_type` + `ScenarioConfig`
- Intent types: `scenario_simulation | cohort_analysis | funnel_analysis | time_series_analysis | segment_recommendation | general_question`
- **Fallback**: rule-based intent detection if LLM fails

### 3. Metric Agent (`metric_agent.py`)
- **Resolves** business metric names to canonical keys via `METRIC_REGISTRY`
- Prevents LLM hallucination of metric formulas
- Registry defined in `metric_definitions.py` with typed `MetricDef` dataclasses

### 4. Data Agent (`data_agent.py`)
- **Loads** loan portfolio from parquet or generates synthetic data
- **Applies** optional time/segment filters from interpreted intent
- Returns raw `pd.DataFrame` for downstream agents

### 5. Simulation Agent (`simulation_agent.py`)
- **Applies** APR shock (additive, in percentage points)
- **Models** demand elasticity (application volume reduction)
- **Models** PD sensitivity (probability of default uplift)
- **Re-derives** revenue and loss metrics on the modified portfolio

### 6. Validation Agent (`validation_agent.py`)
- **Checks** funnel ordering: Applications ≥ Approved ≥ Funded
- **Checks** revenue reconciliation: components sum to total
- **Checks** rate bounds: rates must be in [0, 1]
- **Flags** APR confusion: +5pp means additive, not multiplicative

### 7. Visualization Agent (`visualization_agent.py`)
- **Decides** which dashboard tab to activate based on intent
- Returns chart directives (chart type → tab mapping)
- Does NOT generate actual charts (that's in `charts.py`)

### 8. Recommendation Agent (`recommendation_agent.py`)
- **Calls DeepSeek** with structured analysis context
- Produces executive-ready markdown: Summary, Drivers, Risks, Action
- Temperature = 0.3 (slightly more creative than analytical agents)

---

## Data Flow

```
User Question
    │
    ▼
QuestionInterpreter ──[LLM call]──► intent_type + ScenarioConfig
    │
    ▼
MetricAgent ──────────────────────► resolved metric list
    │
    ▼
DataAgent ────────────────────────► portfolio DataFrame
    │
    ├──[if scenario]──► SimulationAgent ──► simulation_results
    │
    ├──[always]───────► ValidationAgent ──► validation_summary
    │
    ├──[always]───────► VisualizationAgent ─► target_tab
    │
    └──[always]───────► RecommendationAgent ─[LLM call]──► markdown recommendation
```

---

## Scenario Simulation Model

### APR Shock
```
new_int_rate = old_int_rate + apr_shock_pp   # ADDITIVE
```

### Demand Elasticity
```
vol_reduction = abs(apr_shock_pp) × demand_sensitivity_factor
n_apps_dropped = int(n_affected × vol_reduction)
```
Sensitivity factors: low=0.02, medium=0.05, high=0.10

### PD Uplift
```
new_pd = old_pd + abs(apr_shock_pp) × pd_delta_per_pp
```
Sensitivity factors: low=0.005, medium=0.015, high=0.030

### Revenue Re-derivation
```
interest_revenue = loan_amnt × (int_rate / 100) × (term / 12) × utilization
```

### Expected Loss
```
EL = PD × LGD × EAD
   = pd_score × 0.60 × loan_amnt
```

---

## LLM Usage Pattern

All LLM calls go through `src/utils/llm_client.py`:
- Uses `openai.OpenAI` client pointed at DeepSeek's base URL
- `DEEPSEEK_API_KEY` and `DEEPSEEK_MODEL` from environment
- `extract_json()` handles responses with/without code fences
- All agents degrade gracefully if LLM is unavailable (rule-based fallbacks)

---

## Metric Registry Pattern

```python
# All metrics are typed and centrally defined
@dataclass
class MetricDef:
    key: str
    label: str
    unit: str          # count | usd | pct | ratio
    category: str      # funnel | revenue | loss
    compute: Callable[[pd.DataFrame], float]
    aliases: list[str]

# The Metric Agent resolves business names to canonical keys
resolve_metric("applications") → MetricDef(key="n_applications", ...)
```

This ensures LLM can never hallucinate a metric formula — it only references registry keys.

---

## Design Decisions

| Decision | Rationale |
|----------|-----------|
| No LangGraph | Simpler, easier to debug, less dependency overhead |
| Pydantic ScenarioConfig | Type safety, validation, JSON serialisation |
| Synthetic data fallback | App runs fully offline without data download |
| Cached Streamlit data | Avoids re-generating 50K loans on every interaction |
| DeepSeek over OpenAI | Cost-effective, OpenAI-compatible API |
| Additive APR shock | "5pp" = +5 percentage points, NOT ×1.05 |
