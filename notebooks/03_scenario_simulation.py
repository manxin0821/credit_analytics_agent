"""
Notebook 03 — Scenario Simulation
====================================
Demonstrates the full APR shock simulation pipeline.
"""
# %%
import sys
from pathlib import Path
sys.path.insert(0, str(Path(__file__).resolve().parent.parent))

import pandas as pd
import numpy as np

from src.data.synthetic_data import generate_synthetic_loans
from src.simulation.scenario_config import ScenarioConfig
from src.simulation.scenario_engine import run_scenario
from src.utils.validation import validate_metrics, validate_scenario_config

print("=" * 60)
print("SCENARIO SIMULATION NOTEBOOK")
print("=" * 60)

df = generate_synthetic_loans(n=50_000, seed=42)

# ── Scenario 1: APR +5pp, medium sensitivity ─────────────────────────────────
print("\n--- Scenario 1: APR +5pp (Medium Demand & PD Sensitivity) ---")
cfg1 = ScenarioConfig(
    apr_shock_pp=5.0,
    demand_sensitivity="medium",
    pd_sensitivity="medium",
    group_by=["grade"],
    label="APR +5pp Base Case",
)

vr_cfg = validate_scenario_config(cfg1.model_dump())
print("Config validation:", vr_cfg.summary())

results1 = run_scenario(df, cfg1)
b, s, d = results1["baseline"], results1["scenario"], results1["delta"]

print(f"\n{'Metric':<30} {'Baseline':>15} {'Scenario':>15} {'Delta':>15}")
print("-" * 75)
for k, label in [
    ("total_revenue", "Total Revenue"),
    ("interest_revenue", "Interest Revenue"),
    ("net_revenue", "Net Revenue"),
    ("expected_loss", "Expected Loss"),
    ("actual_loss", "Actual Loss"),
]:
    print(f"{label:<30} ${b[k]/1e6:>14.2f}M ${s[k]/1e6:>14.2f}M ${d[k]/1e3:>+13.0f}K")

print(f"\n{'Write-off Rate':<30} {b['writeoff_rate']*100:>14.2f}% {s['writeoff_rate']*100:>14.2f}% {d['writeoff_rate']*100:>+14.2f}pp")
print(f"{'30-DPD Rate':<30} {b['dpd30_rate']*100:>14.2f}% {s['dpd30_rate']*100:>14.2f}% {d['dpd30_rate']*100:>+14.2f}pp")
print(f"{'Applications':<30} {b['n_applications']:>15,.0f} {s['n_applications']:>15,.0f} {d['n_applications']:>+15,.0f}")

# Validate scenario output
vr_metrics = validate_metrics(results1["scenario"])
print("\nMetric validation:", vr_metrics.summary())

# ── Scenario 2: Grade exclusion ───────────────────────────────────────────────
print("\n--- Scenario 2: APR +5pp, Exclude Grades A & B ---")
cfg2 = ScenarioConfig(
    apr_shock_pp=5.0,
    demand_sensitivity="medium",
    pd_sensitivity="medium",
    exclude_grades=["A", "B"],
    label="APR +5pp, excl A/B",
)
results2 = run_scenario(df, cfg2)
b2, s2, d2 = results2["baseline"], results2["scenario"], results2["delta"]
print(f"Net Revenue delta: ${d2['net_revenue']/1e3:+.0f}K (cf ${d['net_revenue']/1e3:+.0f}K without exclusion)")
print(f"Write-off delta: {d2['writeoff_rate']*100:+.2f}pp (cf {d['writeoff_rate']*100:+.2f}pp without exclusion)")

# ── Segment Impact Table ──────────────────────────────────────────────────────
print("\n--- Segment Impact by Grade ---")
seg = results1["segment_impact"]
print(seg[["segment", "baseline_revenue", "scenario_revenue", "revenue_delta_pct",
           "baseline_writeoff_rate", "scenario_writeoff_rate", "recommendation"]].to_string(index=False))

print("\n✅ Scenario simulation complete.")
