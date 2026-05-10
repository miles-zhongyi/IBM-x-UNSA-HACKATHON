from __future__ import annotations

from typing import Any, Optional

from backend.ingestion.storage import get_active_medications

from .generation import generate_answer
from .intent import Intent, classify_intent
from .retrieval import retrieve_for_intent
from .safety import preflight_safety_check
from .translation_1 import normalize_preferred_language, translate_if_needed


def answer_patient_question(
    patient_id: str,
    question: str,
    *,
    language: Optional[str] = None,
    detail_level: str = "full",
) -> dict[str, Any]:
    """
    Full chat pipeline for API layer.

    Returns:
      answer: str
      citations: list[{"document_id","visit_date","chunk_text"}]
      escalated: bool (caller may set True on separate escalate endpoint)
      safety_triggered: bool
    """
    safety = preflight_safety_check(question)
    if safety.triggered:
        return {
            "answer": safety.response or "",
            "citations": [],
            "escalated": False,
            "safety_triggered": True,
            "trend": None,
        }

    meds = get_active_medications(patient_id)
    med_names = [m.get("name") or "" for m in meds if m.get("name")]

    intent = classify_intent(question, med_names_in_record=med_names)
    bundle = retrieve_for_intent(patient_id, question, intent)

    answer, cites = generate_answer(question, bundle, detail_level=detail_level or "full")

    preferred = normalize_preferred_language(language)
    answer = translate_if_needed(answer, source_lang="en", target_lang=preferred)

    api_citations = []
    for c in cites:
        api_citations.append(
            {
                "document_id": c.get("document_id") or "",
                "visit_date": c.get("visit_date"),
                "chunk_text": (c.get("chunk_excerpt") or c.get("excerpt") or "")[:2000],
            }
        )

    trend_payload = None
    if intent == Intent.TREND and bundle.get("lab_trend"):
        trend_payload = bundle["lab_trend"]

    return {
        "answer": answer,
        "citations": api_citations,
        "escalated": False,
        "safety_triggered": False,
        "trend": trend_payload,
    }
