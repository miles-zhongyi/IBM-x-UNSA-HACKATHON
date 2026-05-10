from __future__ import annotations

import re
from typing import Any, Optional

from backend.ingestion.storage import get_active_medications

from .generation import generate_answer
from .intent import Intent, classify_intent
from .retrieval import retrieve_for_intent
from .safety import preflight_safety_check
from .translation_1 import normalize_preferred_language, translate_if_needed, detect_input_language

_OFF_TOPIC = re.compile(
    r"\b(amazon|netflix|weather|football|soccer|bitcoin|crypto|stock market|movie|music)\b",
    re.I,
)
_MODEL_QUESTION = re.compile(r"\b(what model|which model|are you (an )?ai|llm)\b", re.I)
_MOOD_ANXIOUS = re.compile(r"\b(scared|anxious|worried|afraid|nervous|overwhelmed)\b", re.I)
_MOOD_SAD = re.compile(r"\b(sad|depressed|hopeless|lonely|upset)\b", re.I)
_SINGLE_WORD_OK = {
    "pain", "cancer", "report", "summary", "labs", "lab", "meds", "medications",
    "diagnosis", "prognosis", "nausea", "fever", "cough", "headache", "anxiety",
    "depression", "glucose", "a1c", "bp", "blood", "visit", "help", "hi", "hello", "hey",
}


def _looks_like_gibberish(text: str) -> bool:
    t = (text or "").strip()
    if len(t) < 3:
        return True
    tokenized = re.findall(r"[A-Za-z0-9]+", t.lower())
    if not tokenized:
        return True
    if len(tokenized) == 1 and " " not in t:
        tok = tokenized[0]
        if tok in _SINGLE_WORD_OK:
            return False
        # Repeated-character noise like "eeee", "aaaaaa", "1111"
        if len(set(tok)) <= 2 and len(tok) >= 3:
            return True
        # Very short unknown tokens are usually too vague to answer safely.
        if len(tok) <= 4:
            return True
        # Long single-token inputs are frequently random keyboard noise.
        if len(tok) >= 8:
            return True
    if len(tokenized) <= 2:
        known = sum(1 for tok in tokenized if tok in _SINGLE_WORD_OK)
        if known == 0 and sum(len(tok) for tok in tokenized) <= 6:
            return True
    if ";" in t and " " not in t and len(t) >= 8:
        return True
    if re.search(r"[^\w\s\?\.\,\-]", t) and " " not in t and len(t) >= 10:
        return True
    letters = [c for c in t if c.isalpha()]
    if not letters:
        return True
    vowels = sum(1 for c in letters if c.lower() in "aeiou")
    vowel_ratio = vowels / max(len(letters), 1)
    # catches strings like "alajld;safjoawi" reasonably well
    return len(letters) >= 8 and vowel_ratio < 0.15


def _clarify_or_redirect(question_en: str) -> str | None:
    q = (question_en or "").strip()
    if _MODEL_QUESTION.search(q):
        return (
            "I am a health-assistant chatbot for your records. I may use different language models in the background, "
            "but I can best help by explaining your visits, labs, medications, and care plan."
        )
    if _OFF_TOPIC.search(q):
        return (
            "I can only help with your health records in this app. "
            "Could you ask about your symptoms, medications, labs, or latest visit?"
        )
    if _looks_like_gibberish(q):
        return (
            "I may have misunderstood that. Could you rephrase in one short sentence, "
            "for example: \"Explain my latest report simply\"?"
        )
    return None


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

    detected_lang = detect_input_language(question)
    question_en = translate_if_needed(question, source_lang=detected_lang, target_lang="en")
    clarification = _clarify_or_redirect(question_en)
    if clarification:
        preferred = normalize_preferred_language(language)
        answer = translate_if_needed(clarification, source_lang="en", target_lang=preferred)
        return {
            "answer": answer,
            "citations": [],
            "escalated": False,
            "safety_triggered": False,
            "trend": None,
        }

    intent = classify_intent(question_en, med_names_in_record=med_names)
    bundle = retrieve_for_intent(patient_id, question_en, intent)
    answer, cites = generate_answer(question_en, bundle, detail_level=detail_level or "full")
    if _MOOD_ANXIOUS.search(question_en) or _MOOD_SAD.search(question_en):
        answer = (
            "I hear this is hard, and I will explain clearly. "
            + answer
        )

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
