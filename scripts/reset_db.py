"""Reset ingestion stores + reference corpus (dev utility)."""

from __future__ import annotations

import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT))

from backend.ingestion.storage import reset_all
from backend.reference_corpus.load_corpus import reset_reference_corpus

if __name__ == "__main__":
    reset_reference_corpus()
    reset_all()
    print("Ingestion SQLite + Chroma patient collection + reference corpus cleared.")
