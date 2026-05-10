"""
rag_extensions.py — Two targeted fixes for the RAG layer.

  Fix 1: fuzzy_parse_date_in_question()
          Drop-in replacement for _parse_iso_date_in_question() in retrieval.py.
          Handles natural language dates: "last March", "in 2024", "my visit in November".

  Fix 2: Extended translation support in translation.py
          Replaces normalize_preferred_language() and translate_if_needed()
          to support French, Chinese, Arabic, Portuguese, German — not just Spanish.

HOW TO INTEGRATE:

  retrieval.py — replace _parse_iso_date_in_question with fuzzy_parse_date_in_question:
    from .rag_extensions import fuzzy_parse_date_in_question
    # then in retrieve_for_intent():
    d = fuzzy_parse_date_in_question(question)   # was: _parse_iso_date_in_question(question)

  translation.py — replace normalize_preferred_language() and translate_if_needed()
    with the versions below (copy-paste into translation.py).
"""

from __future__ import annotations

import os
import re
from datetime import date, datetime
from typing import Optional


# ---------------------------------------------------------------------------
# Fix 1: Fuzzy date parsing for POINT_IN_TIME retrieval
# ---------------------------------------------------------------------------

_MONTH_MAP = {
    "january": 1, "jan": 1,
    "february": 2, "feb": 2,
    "march": 3, "mar": 3,
    "april": 4, "apr": 4,
    "may": 5,
    "june": 6, "jun": 6,
    "july": 7, "jul": 7,
    "august": 8, "aug": 8,
    "september": 9, "sep": 9, "sept": 9,
    "october": 10, "oct": 10,
    "november": 11, "nov": 11,
    "december": 12, "dec": 12,
}


def fuzzy_parse_date_in_question(question: str) -> Optional[date]:
    """
    Extract a date reference from a natural-language patient question.
    Returns a date if found, else None.

    Handles:
      - ISO:           "2024-03-15"
      - Month + Year:  "March 2024", "in November 2023"
      - Year only:     "in 2024", "my 2023 visit"
      - Relative:      "last month", "last year", "last March"
      - Named month:   "in March" (assumes current year, then prior year if in future)
    """
    q = (question or "").lower().strip()
    today = date.today()

    # 1. Exact ISO date: 2024-03-15
    m = re.search(r"\b(\d{4}-\d{2}-\d{2})\b", q)
    if m:
        try:
            return date.fromisoformat(m.group(1))
        except ValueError:
            pass

    # 2. "Month YYYY" or "YYYY Month": "March 2024", "2024 March"
    for pat in [
        r"\b(" + "|".join(_MONTH_MAP) + r")\s+(\d{4})\b",
        r"\b(\d{4})\s+(" + "|".join(_MONTH_MAP) + r")\b",
    ]:
        m = re.search(pat, q)
        if m:
            groups = m.groups()
            # figure out which group is month and which is year
            if groups[0].isdigit():
                year, month_str = int(groups[0]), groups[1]
            else:
                month_str, year = groups[0], int(groups[1])
            month = _MONTH_MAP.get(month_str)
            if month and 1900 < year <= today.year + 1:
                return date(year, month, 1)

    # 3. Year only: "in 2024", "my 2023 visit"
    m = re.search(r"\b(20\d{2}|19\d{2})\b", q)
    if m:
        year = int(m.group(1))
        if 1900 < year <= today.year:
            return date(year, 1, 1)

    # 4. Relative: "last month", "last year"
    if re.search(r"\blast\s+month\b", q):
        first_of_this_month = today.replace(day=1)
        # go back one month
        if first_of_this_month.month == 1:
            return date(first_of_this_month.year - 1, 12, 1)
        return date(first_of_this_month.year, first_of_this_month.month - 1, 1)

    if re.search(r"\blast\s+year\b", q):
        return date(today.year - 1, 1, 1)

    # 5. "last <month>": "last March"
    m = re.search(r"\blast\s+(" + "|".join(_MONTH_MAP) + r")\b", q)
    if m:
        month = _MONTH_MAP[m.group(1)]
        year = today.year if month < today.month else today.year - 1
        return date(year, month, 1)

    # 6. Named month alone: "in March", "my March visit"
    m = re.search(r"\bin\s+(" + "|".join(_MONTH_MAP) + r")\b", q)
    if m:
        month = _MONTH_MAP[m.group(1)]
        year = today.year if month <= today.month else today.year - 1
        return date(year, month, 1)

    return None


