"""
Synthetic loan data generator.

Produces a realistic Lending-Club-style dataset when real data is unavailable.
All randomness is seeded for reproducibility.
"""
from __future__ import annotations

import logging
from pathlib import Path

import numpy as np
import pandas as pd

logger = logging.getLogger(__name__)

GRADE_RATES = {
    "A": (0.055, 0.075),
    "B": (0.085, 0.115),
    "C": (0.115, 0.155),
    "D": (0.155, 0.200),
    "E": (0.200, 0.265),
    "F": (0.265, 0.320),
    "G": (0.320, 0.360),
}

GRADE_PD = {
    "A": 0.02,
    "B": 0.05,
    "C": 0.09,
    "D": 0.14,
    "E": 0.20,
    "F": 0.28,
    "G": 0.36,
}

PURPOSES = [
    "debt_consolidation",
    "credit_card",
    "home_improvement",
    "other",
    "major_purchase",
    "medical",
    "small_business",
    "vacation",
    "car",
    "moving",
]

STATES = [
    "CA", "TX", "NY", "FL", "IL", "PA", "OH", "GA", "NC", "MI",
    "NJ", "VA", "WA", "AZ", "MA", "TN", "IN", "MD", "CO", "MO",
]

INCOME_BANDS = ["<40k", "40-60k", "60-80k", "80-100k", "100-150k", ">150k"]
INCOME_BAND_RANGES = [(0, 40000), (40000, 60000), (60000, 80000),
                      (80000, 100000), (100000, 150000), (150000, 300000)]


