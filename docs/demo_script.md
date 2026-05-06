# Demo Script — Agentic Credit Analytics Command Center

## Setup (2 minutes before demo)

```bash
# Terminal
cd agentic_credit_analytics
streamlit run app.py
# Open browser at http://localhost:8501
```

---

## Demo Flow (~15 minutes)

### Scene 1: Baseline Portfolio Overview (2 min)

**Show:** Overview tab

**Say:**  
> "This is the Agentic Credit Analytics Command Center — an executive dashboard backed by a multi-agent AI system. The left side shows the live portfolio dashboard. The right side is the AI copilot."

**Point to KPIs:**
- 50,000 applications → [X]K funded
- $[X]M booked balance
- Average APR: ~12%
- Write-off rate: [X]%

**Show:** Grade breakdown chart + APR distribution

---

### Scene 2: APR Scenario Question (4 min)

**Type in copilot:**
```
If APR increases by 5 percentage points, what happens to revenue and loss?
```

**While agents run, narrate:**
> "Watch the Agent Trace tab — you can see each agent in the pipeline executing in sequence: Question Interpreter, Metric Agent, Data Agent, Simulation Agent, Validation Agent, Recommendation Agent."

**After response:**
- Switch to **Scenario Lab** tab (auto-suggested by AI)
- Show: Revenue waterfall chart — baseline vs scenario
- Show: KPI cards with delta indicators
- Point out: "Total revenue went up due to higher interest rates, but net revenue may have declined due to higher defaults — that's the trade-off the board needs to understand."

**Show recommendation card:**
> "The AI has automatically generated an executive-ready recommendation with key drivers and risks."

---

### Scene 3: Segment Exclusion Question (3 min)

**Type in copilot:**
```
Which segments should we exclude from the rate increase?
```

**After response:**
- Show **Segment Impact & Recommendations** table
- Point to the `recommendation` column: "⛔ Exclude / ⚠️ Monitor / ✅ Apply"
- Explain: "The AI ran the scenario for each grade and income band, identified which segments see the worst deterioration in write-off rates relative to revenue gain, and automatically flagged them."

---

### Scene 4: Cohort Deterioration (3 min)

**Type in copilot:**
```
Which vintage cohort shows early delinquency deterioration?
```

**After response:**
- Switch to **Cohort** tab (auto-navigated)
- Show the **heatmap**: Darker red = higher 30-DPD rate
- Point to specific vintages with high early MOB delinquency
- "This is critical for early warning — if MOB 3-6 is already red, that cohort is heading for charge-off."

---

### Scene 5: Revenue vs Net Revenue (2 min)

**Type in copilot:**
```
Why did total revenue increase but net revenue decline?
```

**Show:** 
- Revenue waterfall chart
- "Total revenue went up because interest income increased. Net revenue went down because the loss component grew faster — the PD uplift from higher rates pushed more borrowers into default."

---

### Scene 6: Agent Trace (1 min)

**Show Agent Trace tab:**
> "This is the full multi-agent execution log — every agent, how long it took, what it received and returned. This level of explainability is what separates agentic AI from black-box models."

Expand a few trace entries to show input/output.

---

## Key Talking Points

### For Technical Interviews

1. **Multi-agent orchestration without LangGraph** — show `orchestrator.py` and the sequential pipeline
2. **Type safety** — `ScenarioConfig` Pydantic model, `MetricDef` dataclass registry
3. **Hallucination prevention** — Metric Registry pattern ensures LLM can only reference validated metric keys
4. **Graceful degradation** — every agent has a rule-based fallback if LLM fails
5. **Validation layer** — cross-metric consistency checks before surfacing results

### For Business Stakeholders

1. **Natural language → analysis** — no SQL, no manual report building
2. **Scenario simulation** — "what if" in seconds, not days
3. **Segment recommendations** — AI tells you exactly which groups to protect
4. **Audit trail** — every recommendation is traceable to the data

---

## Common Questions & Answers

**Q: Is the API key safe?**  
A: Never hardcoded. Loaded from `.env` via `python-dotenv`. `.env` is in `.gitignore`.

**Q: What if DeepSeek is unavailable?**  
A: Every agent has a rule-based fallback. The dashboard data and scenario engine work independently of the LLM.

**Q: Can this use real Lending Club data?**  
A: Yes — place `loans.parquet` or `loans.csv` in `data/processed/` and the app will use it automatically.

**Q: How do you prevent LLM hallucination of metric formulas?**  
A: The Metric Registry pattern. The LLM only receives metric *names* and resolves them through the typed `MetricDef` registry. It can never invent a formula.
