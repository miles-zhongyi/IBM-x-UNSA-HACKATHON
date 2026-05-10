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


def test_detect_input_language_more_languages():
    from backend.chat.translation_1 import detect_input_language

    assert detect_input_language("Hola, ¿qué tal?") == "es"
    assert detect_input_language("你好，我很好") == "zh"
    assert detect_input_language("Bonjour, comment ça va?") == "fr"


def test_normalize_preferred_language_returns_short_code():
    from backend.chat.translation_1 import normalize_preferred_language

    assert normalize_preferred_language("zh-CN") == "zh"
    assert normalize_preferred_language("fr-FR") == "fr"
    assert normalize_preferred_language("pt") == "en"
