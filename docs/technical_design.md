# Technical Design Document
## Agentic Credit Analytics Command Center

### 1. System Overview

A production-quality multi-agent AI analytics platform for consumer lending portfolios. The system enables executives to interact with a live loan portfolio dashboard through natural language, triggering automated scenario simulations, cohort analysis, and AI-generated recommendations.

---

### 2. Technology Stack

| Layer | Technology | Rationale |
|-------|-----------|-----------|
| Frontend | Streamlit 1.35+ | Rapid prototyping, Python-native, wide layout support |
| LLM | DeepSeek (`deepseek-chat`) | OpenAI-compatible API, cost-effective, strong reasoning |
| Data | Synthetic (Lending-Club-style) | Runs offline, no data download required |
| Charts | Plotly | Interactive, export-ready, dark-theme support |
| Schema | Pydantic v2 | Runtime type validation, JSON serialisation |
| ML | Scikit-learn / NumPy | PD scoring, scenario modelling |
| Testing | pytest | 20 unit tests across metrics, scenarios, validation |

---

### 3. Agent Pipeline

```
User → Orchestrator
         ├── QuestionInterpreter  [LLM] → intent + ScenarioConfig
         ├── MetricAgent          [Registry] → resolved metrics
         ├── DataAgent            [Parquet/Synthetic] → DataFrame
         ├── SimulationAgent      [Numerical] → scenario results
         ├── ValidationAgent      [Rules] → consistency check
         ├── VisualizationAgent   [Rules] → chart directives
         └── RecommendationAgent  [LLM] → executive markdown
```

Each agent extends `BaseAgent` which provides:
- Timed execution with `perf_counter`
- Structured `AgentTrace` output
- Graceful exception handling
- Input/output summarisation for the trace log

---

### 4. Data Model

#### Loan Record Fields
| Field | Type | Description |
|-------|------|-------------|
| `loan_id` | int | Unique identifier |
| `application_date` | datetime | Date of application |
| `application_month` | str | Period string (YYYY-MM) |
| `vintage_month` | str | Funding vintage period |
| `grade` | str | Risk grade A-G |
| `term` | int | Loan term in months (36 or 60) |
| `int_rate` | float | Annual interest rate (%) |
| `loan_amnt` | float | Loan amount ($) |
| `annual_inc` | float | Borrower annual income ($) |
| `income_band` | str | Income bracket |
| `purpose` | str | Loan purpose |
| `approved` | bool | Application approved |
| `funded` | bool | Loan funded |
| `mob` | int | Months on book |
| `pd_score` | float | Probability of default [0,1] |
| `charged_off` | bool | Loan charged off |
| `dpd30/60/90` | bool | Delinquency flags |
| `interest_revenue` | float | Simulated interest income |
| `interchange_revenue` | float | Simulated interchange |
| `origination_fee` | float | Origination fee |

#### ScenarioConfig Schema (Pydantic)
```python
class ScenarioConfig(BaseModel):
    apr_shock_pp: float          # Additive APR change in pp
    scope: str                   # Filter scope
    lgd: float                   # Loss Given Default
    demand_sensitivity: Literal["low","medium","high"]
    pd_sensitivity: Literal["low","medium","high"]
    group_by: list[str]          # Breakdown dimensions
    metrics: list[str]           # Metrics to compute
    exclude_grades: list[str]    # Grades excluded from shock
    exclude_income_bands: list[str]
    label: str                   # Human-readable label
```

---

### 5. Scenario Simulation Model

#### 5.1 APR Shock (Additive)
```
new_APR = old_APR + apr_shock_pp
```
**Important:** "+5pp" = additive increase, NOT multiplicative. This is validated explicitly by the Validation Agent.

#### 5.2 Demand Elasticity
```
volume_reduction = |apr_shock_pp| × demand_factor
demand_factor = { low: 2%, medium: 5%, high: 10% } per pp
```

#### 5.3 PD Uplift
```
new_PD = old_PD + |apr_shock_pp| × pd_factor
pd_factor = { low: 0.5%, medium: 1.5%, high: 3.0% } per pp
```

#### 5.4 Revenue Recomputation
```
interest_revenue = loan_amnt × (int_rate/100) × (term/12) × utilization
utilization ~ Uniform(0.55, 0.95)
```

#### 5.5 Expected Loss
```
EL = PD × LGD × EAD
   = pd_score × 0.60 × loan_amnt
```

---

### 6. Metric Registry Pattern

All metrics are defined as typed `MetricDef` objects in `metric_definitions.py`. The LLM can only reference metrics by key; it cannot hallucinate formulas because the actual computation always goes through the registry's `compute` callable.

```python
@dataclass
class MetricDef:
    key: str
    label: str
    unit: str       # count | usd | pct | ratio
    category: str   # funnel | revenue | loss
    compute: Callable[[pd.DataFrame], float]
    aliases: list[str]   # e.g. ["applications", "app_count"] → "n_applications"
```

---

### 7. Validation Rules

| Rule | Formula | Severity |
|------|---------|----------|
| Funnel order | n_approved ≤ n_applications | FAIL |
| Funnel order | n_funded ≤ n_approved | FAIL |
| Revenue reconciliation | components ≈ total (±5%) | FAIL |
| Write-off rate formula | writeoff_count / n_funded | WARN |
| Rate bounds | rates ∈ [0, 1] | WARN |
| APR confusion | shock > 20pp | WARN |
| LGD bounds | lgd ∈ [0, 1] | FAIL |

---

### 8. LLM Integration

Two agents use DeepSeek:

1. **QuestionInterpreter** (temperature=0.1)
   - System prompt enforces strict JSON output schema
   - Falls back to rule-based intent detection on parse failure
   - Correctly handles: "5pp", "5 percentage points", "increase by 5"

2. **RecommendationAgent** (temperature=0.3)
   - Generates structured executive markdown
   - Context includes baseline/scenario metric deltas
   - Output format: Summary → Key Drivers → Risks → Action

---

### 9. Performance Characteristics

| Operation | Typical Time | Notes |
|-----------|-------------|-------|
| Data load (synthetic) | ~2s | 50K loans generated once, cached |
| Metric computation | <100ms | Vectorised pandas operations |
| Scenario simulation | <500ms | Row drops + numpy recomputation |
| LLM call (interpret) | 1-3s | Depends on DeepSeek API latency |
| LLM call (recommend) | 2-5s | Longer response generation |
| Total pipeline | 5-10s | Full end-to-end orchestration |

---

### 10. Assumptions & Limitations

1. **Synthetic data** does not capture real credit correlations (bureau scores, macroeconomic cycles, vintage seasoning).
2. **Demand elasticity** is linear — real demand curves are non-linear.
3. **PD model** is based on simulated probabilities, not a calibrated logistic regression.
4. **Revenue utilization** (55-95%) is randomly sampled; real utilization depends on prepayment behaviour.
5. **Interchange revenue** is estimated at 1.5% of funded balance — varies by product type.
6. **No time decay** — scenario results are instantaneous, not multi-period projections.

---

### 11. Future Improvements

| Priority | Enhancement |
|----------|------------|
| High | Integrate real Lending Club data (Kaggle download) |
| High | Train calibrated LightGBM PD model on real data |
| High | Add FRED API integration for macro scenarios |
| Medium | Multi-period simulation (36-60 month vintage evolution) |
| Medium | Confidence intervals on scenario outputs |
| Medium | LangGraph-based parallel agent execution |
| Low | Real-time streaming from loan origination systems |
| Low | PDF export of executive recommendation |
