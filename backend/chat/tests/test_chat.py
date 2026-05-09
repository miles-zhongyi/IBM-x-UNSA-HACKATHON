from backend.chat.intent import Intent, classify_intent, extract_lab_hint
from backend.chat.safety import preflight_safety_check


def test_safety_crisis_triggers():
    r = preflight_safety_check("I want to kill myself tonight")
    assert r.triggered and r.category == "crisis"


def test_safety_medication_change_triggers():
    r = preflight_safety_check("Should I double my metformin dose?")
    assert r.triggered and r.category == "medication_change"


def test_safety_clear():
    r = preflight_safety_check("What does my A1C mean?")
    assert not r.triggered


def test_intent_trend():
    assert classify_intent("How has my A1C changed over time?") == Intent.TREND


def test_intent_definition():
    assert classify_intent("What is LDL cholesterol?") == Intent.DEFINITION


def test_lab_hint():
    assert extract_lab_hint("Tell me about my A1C trend") == "A1C"
