from __future__ import annotations

import re
from typing import Optional

# Lightweight language hints (no external deps). Extend as needed.
_LANGUAGE_HINTS = {
    "es": re.compile(r"\b(el|la|los|las|qué|cómo|cuándo|dónde|por qué|medicamento|dolor|azúcar)\b", re.I),
    "zh": re.compile(r"[\u4e00-\u9fff]"),
    "fr": re.compile(r"\b(bonjour|merci|s'il vous plaît|surtout|être|avoir)\b", re.I),
    "de": re.compile(r"\b(hallo|danke|bitte|ich|sie|ist)\b", re.I),
    "ja": re.compile(r"[\u3040-\u30ff\u4e00-\u9fff]"),
    "ko": re.compile(r"[\uac00-\ud7af]"),
}

_LANGUAGE_NAMES = {
    "en": "English",
    "es": "Spanish",
    "fr": "French",
    "de": "German",
    "zh": "Chinese",
    "ja": "Japanese",
    "ko": "Korean",
}


def detect_input_language(text: str) -> str:
    """Returns a best-effort short code for common languages."""
    t = (text or "").strip()
    if not t:
        return "en"
    for lang, regex in _LANGUAGE_HINTS.items():
        if regex.search(t):
            return lang
    return "en"


def normalize_preferred_language(language: Optional[str]) -> str:
    if not language:
        return "en"
    low = language.lower()
    if "-" in low:
        low = low.split("-")[0]
    return low if low in _LANGUAGE_NAMES else "en"


def _google_translate_fallback(text: str, source: str, target: str) -> str:
    try:
        import requests
        from urllib.parse import quote_plus

        if not text.strip():
            return text
        source = source or "auto"
        target = target or "en"
        response = requests.get(
            "https://translate.googleapis.com/translate_a/single",
            params={
                "client": "gtx",
                "sl": source,
                "tl": target,
                "dt": "t",
                "q": text,
            },
            headers={"User-Agent": "Mozilla/5.0"},
            timeout=20,
        )
        response.raise_for_status()
        data = response.json()
        if isinstance(data, list) and data and isinstance(data[0], list):
            return "".join([segment[0] for segment in data[0] if segment and segment[0]])
    except Exception:
        pass
    return text


def translate_if_needed(text: str, source_lang: str, target_lang: str) -> str:
    """
    If source != target, translate via watsonx or Featherless when configured; otherwise return original.
    """
    if not (text or "").strip():
        return text
    source = normalize_preferred_language(source_lang)
    target = normalize_preferred_language(target_lang)
    if source == target:
        return text

    source_name = _LANGUAGE_NAMES.get(source, "English")
    target_name = _LANGUAGE_NAMES.get(target, "English")

    try:
        from .watsonx_client import generate_text, watsonx_configured

        if not watsonx_configured():
            raise RuntimeError("watsonx not configured")
        prompt = (
            f"Translate the following patient-facing health explanation from {source_name} to {target_name}.\n"
            f"Keep medical terms accurate. Do not add facts. Output only the translation.\n\n"
            f"TEXT:\n{text}\n"
        )
        return generate_text(prompt, max_new_tokens=800, temperature=0)
    except Exception:
        pass

    import os
    api_key = os.getenv("FEATHERLESS_API_KEY")
    if api_key:
        try:
            import requests
            prompt = (
                f"Translate the following patient-facing health explanation from {source_name} to {target_name}.\n"
                f"Keep medical terms accurate. Do not add facts. Output only the translation.\n\n"
                f"TEXT:\n{text}"
            )
            resp = requests.post(
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
            return resp.json()["choices"][0]["message"]["content"].strip()
        except Exception:
            pass

    return _google_translate_fallback(text, source, target)
