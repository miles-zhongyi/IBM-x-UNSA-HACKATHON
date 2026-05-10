from __future__ import annotations

import json
import re
from dataclasses import dataclass
from pathlib import Path

_TEMPLATES_PATH = Path(__file__).resolve().parent / "prompts" / "refusal_templates.json"


@dataclass
class SafetyCheckResult:
    triggered: bool
    category: str | None = None
    response: str | None = None


def _templates() -> dict:
    if not _TEMPLATES_PATH.exists():
        return {}
    return json.loads(_TEMPLATES_PATH.read_text(encoding="utf-8"))


# Patterns that must never reach the LLM (hard-coded safe responses).
_CRISIS = re.compile(
    r"\b(kill myself|suicide|end my life|want to die|hurt myself|"
    r"self[- ]harm)\b",
    re.I,
)
_EMERGENCY = re.compile(
    r"\b(chest pain|can't breathe|cannot breathe|stroke|facial droop|"
    r"worst headache|unconscious|passed out|severe bleeding|"
    r"overdose|seizure)\b",
    re.I,
)
_DOSAGE_CHANGE = re.compile(
    r"\b(should i stop|can i stop|double my(\s+\w+)?\s+dose|halve my dose|"
    r"change my dose|skip my|extra pill|how much should i take|"
    r"what dose should|taper myself)\b",
    re.I,
)
_DISTRESS = re.compile(
    r"\b(am i (?:gonna|going to) die|will i die|i'm scared|i am scared|"
    r"no reason to live|hopeless|what's the point of living)\b",
    re.I,
)


def preflight_safety_check(question: str) -> SafetyCheckResult:
    """
    Pre-flight safety gate. If triggered, caller must skip the LLM entirely
    and return `response` to the user.
    """
    q = (question or "").strip()
    t = _templates()

    if _CRISIS.search(q):
        return SafetyCheckResult(
            triggered=True,
            category="crisis",
            response=t.get(
                "crisis",
                "If you are in danger or thinking about hurting yourself, please call your local "
                "emergency number now (for example, 911 in the U.S.) or go to the nearest emergency room. "
                "You deserve immediate help from a trained professional.",
            ),
        )
    if _EMERGENCY.search(q):
        return SafetyCheckResult(
            triggered=True,
            category="emergency",
            response=t.get(
                "emergency",
                "What you describe could be an emergency. Please call your local emergency number "
                "or go to the nearest emergency department right now. This app cannot assess urgency.",
            ),
        )
    if _DOSAGE_CHANGE.search(q):
        return SafetyCheckResult(
            triggered=True,
            category="medication_change",
            response=t.get(
                "medication_change",
                "I cannot tell you to start, stop, or change a medication or dose. "
                "Please ask your prescribing clinician or pharmacist. "
                "I can still help you read what your visit notes say about medications.",
            ),
        )
    if _DISTRESS.search(q):
        return SafetyCheckResult(
            triggered=True,
            category="distress",
            response=t.get(
                "distress",
                "I hear that this feels scary right now, and you are not alone. "
                "I cannot predict exactly what will happen, but I can help explain what your notes say. "
                "If you feel overwhelmed or unsafe, please contact your care team right away or your local emergency number.",
            ),
        )

    return SafetyCheckResult(triggered=False)
