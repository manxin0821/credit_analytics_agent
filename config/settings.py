"""
Global application settings loaded from environment variables.
"""
import os
from pathlib import Path
from dotenv import load_dotenv

load_dotenv()

BASE_DIR = Path(__file__).resolve().parent.parent

# ── LLM ──────────────────────────────────────────────────────────────────────
DEEPSEEK_API_KEY: str = os.environ.get("DEEPSEEK_API_KEY", "")
DEEPSEEK_MODEL: str = os.environ.get("DEEPSEEK_MODEL", "deepseek-chat")
DEEPSEEK_BASE_URL: str = "https://api.deepseek.com"
LLM_TEMPERATURE: float = 0.2
LLM_MAX_TOKENS: int = 2048

# ── Data paths ────────────────────────────────────────────────────────────────
DATA_RAW_DIR: Path = BASE_DIR / "data" / "raw"
DATA_PROCESSED_DIR: Path = BASE_DIR / "data" / "processed"
SYNTHETIC_SEED: int = 42
SYNTHETIC_N_LOANS: int = 50_000

# ── Model ─────────────────────────────────────────────────────────────────────
MODEL_DIR: Path = BASE_DIR / "src" / "models"
LGB_PARAMS: dict = {
    "n_estimators": 200,
    "max_depth": 5,
    "learning_rate": 0.05,
    "num_leaves": 31,
    "random_state": 42,
    "verbosity": -1,
}

# ── Scenario defaults ─────────────────────────────────────────────────────────
DEFAULT_LGD: float = 0.60
DEMAND_SENSITIVITY_MAP: dict = {"low": 0.02, "medium": 0.05, "high": 0.10}
PD_SENSITIVITY_MAP: dict = {"low": 0.005, "medium": 0.015, "high": 0.030}

# ── UI ────────────────────────────────────────────────────────────────────────
APP_TITLE: str = "Agentic Credit Analytics Command Center"
DASHBOARD_TABS: list = ["Overview", "Funnel", "Cohort", "Time Series", "Scenario Lab", "Agent Trace"]
