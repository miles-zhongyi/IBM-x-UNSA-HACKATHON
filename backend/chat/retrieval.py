from __future__ import annotations

import re
from datetime import date, datetime

from backend.ingestion.embedding import embed_query
from backend.ingestion.storage import (
    get_active_medications,
    get_lab_trend,
    search_chunks,
)

from .intent import Intent, extract_lab_hint


def _parse_iso_date_in_question(q: str) -> date | None:
    m = re.search(r"\b(\d{4}-\d{2}-\d{2})\b", q or "")
    if m:
        try:
            return date.fromisoformat(m.group(1))
        except ValueError:
            return None
    return None


def search_reference_snippets(query_embedding: list[float], n_results: int = 4) -> list[dict]:
    """Semantic search over vetted education snippets (separate Chroma collection)."""
    from backend.reference_corpus.load_corpus import query_reference_collection

    return query_reference_collection(query_embedding, n_results=n_results)


def retrieve_for_intent(
    patient_id: str,
    question: str,
    intent: Intent,
    *,
    n_chunks: int = 6,
) -> dict:
    """
    Intent-routed retrieval bundle for generation.

    Returns dict keys:
      chunks: list[dict]  (same shape as storage.search_chunks)
      lab_trend: list[dict] | None
      active_medications: list[dict] | None
      reference_snippets: list[dict] | None
    """
    q_emb = embed_query(question)
    lab_hint = extract_lab_hint(question)

    out: dict = {
        "chunks": [],
        "lab_trend": None,
        "active_medications": None,
        "reference_snippets": None,
    }

    if intent == Intent.TREND:
        if lab_hint:
            out["lab_trend"] = get_lab_trend(patient_id, lab_hint)
        out["chunks"] = search_chunks(patient_id, q_emb, n_results=n_chunks)

    elif intent == Intent.POINT_IN_TIME:
        d = _parse_iso_date_in_question(question)
        if d:
            out["chunks"] = search_chunks(
                patient_id,
                q_emb,
                n_results=n_chunks,
                after_date=d,
                before_date=d,
            )
        if not out["chunks"]:
            out["chunks"] = search_chunks(patient_id, q_emb, n_results=n_chunks)

    elif intent == Intent.DEFINITION:
        out["reference_snippets"] = search_reference_snippets(q_emb, n_results=4)
        out["chunks"] = search_chunks(patient_id, q_emb, n_results=max(3, n_chunks - 2))

    elif intent in (Intent.MEDICATION, Intent.SAFETY):
        out["active_medications"] = get_active_medications(patient_id)
        out["chunks"] = search_chunks(patient_id, q_emb, n_results=n_chunks)

    else:
        out["chunks"] = search_chunks(patient_id, q_emb, n_results=n_chunks)

    return out
