"""
Data loading layer.

Tries to load processed data from disk; falls back to generating synthetic data.
"""
from __future__ import annotations

import logging
from pathlib import Path

import pandas as pd

from src.data.synthetic_data import generate_synthetic_loans
from config.settings import DATA_PROCESSED_DIR, SYNTHETIC_N_LOANS, SYNTHETIC_SEED

logger = logging.getLogger(__name__)

_CACHE: pd.DataFrame | None = None


def load_loans(force_refresh: bool = False) -> pd.DataFrame:
    """
    Load the loan portfolio DataFrame.

    Checks for a parquet file at DATA_PROCESSED_DIR/loans.parquet.
    Falls back to synthetic data generation if not found.

    Parameters
    ----------
    force_refresh : bool
        If True, ignores in-memory cache and reloads from disk/generates.

    Returns
    -------
    pd.DataFrame
    """
    global _CACHE

    if _CACHE is not None and not force_refresh:
        return _CACHE

    parquet_path = DATA_PROCESSED_DIR / "loans.parquet"
    csv_path = DATA_PROCESSED_DIR / "loans.csv"

    if parquet_path.exists():
        logger.info("Loading loan data from %s", parquet_path)
        df = pd.read_parquet(parquet_path)
    elif csv_path.exists():
        logger.info("Loading loan data from %s", csv_path)
        df = pd.read_csv(csv_path, low_memory=False)
        df = _ensure_date_columns(df)
    else:
        logger.warning(
            "No processed data found at %s. Generating synthetic dataset…",
            DATA_PROCESSED_DIR,
        )
        DATA_PROCESSED_DIR.mkdir(parents=True, exist_ok=True)
        df = generate_synthetic_loans(
            n=SYNTHETIC_N_LOANS,
            seed=SYNTHETIC_SEED,
            output_path=parquet_path,
        )

    _CACHE = df
    logger.info("Dataset loaded: %d rows, %d columns", len(df), len(df.columns))
    return df


def _ensure_date_columns(df: pd.DataFrame) -> pd.DataFrame:
    """Parse string date columns to datetime where needed."""
    for col in ["application_date"]:
        if col in df.columns and not pd.api.types.is_datetime64_any_dtype(df[col]):
            df[col] = pd.to_datetime(df[col], errors="coerce")
    return df


def filter_funded(df: pd.DataFrame) -> pd.DataFrame:
    """Return only funded loan records."""
    return df[df["funded"] == True].copy()


def sample_for_display(df: pd.DataFrame, n: int = 5_000, seed: int = 42) -> pd.DataFrame:
    """Return a random sample for heavy charting operations."""
    if len(df) <= n:
        return df
    return df.sample(n=n, random_state=seed)
