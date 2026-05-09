"""
Re-seed demo patients by resetting stores and running the same logic as API startup.

Usage (from repository root):
  python scripts/seed_demo_data.py
"""

from __future__ import annotations

import os
import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT))

os.environ["DEMO_SEED_FRESH"] = "1"

from backend.api.startup import run_startup  # noqa: E402

if __name__ == "__main__":
    run_startup()
    print("Demo data seeded. Start the API with: uvicorn backend.api.main:app --reload")
