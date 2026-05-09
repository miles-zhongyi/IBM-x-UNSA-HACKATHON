from __future__ import annotations

import os
from pathlib import Path

from backend.ingestion.pipeline import ingest_text
from backend.ingestion.storage import get_patient_timeline, init_db
from backend.reference_corpus.load_corpus import load_corpus_if_empty

from .escalation_store import init_escalation_db


def _repo_root() -> Path:
    return Path(__file__).resolve().parents[2]


def _seed_demo_patients() -> None:
    root = _repo_root()
    samples = root / "backend" / "ingestion" / "sample_notes"
    demo = root / "demo_data"

    cases: list[tuple[str, Path, str]] = [
        ("marcus-demo", samples / "note1_stemi.txt", "note1_stemi.txt"),
        ("dorothy-demo", samples / "note3_hospice.txt", "note3_hospice.txt"),
    ]
    for path in [
        demo / "elena_visit_2023_09.txt",
        demo / "elena_visit_2024_03.txt",
        demo / "elena_visit_2024_11.txt",
        demo / "elena_visit_2025_05.txt",
    ]:
        if path.exists():
            cases.append(("elena-demo", path, path.name))

    for patient_id, path, label in cases:
        text = path.read_text(encoding="utf-8")
        ingest_text(text, patient_id=patient_id, source_label=label)


def run_startup() -> None:
    """Idempotent: init schema, load reference corpus, seed demo patients if empty."""
    init_db()
    init_escalation_db()

    if os.getenv("DEMO_SEED_FRESH", "").lower() in ("1", "true", "yes"):
        from backend.ingestion.storage import reset_all
        from backend.reference_corpus.load_corpus import reset_reference_corpus

        reset_reference_corpus()
        reset_all()
        init_escalation_db()

    load_corpus_if_empty()

    if len(get_patient_timeline("marcus-demo")) == 0:
        _seed_demo_patients()
