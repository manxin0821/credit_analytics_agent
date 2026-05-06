#!/usr/bin/env bash
# ──────────────────────────────────────────────────────────────
# Agentic Credit Analytics — Local Run Script
# Usage: bash run_local.sh
# ──────────────────────────────────────────────────────────────
set -e

echo ""
echo "╔═══════════════════════════════════════════════════════╗"
echo "║  Agentic Credit Analytics Command Center              ║"
echo "╚═══════════════════════════════════════════════════════╝"
echo ""

# 1. Check .env
if [ ! -f ".env" ]; then
  echo "⚠  .env not found. Copying from .env.example..."
  cp .env.example .env
  echo "   → Edit .env and add your DEEPSEEK_API_KEY, then re-run."
  exit 1
fi

# 2. Install dependencies
echo "📦 Installing dependencies..."
pip install -r requirements.txt -q

# 3. Pre-generate data
echo "📊 Pre-generating synthetic loan data..."
python src/data/synthetic_data.py

# 4. Run tests
echo "🧪 Running tests..."
python -m pytest tests/ -q --tb=short

# 5. Launch Streamlit
echo ""
echo "🚀 Launching dashboard at http://localhost:8501"
echo ""
streamlit run app.py --server.port 8501