def date_to_range(d: date) -> tuple[date, date]:
    """
    Convert a partial date (year-only or month-only) to an inclusive range.
    Use with search_chunks(after_date=..., before_date=...).

    - If day == 1 and we infer it was year-only → full year range
    - If day == 1 and month was specified → full month range
    - Otherwise → exact date (same for both bounds)
    """
    import calendar
    # Year-only signal: January 1st
    if d.month == 1 and d.day == 1:
        return date(d.year, 1, 1), date(d.year, 12, 31)
    # Month-only signal: 1st of a non-January month
    if d.day == 1:
        last_day = calendar.monthrange(d.year, d.month)[1]
        return date(d.year, d.month, 1), date(d.year, d.month, last_day)
    # Exact date
    return d, d


# ---------------------------------------------------------------------------
# Fix 2: Multilingual translation support
# ---------------------------------------------------------------------------

# Full language map — covers the languages your parser's OCR can handle
_LANG_MAP = {
    # BCP-47 code → (display name, common aliases)
    "en": ("English",    ["en", "eng", "english"]),
    "es": ("Spanish",    ["es", "spa", "spanish", "español"]),
    "fr": ("French",     ["fr", "fra", "french", "français"]),
    "zh": ("Chinese",    ["zh", "zho", "chinese", "mandarin", "zh-cn", "zh-tw"]),
    "ar": ("Arabic",     ["ar", "ara", "arabic"]),
    "pt": ("Portuguese", ["pt", "por", "portuguese", "português"]),
    "de": ("German",     ["de", "deu", "german", "deutsch"]),
    "hi": ("Hindi",      ["hi", "hin", "hindi"]),
    "tl": ("Filipino",   ["tl", "fil", "tagalog", "filipino"]),
    "vi": ("Vietnamese", ["vi", "vie", "vietnamese"]),
    "ko": ("Korean",     ["ko", "kor", "korean"]),
    "ja": ("Japanese",   ["ja", "jpn", "japanese"]),
}


def normalize_preferred_language(language: Optional[str]) -> str:
    """
    Convert any language string to a canonical BCP-47 code.
    Returns 'en' if unrecognized.

    Replaces normalize_preferred_language() in translation.py.
    """
    if not language:
        return "en"
    low = language.lower().strip()
    for code, (name, aliases) in _LANG_MAP.items():
        if low in aliases or low == name.lower():
            return code
    # Partial match: "es-MX" → "es"
    prefix = low.split("-")[0].split("_")[0]
    if prefix in _LANG_MAP:
        return prefix
    return "en"


def translate_if_needed(text: str, source_lang: str, target_lang: str) -> str:
    """
    Translate text from source_lang to target_lang via watsonx (primary)
    or Featherless AI (fallback). Returns original if same language or
    if no API is configured.

    Replaces translate_if_needed() in translation.py.
    """
    if source_lang == target_lang or not (text or "").strip():
        return text

    src_name = _LANG_MAP.get(source_lang, (source_lang,))[0]
    tgt_name = _LANG_MAP.get(target_lang, (target_lang,))[0]

    prompt = (
        f"Translate the following patient-facing health explanation "
        f"from {src_name} to {tgt_name}.\n"
        f"Keep medical terms accurate. Do not add facts. "
        f"Output only the translation.\n\nTEXT:\n{text}\n"
    )

    # Try watsonx first (IBM — mandatory tech)
    try:
        from backend.chat.watsonx_client import generate_text, watsonx_configured
        if watsonx_configured():
            return generate_text(prompt, max_new_tokens=800, temperature=0)
    except Exception:
        pass

    # Fallback: Featherless AI
    api_key = os.getenv("rc_2fe81ea0a236a2bf19bbfe9d4c6bba373a84acf1b636585a0684be2af325c02b")
    if api_key:
        try:
            import requests
            response = requests.post(
                "https://api.featherless.ai/v1/chat/completions",
                headers={
                    "Authorization": f"Bearer {api_key}",
                    "Content-Type": "application/json",
                },
                json={
                    "model": "meta-llama/Llama-3.3-70B-Instruct",
                    "messages": [{"role": "user", "content": prompt}],
                    "max_tokens": 800,
                    "temperature": 0,
                },
                timeout=20,
            )
            return response.json()["choices"][0]["message"]["content"].strip()
        except Exception:
            pass

    return text  # graceful degradation — return original if both fail
