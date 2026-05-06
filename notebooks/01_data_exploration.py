"""
Notebook 01 — Data Exploration & EDA
=====================================
Run interactively with: jupyter nbconvert --to notebook --execute
Or as a plain script: python notebooks/01_data_exploration.py
"""
# %% [markdown]
# # Agentic Credit Analytics — Data Exploration
# This notebook walks through the synthetic loan dataset, computes baseline metrics,
# and produces the visualisations used by the dashboard.

# %%
import sys
from pathlib import Path
sys.path.insert(0, str(Path(__file__).resolve().parent.parent))

import pandas as pd
import numpy as np
import matplotlib.pyplot as plt
import matplotlib
matplotlib.use("Agg")

from src.data.synthetic_data import generate_synthetic_loans
from src.metrics.metric_definitions import compute_all_metrics
from src.metrics.cohort_metrics import build_cohort_table, grade_segment_summary, delinquency_progression

print("=" * 60)
print("STEP 1: Generate Synthetic Portfolio")
print("=" * 60)

df = generate_synthetic_loans(n=50_000, seed=42)
print(f"Dataset: {len(df):,} rows × {len(df.columns)} columns")
print(f"\nColumns:\n{list(df.columns)}")

# %% [markdown]
# ## Loan Status Distribution
# %%
print("\n--- Loan Status Distribution ---")
print(df["loan_status"].value_counts(normalize=True).mul(100).round(2).to_string())

# %% [markdown]
# ## Grade Distribution
# %%
print("\n--- Grade Distribution ---")
print(df["grade"].value_counts().sort_index().to_string())

# %% [markdown]
# ## APR by Grade
# %%
print("\n--- Average APR by Grade ---")
print(df.groupby("grade")["int_rate"].agg(["mean", "std", "min", "max"]).round(2).to_string())

# %% [markdown]
# ## Funnel Metrics
# %%
print("\n" + "=" * 60)
print("STEP 2: Funnel Metrics")
print("=" * 60)

n_app = len(df)
n_appr = df["approved"].sum()
n_fund = df["funded"].sum()

print(f"Applications :  {n_app:>10,}")
print(f"Approved     :  {n_appr:>10,}  ({n_appr/n_app*100:.1f}%)")
print(f"Funded       :  {n_fund:>10,}  ({n_fund/n_appr*100:.1f}% of approved)")
print(f"Booked Bal   :  ${df[df['funded']]['loan_amnt'].sum()/1e6:>9.2f}M")
print(f"Avg APR      :  {df[df['funded']]['int_rate'].mean():>10.2f}%")

# %% [markdown]
# ## All Metrics
# %%
print("\n" + "=" * 60)
print("STEP 3: Full Metric Computation")
print("=" * 60)

metrics = compute_all_metrics(df)
for k, v in sorted(metrics.items()):
    if isinstance(v, float) and not np.isnan(v):
        if v > 1_000_000:
            print(f"  {k:<30}: ${v/1e6:.2f}M")
        elif v > 1_000:
            print(f"  {k:<30}: {v:,.0f}")
        elif v < 1 and v > 0:
            print(f"  {k:<30}: {v*100:.2f}%")
        else:
            print(f"  {k:<30}: {v:.4f}")

# %% [markdown]
# ## Cohort Analysis
# %%
print("\n" + "=" * 60)
print("STEP 4: Cohort Heatmap")
print("=" * 60)

cohort = build_cohort_table(df, metric_col="dpd30")
print(f"Cohort table shape: {cohort.shape}")
print(f"Max 30-DPD rate: {cohort.max().max()*100:.1f}%")
print(f"Min 30-DPD rate: {cohort.min().min()*100:.1f}%")

# %%
print("\n" + "=" * 60)
print("STEP 5: Grade Summary")
print("=" * 60)

grade_df = grade_segment_summary(df)
print(grade_df[["grade", "n_funded", "avg_apr", "dpd30_rate", "writeoff_rate", "net_revenue"]].to_string(index=False))

# %%
print("\n" + "=" * 60)
print("STEP 6: Delinquency Progression")
print("=" * 60)

dprog = delinquency_progression(df, "vintage_month")
print(f"Vintages analysed: {len(dprog)}")
worst = dprog.nlargest(5, "dpd30_rate")[["cohort", "dpd30_rate", "dpd90_rate", "writeoff_rate"]]
print("\nTop 5 worst cohorts by 30-DPD:")
print(worst.to_string(index=False))

print("\n✅ Data exploration complete.")
