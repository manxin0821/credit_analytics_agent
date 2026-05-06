# Agentic Credit Analytics Command Center
check this:https://creditanalyticsagent.streamlit.app

> **Multi-agent AI analytics platform for consumer lending portfolios.**  
> Executive-facing dashboard + AI copilot powered by DeepSeek.

![Python](https://img.shields.io/badge/python-3.10%2B-blue)
![Streamlit](https://img.shields.io/badge/streamlit-1.35%2B-red)
![DeepSeek](https://img.shields.io/badge/LLM-DeepSeek-orange)
![License](https://img.shields.io/badge/license-MIT-green)

---

## Overview

This project demonstrates a **production-quality multi-agent AI system** applied to credit/lending analytics. Executives interact with a natural-language copilot that:

1. **Interprets** questions about the loan portfolio
2. **Runs** scenario simulations (e.g., APR shocks)
3. **Validates** results for mathematical consistency
4. **Updates** the dashboard automatically
5. **Generates** executive-ready recommendations

---

## Architecture

```
User Question
     │
     ▼
┌─────────────────────────────────────────┐
│         Root Orchestrator Agent          │
└──────────────┬──────────────────────────┘
               │
    ┌──────────┼──────────────────────┐
    ▼          ▼          ▼           ▼
Question   Metric     Data        Risk
Interpreter  Agent    Agent       Model Agent
    │
    ▼
Simulation Agent  ──►  Validation Agent
    │
    ▼
Visualization Agent  ──►  Recommendation Agent
```

See [docs/architecture.md](docs/architecture.md) for full details.

---

## Quick Start

### 1. Clone & Install

```bash
git clone <repo>
cd agentic_credit_analytics
pip install -r requirements.txt
```

### 2. Configure API Key

```bash
cp .env.example .env
# Edit .env and add your DeepSeek API key:
# DEEPSEEK_API_KEY=your_key_here
```

### 3. Generate Synthetic Data (optional)

The app auto-generates synthetic data on first run. To pre-generate:

```bash
python src/data/synthetic_data.py
```

### 4. Run the App

```bash
streamlit run app.py
```

Navigate to `http://localhost:8501`

---

## Dashboard Tabs

| Tab | Description |
|-----|-------------|
| **Overview** | Portfolio KPIs, revenue & loss summary, grade breakdown |
| **Funnel** | Application → Approval → Funding funnel analysis |
| **Cohort** | Vintage × MOB delinquency heatmap |
| **Time Series** | Monthly portfolio trends |
| **Scenario Lab** | APR shock simulation with segment-level impact |
| **Agent Trace** | Real-time multi-agent execution log |

---

## AI Copilot — Example Questions

```
"If APR increases by 5 percentage points, what happens to revenue and loss?"
"Which segments should we exclude from the rate increase?"
"Which vintage cohort shows early delinquency deterioration?"
"Why did total revenue increase but net revenue decline?"
"What is the risk-adjusted revenue by grade?"
```

---

## Project Structure

```
agentic_credit_analytics/
├── app.py                    ← Streamlit entry point
├── requirements.txt
├── .env.example
├── config/
│   ├── settings.py           ← Environment config
│   └── metrics.yaml          ← Canonical metric definitions
├── src/
│   ├── agents/               ← Multi-agent system
│   │   ├── orchestrator.py
│   │   ├── question_interpreter.py
│   │   ├── metric_agent.py
│   │   ├── data_agent.py
│   │   ├── simulation_agent.py
│   │   ├── validation_agent.py
│   │   ├── visualization_agent.py
│   │   └── recommendation_agent.py
│   ├── data/
│   │   ├── load_data.py
│   │   └── synthetic_data.py
│   ├── metrics/
│   │   ├── metric_definitions.py
│   │   └── cohort_metrics.py
│   ├── simulation/
│   │   ├── scenario_config.py
│   │   └── scenario_engine.py
│   ├── ui/
│   │   ├── charts.py
│   │   └── components.py
│   └── utils/
│       ├── llm_client.py
│       ├── logging.py
│       └── validation.py
├── tests/
│   ├── test_metrics.py
│   ├── test_scenario_engine.py
│   └── test_validation.py
└── docs/
    ├── architecture.md
    ├── metric_dictionary.md
    └── demo_script.md
```

---

## Running Tests

```bash
pytest tests/ -v
```

---

## Tech Stack

| Component | Technology |
|-----------|-----------|
| Frontend | Streamlit 1.35+ |
| LLM | DeepSeek (via OpenAI-compatible API) |
| Data | Synthetic Lending-Club-style data |
| Charts | Plotly |
| ML Models | Scikit-learn / LightGBM |
| Validation | Pydantic v2 |

---

## Environment Variables

| Variable | Default | Description |
|----------|---------|-------------|
| `DEEPSEEK_API_KEY` | (required) | Your DeepSeek API key |
| `DEEPSEEK_MODEL` | `deepseek-chat` | Model name |

---

## License

MIT