def generate_synthetic_loans(
    n: int = 50_000,
    seed: int = 42,
    start_date: str = "2018-01-01",
    end_date: str = "2023-12-31",
    output_path: Path | None = None,
) -> pd.DataFrame:
    """
    Generate a synthetic loan portfolio DataFrame.

    Parameters
    ----------
    n : int
        Number of loan records to generate.
    seed : int
        Random seed for reproducibility.
    start_date : str
        Earliest possible application date (ISO format).
    end_date : str
        Latest possible application date (ISO format).
    output_path : Path | None
        If provided, saves as parquet to this path.

    Returns
    -------
    pd.DataFrame
        Synthetic loan portfolio with all required fields.
    """
    rng = np.random.default_rng(seed)
    logger.info("Generating %d synthetic loans (seed=%d)…", n, seed)

    # ── Application dates ──────────────────────────────────────────────────────
    date_range = pd.date_range(start_date, end_date, freq="D")
    app_dates = pd.to_datetime(
        rng.choice(date_range, size=n, replace=True)
    )

    # ── Core loan attributes ───────────────────────────────────────────────────
    grades = rng.choice(list(GRADE_RATES.keys()), size=n,
                        p=[0.20, 0.22, 0.20, 0.16, 0.12, 0.06, 0.04])
    terms = rng.choice([36, 60], size=n, p=[0.65, 0.35])
    purposes = rng.choice(PURPOSES, size=n,
                          p=[0.35, 0.20, 0.10, 0.10, 0.07,
                             0.05, 0.05, 0.03, 0.03, 0.02])
    states = rng.choice(STATES, size=n)

    # ── Income & loan amounts ─────────────────────────────────────────────────
    annual_inc = np.clip(
        rng.lognormal(mean=11.0, sigma=0.5, size=n), 20_000, 500_000
    )
    income_band_idx = np.searchsorted(
        [r[1] for r in INCOME_BAND_RANGES[:-1]], annual_inc
    )
    income_band = np.array(INCOME_BANDS)[income_band_idx]

    loan_amnt = np.clip(
        rng.lognormal(mean=9.3, sigma=0.6, size=n), 1_000, 40_000
    ).round(-2)

    # ── APR / interest rate ────────────────────────────────────────────────────
    int_rate = np.array([
        rng.uniform(*GRADE_RATES[g]) for g in grades
    ])

    # ── Origination fee (1–5% of loan amount) ─────────────────────────────────
    origination_fee_rate = rng.uniform(0.01, 0.05, size=n)
    origination_fee = (loan_amnt * origination_fee_rate).round(2)

    # ── Approval / funding funnel ──────────────────────────────────────────────
    approval_prob = np.where(
        np.isin(grades, ["A", "B"]), 0.82,
        np.where(np.isin(grades, ["C", "D"]), 0.65, 0.48)
    )
    approved = rng.random(size=n) < approval_prob
    funded = approved & (rng.random(size=n) < 0.88)

    # ── Loan status & delinquency simulation ──────────────────────────────────
    base_pd = np.array([GRADE_PD[g] for g in grades])
    # small random noise per loan
    loan_pd = np.clip(base_pd + rng.normal(0, 0.01, size=n), 0.001, 0.99)

    # simulate loan status
    rand_outcome = rng.random(size=n)
    charged_off = funded & (rand_outcome < loan_pd)
    late = funded & ~charged_off & (rand_outcome < loan_pd * 2.5)
    current = funded & ~charged_off & ~late

    loan_status = np.where(
        ~funded, "Not Funded",
        np.where(charged_off, "Charged Off",
                 np.where(late, "Late (31-120 days)", "Current"))
    )

    # ── MOB / months on book ───────────────────────────────────────────────────
    today = pd.Timestamp("2024-06-01")
    mob = np.clip(((today - app_dates).days // 30), 0, 72)

    # ── DPD simulation ─────────────────────────────────────────────────────────
    dpd30 = funded & ~charged_off & (rng.random(size=n) < loan_pd * 1.8)
    dpd60 = dpd30 & (rng.random(size=n) < 0.50)
    dpd90 = dpd60 & (rng.random(size=n) < 0.45)

    # ── Revenue components ─────────────────────────────────────────────────────
    term_years = terms / 12
    interest_revenue = np.where(
        funded, (loan_amnt * int_rate * term_years * rng.uniform(0.55, 0.95, size=n)).round(2), 0
    )
    interchange_rev = np.where(funded, (loan_amnt * 0.015).round(2), 0)
    late_fee_rev = np.where(late, rng.uniform(25, 150, size=n).round(2), 0)

    # ── Build DataFrame ────────────────────────────────────────────────────────
    df = pd.DataFrame({
        "loan_id": np.arange(1, n + 1),
        "application_date": app_dates,
        "application_month": app_dates.to_period("M").astype(str),
        "funding_month": pd.to_datetime(
            np.where(funded, app_dates + pd.to_timedelta(
                rng.integers(3, 14, size=n), unit="D"), pd.NaT)
        ).to_period("M").astype(str),
        "vintage_month": pd.to_datetime(
            np.where(funded, app_dates, pd.NaT)
        ).to_period("M").astype(str),
        "grade": grades,
        "sub_grade": [f"{g}{rng.integers(1,6)}" for g in grades],
        "term": terms,
        "int_rate": (int_rate * 100).round(2),   # store as percentage
        "loan_amnt": loan_amnt,
        "annual_inc": annual_inc.round(0),
        "income_band": income_band,
        "purpose": purposes,
        "addr_state": states,
        "loan_status": loan_status,
        "approved": approved,
        "funded": funded,
        "mob": mob,
        "pd_score": loan_pd.round(4),
        "charged_off": charged_off,
        "dpd30": dpd30,
        "dpd60": dpd60,
        "dpd90": dpd90,
        "origination_fee": origination_fee,
        "interest_revenue": interest_revenue,
        "interchange_revenue": interchange_rev,
        "late_fee_revenue": late_fee_rev,
    })

    df["outstanding_balance"] = np.where(
        df["funded"],
        (df["loan_amnt"] * rng.uniform(0.3, 1.0, size=n)).round(2),
        0.0
    )

    logger.info("Synthetic dataset shape: %s", df.shape)

    if output_path is not None:
        output_path = Path(output_path)
        output_path.parent.mkdir(parents=True, exist_ok=True)
        df.to_parquet(output_path, index=False)
        logger.info("Saved synthetic data → %s", output_path)

    return df


if __name__ == "__main__":
    logging.basicConfig(level=logging.INFO)
    out = Path(__file__).resolve().parents[2] / "data" / "processed" / "loans.parquet"
    generate_synthetic_loans(n=50_000, output_path=out)
    print(f"Done → {out}")
