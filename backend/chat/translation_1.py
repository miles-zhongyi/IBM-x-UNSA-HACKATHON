from __future__ import annotations

import re
from typing import Optional

# Lightweight language hints (no external deps). Extend as needed.
_SPANISH_HINT = re.compile(
    r"\b(el|la|los|las|qué|cómo|cuándo|dónde|por qué|medicamento|dolor|azúcar)\b",
    re.I,
)


def detect_input_language(text: str) -> str:
    """Returns BCP-47 style short code: 'en' or 'es' (best-effort)."""
    t = (text or "").strip()
    if not t:
        return "en"
    if _SPANISH_HINT.search(t):
        return "es"
    return "en"


def normalize_preferred_language(language: Optional[str]) -> str:
    if not language:
        return "en"
    low = language.lower()
    if low.startswith("es"):
        return "es"
    return "en"


def translate_if_needed(text: str, source_lang: str, target_lang: str) -> str:
    """
    If source != target, translate via watsonx when configured; otherwise return original.
    """
    if source_lang == target_lang or not (text or "").strip():
        return text
    try:
        from .watsonx_client import generate_text, watsonx_configured

        if not watsonx_configured():
            raise RuntimeError("watsonx not configured")
        tgt = "Spanish" if target_lang == "es" else "English"
        src = "Spanish" if source_lang == "es" else "English"
        prompt = (
            f"Translate the following patient-facing health explanation from {src} to {tgt}.\n"
            f"Keep medical terms accurate. Do not add facts. Output only the translation.\n\n"
            f"TEXT:\n{text}\n"
        )
        return generate_text(prompt, max_new_tokens=800, temperature=0)
    except Exception:
        pass
    import os, requests
    api_key = os.getenv("FEATHERLESS_API_KEY")
    if api_key:
        try:
            tgt = "Spanish" if target_lang == "es" else "English"
            src = "Spanish" if source_lang == "es" else "English"
            prompt = f"Translate from {src} to {tgt}. Output only the translation.\n\nTEXT:\n{text}"
            resp = requests.post(
                "https://api.featherless.ai/v1/chat/completions",
                headers={"Authorization": f"Bearer {api_key}",
                         "Content-Type": "application/json"},
                json={"model": "meta-llama/Llama-3.3-70B-Instruct",
                      "messages": [{"role": "user", "content": prompt}],
                      "max_tokens": 800, "temperature": 0},
                timeout=20,
            )
            return resp.json()["choices"][0]["message"]["content"].strip()
        except Exception:
            pass
    return text
