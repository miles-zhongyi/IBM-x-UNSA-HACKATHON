from __future__ import annotations

import re
from enum import Enum


class Intent(str, Enum):
    TREND = "TREND"
    POINT_IN_TIME = "POINT_IN_TIME"
    DEFINITION = "DEFINITION"
    MEDICATION = "MEDICATION"
    SAFETY = "SAFETY"
    GENERAL = "GENERAL"


_TREND_PAT = re.compile(
    r"\b(trend|trends|over time|history of|changed|change|increas|decreas|"
    r"getting better|getting worse|compared to|last \d+|since|progression)\b",
    re.I,
)
_POINT_PAT = re.compile(
    r"\b(when|what date|on which|at my last visit|last time|yesterday|today|"
    r"this week|in \d{4}|january|february|march|april|may|june|july|august|"
    r"september|october|november|december)\b",
    re.I,
)
_DEF_PAT = re.compile(
    r"\b(what is|what does .{1,40} mean|what do .{1,40} mean|define|"
    r"explain (?:the )?(?:term|word|lab|test)|meaning of)\b",
    re.I,
)
_MED_PAT = re.compile(
    r"\b(medication|medicine|pill|tablet|prescription|drug|dose|dosage|"
    r"mg\b|mcg\b|insulin|metformin|aspirin|lisinopril|atorvastatin)\b",
    re.I,
)
_SAFE_PAT = re.compile(
    r"\b(side effect|interaction|interactions|allergy|allergic|overdose|"
    r"black box|warning|is it safe|can i take .{0,30} with)\b",
    re.I,
)


def classify_intent(question: str, med_names_in_record: list[str] | None = None) -> Intent:
    """
    Lightweight rule-based classifier (no LLM). Good enough for hackathon routing.
    Order matters: more specific intents before GENERAL.
    """
    q = (question or "").strip()
    if not q:
        return Intent.GENERAL

    med_names_in_record = med_names_in_record or []
    q_lower = q.lower()
    for name in med_names_in_record:
        if name and len(name) > 3 and name.lower() in q_lower:
            return Intent.MEDICATION

    if _DEF_PAT.search(q):
        return Intent.DEFINITION
    if _TREND_PAT.search(q):
        return Intent.TREND
    if _POINT_PAT.search(q):
        return Intent.POINT_IN_TIME
    if _SAFE_PAT.search(q):
        return Intent.SAFETY
    if _MED_PAT.search(q):
        return Intent.MEDICATION

    return Intent.GENERAL


def extract_lab_hint(question: str) -> str | None:
    """Crude lab name hint for get_lab_trend (e.g. A1C, glucose)."""
    q = question or ""
    for pat, name in (
        (r"\bA1[Cc]\b|hemoglobin\s+A1[Cc]|hba1c", "A1C"),
        (r"\bglucose\b|blood sugar", "glucose"),
        (r"\bLDL\b", "LDL"),
        (r"\bHDL\b", "HDL"),
        (r"\bcreatinine\b", "creatinine"),
        (r"\bTroponin\b", "troponin"),
        (r"\bBNP\b", "BNP"),
        (r"\bINR\b|PT/INR", "INR"),
    ):
        if re.search(pat, q, re.I):
            return name
    return None
