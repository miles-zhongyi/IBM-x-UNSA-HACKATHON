from __future__ import annotations

import json
import os
import re
import time
from pathlib import Path
from typing import Any

_SYSTEM_PROMPT_PATH = Path(__file__).resolve().parent / "prompts" / "system_prompt.txt"


def _load_system_prompt(detail_level: str) -> str:
    base = _SYSTEM_PROMPT_PATH.read_text(encoding="utf-8") if _SYSTEM_PROMPT_PATH.exists() else ""
    if detail_level == "basic":
        base += "\n\nUser asked for BASIC detail: keep the answer shorter (roughly half the length).\n"
    return base


def _format_context_bundle(bundle: dict) -> str:
    parts: list[str] = []

    if bundle.get("lab_trend"):
        parts.append("=== LAB TREND (structured) ===\n")
        parts.append(json.dumps(bundle["lab_trend"], indent=2, default=str))

    if bundle.get("active_medications"):
        parts.append("\n=== ACTIVE MEDICATIONS (most recent visit) ===\n")
        parts.append(json.dumps(bundle["active_medications"], indent=2, default=str))

    if bundle.get("reference_snippets"):
        parts.append("\n=== TRUSTED PATIENT EDUCATION SNIPPETS ===\n")
        for i, hit in enumerate(bundle["reference_snippets"][:2], 1):
            meta = hit.get("metadata") or {}
            text = _sanitize_text(hit.get("text", "") or "")[:320]
            if _is_noisy_text(text):
                continue
            parts.append(
                f"{i}. [{meta.get('title', 'topic')}] {text}\n"
                f"   Source: {meta.get('source', 'reference corpus')}\n"
            )

    if bundle.get("chunks"):
        parts.append("\n=== RELEVANT NOTE EXCERPTS (patient's records) ===\n")
        for i, hit in enumerate(bundle["chunks"][:3], 1):
            meta = hit.get("metadata") or {}
            text = _sanitize_text(hit.get("text", "") or "")[:360]
            if _is_noisy_text(text):
                continue
            parts.append(
                f"{i}. [Visit: {meta.get('visit_date', 'unknown')}] "
                f"[document_id={meta.get('document_id')}] [section={meta.get('section')}]\n"
                f"{text}\n"
            )

    return "\n".join(parts) if parts else "(No retrieved context — say you cannot find it in the records.)"


_JSON_BLOCK = re.compile(r"\{[\s\S]*\}\s*$")
_ANSWER_FIELD = re.compile(r'"answer"\s*:\s*"((?:[^"\\]|\\.)*)"', re.S)
_ANSWER_FIELD_OPEN = re.compile(r'"answer"\s*:\s*"([\s\S]*)', re.S)
_WATSONX_SKIP_UNTIL = 0.0
_WATSONX_LAST_CREDS = ""
_CTRL = re.compile(r"[\x00-\x08\x0B\x0C\x0E-\x1F\x7F]")
_BINARY_ARTIFACT = re.compile(r"(%PDF-|xref|endobj|stream|/Linearized|obj\s*<<)", re.I)
_ASK_WORSE = re.compile(r"\b(getting worse|worse|declin|deteriorat|progress(ing|ion)?)\b", re.I)
_ASK_SURVIVAL = re.compile(r"\b(how long (can|could|do) i (live|have)|life expectancy|how much time)\b", re.I)
_ASK_LAST_VISIT_SUMMARY = re.compile(
    r"(\b(summarize|summary|explain)\b[\s\w]{0,30}\b(last|latest|recent)\b[\s\w]{0,20}\b(visit|report|note)\b)|"
    r"(\b(last|latest|recent)\s+(visit|report|note)\b)",
    re.I,
)
_COMMON_WORDS = {
    "the", "and", "for", "with", "patient", "pain", "plan", "visit", "history",
    "medication", "medications", "symptom", "support", "family", "care",
    "reported", "continue", "daily", "week", "hospice", "diagnosis",
}


def _sanitize_text(text: str) -> str:
    t = _CTRL.sub(" ", str(text or ""))
    t = t.replace("\r", " ").replace("\n", " ")
    return re.sub(r"\s+", " ", t).strip()


def _is_noisy_text(text: str) -> bool:
    t = _sanitize_text(text)
    if len(t) < 20:
        return False
    if _BINARY_ARTIFACT.search(t):
        return True
    total = len(t)
    alpha_words = re.findall(r"[A-Za-z]{3,}", t)
    if len(alpha_words) < 3 and total > 60:
        return True
    spaces = sum(1 for c in t if c.isspace())
    punct = sum(1 for c in t if c in ".,;:!?-()[]/%'\"+{}_\\|@#$^&*~`")
    alpha_chars = sum(1 for c in t if c.isalpha())
    digit_chars = sum(1 for c in t if c.isdigit())
    vowels = sum(1 for c in t.lower() if c in "aeiou")
    non_ascii = sum(1 for c in t if ord(c) > 127)
    weird = sum(1 for c in t if not (c.isalnum() or c.isspace() or c in ".,;:!?-()[]/%'\"+"))
    if (alpha_chars / total) < 0.45 and ((punct + digit_chars) / total) > 0.25:
        return True
    if (non_ascii / total) > 0.12:
        return True
    if alpha_chars >= 20 and (vowels / max(alpha_chars, 1)) < 0.20 and (punct / total) > 0.08:
        return True
    if (weird / total) > 0.28 and (spaces / total) < 0.20:
        return True
    if (punct / total) > 0.30:
        return True
    tokens = re.findall(r"[A-Za-z0-9_-]{6,}", t)
    low_vowel = 0
    for tok in tokens:
        letters = [c for c in tok if c.isalpha()]
        if not letters:
            continue
        vowels = sum(1 for c in letters if c.lower() in "aeiou")
        if vowels / len(letters) < 0.20:
            low_vowel += 1
    if tokens and low_vowel / len(tokens) > 0.6:
        return True
    words = re.findall(r"[A-Za-z]{2,}", t.lower())
    if len(words) >= 10:
        common = sum(1 for w in words if w in _COMMON_WORDS)
        symbol_heavy = ((punct + digit_chars + weird) / total) > 0.22
        if common <= 1 and symbol_heavy:
            return True
    return False


def _parse_generation_json(raw: str) -> tuple[str, list[dict[str, Any]]]:
    """Expect model to return JSON with answer + citations."""
    text = raw.strip()
    if text.startswith("```"):
        text = re.sub(r"^```(?:json)?\s*", "", text)
        text = re.sub(r"\s*```$", "", text)
    try:
        data = json.loads(text)
        answer = _sanitize_text(str(data.get("answer", "")).strip())
        cites = data.get("citations") or []
        if not isinstance(cites, list):
            cites = []
        norm: list[dict[str, Any]] = []
        for c in cites:
            if not isinstance(c, dict):
                continue
            norm.append(
                {
                    "visit_date": c.get("visit_date"),
                    "document_id": c.get("document_id"),
                    "chunk_excerpt": _sanitize_text(c.get("chunk_excerpt") or c.get("excerpt") or ""),
                }
            )
        return answer, norm
    except json.JSONDecodeError:
        m = _JSON_BLOCK.search(text)
        if m:
            try:
                data = json.loads(m.group(0))
                return _sanitize_text(str(data.get("answer", text)).strip()), data.get("citations") or []
            except json.JSONDecodeError:
                pass
        # Model sometimes returns truncated JSON; recover "answer" field best-effort.
        m2 = _ANSWER_FIELD.search(text)
        if m2:
            frag = m2.group(1)
            try:
                answer = json.loads(f'"{frag}"')
            except Exception:
                answer = frag.replace('\\"', '"').replace("\\n", "\n")
            return _sanitize_text(str(answer).strip()), []
        m3 = _ANSWER_FIELD_OPEN.search(text)
        if m3:
            frag2 = m3.group(1)
            frag2 = re.split(r'"\s*,\s*"citations"\s*:', frag2, maxsplit=1)[0]
            answer2 = frag2.replace('\\"', '"').replace("\\n", "\n").rstrip('"} ,')
            return _sanitize_text(answer2), []
        return _sanitize_text(text), []


def _fallback_answer(question: str, bundle: dict) -> tuple[str, list[dict[str, Any]]]:
    """Deterministic answer when watsonx is unavailable."""
    q = (question or "").strip().lower()
    if q in {"hi", "hello", "hey", "m", "yo"} or len(q) <= 2:
        return (
            "Hi! I can help explain your records. Try asking something specific like "
            "\"Explain my latest report\" or \"What changed in my labs?\"",
            [],
        )

    cites: list[dict[str, Any]] = []
    lines: list[str] = []

    # Build minimal keyword set to pick relevant chunks
    raw_tokens = re.findall(r"[a-zA-Z]{3,}", q)
    stop = {
        "what", "when", "where", "which", "with", "from", "your", "about",
        "this", "that", "have", "does", "should", "could", "would", "explain",
        "latest", "report", "visit", "simply", "please",
    }
    q_tokens = {t for t in raw_tokens if t not in stop}

    if bundle.get("lab_trend"):
        lines.append("Here is what your saved lab values show over time:")
        for row in bundle["lab_trend"][:12]:
            vd = row.get("test_date") or row.get("visit_date")
            name = row.get("name")
            val = row.get("value")
            vt = row.get("value_text")
            unit = row.get("unit") or ""
            val_s = f"{val}" if val is not None else (vt or "")
            lines.append(f"- {name}: {val_s} {unit}".strip() + (f" (date: {vd})" if vd else ""))
            cites.append(
                {
                    "visit_date": str(vd) if vd else None,
                    "document_id": row.get("document_id"),
                    "chunk_excerpt": f"{name} {val_s}".strip(),
                }
            )

    chunks = bundle.get("chunks") or []
    ranked_chunks: list[tuple[int, dict]] = []
    for hit in chunks:
        clean = _sanitize_text(hit.get("text") or "")
        if _is_noisy_text(clean):
            continue
        text = clean.lower()
        score = sum(1 for tok in q_tokens if tok in text)
        ranked_chunks.append((score, {**hit, "text": clean}))
    ranked_chunks.sort(key=lambda x: x[0], reverse=True)
    selected_chunks = [h for _, h in ranked_chunks[:3]]

    def _build_cites_from_chunks(limit: int = 2) -> list[dict[str, Any]]:
        out: list[dict[str, Any]] = []
        for hit in selected_chunks[:limit]:
            meta = hit.get("metadata") or {}
            excerpt = _sanitize_text(hit.get("text") or "")[:320]
            if not excerpt:
                continue
            out.append(
                {
                    "visit_date": meta.get("visit_date"),
                    "document_id": meta.get("document_id"),
                    "chunk_excerpt": excerpt,
                }
            )
        return out

    joined = " ".join((h.get("text") or "") for h in selected_chunks).lower()
    prognosis_match = re.search(
        r"(estimated|prognosis)[^\.]{0,100}?(\d+\s*(?:-|to)\s*\d+\s*(?:day|days|week|weeks|month|months))",
        joined,
    )
    if _ASK_WORSE.search(q):
        worsening = any(
            k in joined for k in ("progression", "disease progression", "functional decline", "hospice", "poor oral intake")
        )
        if worsening:
            msg = "Yes, your recent records suggest your health is worsening, mainly from disease progression and functional decline."
        else:
            msg = "I do not see clear evidence of worsening in the latest note alone."
        if prognosis_match:
            msg += f" The note also mentions an estimated prognosis of {prognosis_match.group(2)}."
        return msg, []
    if _ASK_SURVIVAL.search(q):
        msg = "I cannot predict exact survival time, but I can share what your latest note says."
        if prognosis_match:
            msg += f" It records an estimated prognosis of {prognosis_match.group(2)}."
        else:
            msg += " I do not see a clear time estimate in the available text."
        return msg, []
    if _ASK_LAST_VISIT_SUMMARY.search(q):
        if not selected_chunks:
            return (
                "I cannot find a clear latest visit note in the available records. "
                "Please ask your care team or upload the latest report.",
                [],
            )
        first_meta = selected_chunks[0].get("metadata") or {}
        visit_date = first_meta.get("visit_date")
        key_points: list[str] = []
        seen: set[str] = set()
        for hit in selected_chunks:
            t = _sanitize_text(hit.get("text") or "")
            if not t:
                continue
            first_sentence = re.split(r"(?<=[\.\!\?])\s+", t, maxsplit=1)[0].strip()
            if len(first_sentence) < 20:
                continue
            norm = first_sentence.lower()
            if norm in seen:
                continue
            seen.add(norm)
            key_points.append(first_sentence.rstrip("."))
            if len(key_points) >= 2:
                break
        if not key_points:
            key_points = ["I found the visit note, but the text is limited."]
        if visit_date:
            answer = f"Your latest visit ({visit_date}) says: {key_points[0]}."
        else:
            answer = f"Your latest visit says: {key_points[0]}."
        if len(key_points) > 1:
            answer += f" Also, {key_points[1]}."
        return answer, _build_cites_from_chunks(limit=2)

    cites.extend(_build_cites_from_chunks(limit=3))

    if not lines and selected_chunks:
        if any(w in q for w in ("blood", "lab", "hemoglobin", "a1c", "glucose")):
            lines.append(
                "I do not see clear blood test values in your latest note. "
                "The note is focused on hospice care, symptom control, and support planning."
            )
        else:
            summaries = []
            for hit in selected_chunks[:2]:
                t = _sanitize_text(hit.get("text") or "")
                if not t:
                    continue
                first_sentence = re.split(r"(?<=[\.\!\?])\s+", t, maxsplit=1)[0]
                summaries.append((first_sentence or t)[:180])
            if summaries:
                lines.append(f"Based on your latest records: {summaries[0]}")
            if len(summaries) > 1:
                lines.append(f"Also: {summaries[1]}")

    if bundle.get("reference_snippets") and not lines:
        lines.append("Here is trusted general information (not specific to your chart):")
        for hit in bundle["reference_snippets"][:2]:
            lines.append(f"- {(hit.get('text') or '')[:400]}")

    if not lines:
        lines.append(
            "I could not find enough information in your uploaded records to answer that safely. "
            "Try rephrasing, or ask your care team."
        )

    answer = " ".join(lines) if len(lines) == 1 else "\n".join(lines)
    return answer, cites[:8]


def generate_answer(
    question: str,
    bundle: dict,
    *,
    detail_level: str = "full",
) -> tuple[str, list[dict[str, Any]]]:
    """
    Returns (answer, citations_metadata) where each citation has
    visit_date, document_id, chunk_excerpt.
    """
    context = _format_context_bundle(bundle)
    system = _load_system_prompt(detail_level)

    user = (
        f"PATIENT QUESTION:\n{question}\n\n"
        f"RETRIEVED CONTEXT:\n{context}\n\n"
        "Respond with ONLY valid JSON (no markdown fences) in this shape:\n"
        '{"answer":"<plain language, 6th-grade reading level>",'
        '"citations":[{"visit_date":"YYYY-MM-DD or null","document_id":"uuid or null",'
        '"chunk_excerpt":"short quote"}]}\n'
        "Rules: Use ONLY facts supported by RETRIEVED CONTEXT. "
        "If something is unknown from context, say so. "
        "Never recommend changing doses or stopping medications. "
        "Citations should align with note excerpts when possible."
    )

    prompt = f"<|system|>\n{system}\n<|user|>\n{user}\n<|assistant|>\n"

    # Try watsonx first (skip for a while after auth failures to reduce latency)
    global _WATSONX_SKIP_UNTIL, _WATSONX_LAST_CREDS
    creds_sig = "|".join(
        [
            os.getenv("WATSONX_API_KEY", "")[:16],
            os.getenv("WATSONX_PROJECT_ID", ""),
            os.getenv("WATSONX_URL", ""),
            os.getenv("WATSONX_MODEL_ID", ""),
        ]
    )
    # If credentials were updated during runtime, retry watsonx immediately.
    if creds_sig != _WATSONX_LAST_CREDS:
        _WATSONX_SKIP_UNTIL = 0.0
        _WATSONX_LAST_CREDS = creds_sig
    try:
        if time.time() >= _WATSONX_SKIP_UNTIL:
            from .watsonx_client import generate_text, watsonx_configured

            if watsonx_configured():
                raw = generate_text(prompt, max_new_tokens=320, temperature=0.2)
                answer, cites = _parse_generation_json(raw)
                if answer:
                    if not cites:
                        for hit in (bundle.get("chunks") or [])[:3]:
                            meta = hit.get("metadata") or {}
                            cites.append(
                                {
                                    "visit_date": meta.get("visit_date"),
                                    "document_id": meta.get("document_id"),
                                    "chunk_excerpt": (hit.get("text") or "")[:280],
                                }
                            )
                    return answer, cites
    except Exception as e:
        msg = str(e).lower()
        if "invalidcredentials" in msg or "api key" in msg or "bxnim0415e" in msg:
            _WATSONX_SKIP_UNTIL = time.time() + 1800  # 30 min

    # Fallback: Featherless AI
    api_key = os.getenv("FEATHERLESS_API_KEY")
    print(f"[generation] watsonx skipped, trying Featherless (key={'set' if api_key else 'MISSING'})")
    if api_key:
        models = [
            m.strip()
            for m in os.getenv(
                "FEATHERLESS_MODELS",
                "meta-llama/Llama-3.3-70B-Instruct,deepseek-ai/DeepSeek-R1-0528",
            ).split(",")
            if m.strip()
        ]
        try:
            import requests
            messages = [
                {"role": "system", "content": system},
                {"role": "user", "content": user},
            ]
            for model in models:
                try:
                    resp = requests.post(
                        "https://api.featherless.ai/v1/chat/completions",
                        headers={
                            "Authorization": f"Bearer {api_key}",
                            "Content-Type": "application/json",
                        },
                        json={
                            "model": model,
                            "messages": messages,
                            "max_tokens": 320,
                            "temperature": 0.2,
                        },
                        timeout=8,
                    )
                    if resp.status_code >= 400:
                        print(f"[generation] Featherless {model} failed with status {resp.status_code}")
                        continue
                    payload = resp.json()
                    raw = ((payload.get("choices") or [{}])[0].get("message") or {}).get("content", "").strip()
                    if not raw:
                        continue
                    answer, cites = _parse_generation_json(raw)
                    if answer:
                        if not cites:
                            # Keep concise but still provide references for UI.
                            for hit in (bundle.get("chunks") or [])[:3]:
                                meta = hit.get("metadata") or {}
                                cites.append(
                                    {
                                        "visit_date": meta.get("visit_date"),
                                        "document_id": meta.get("document_id"),
                                        "chunk_excerpt": (hit.get("text") or "")[:280],
                                    }
                                )
                        return answer, cites
                except Exception as me:
                    print(f"[generation] Featherless model {model} failed: {me}")
        except Exception as e:
            print(f"[generation] Featherless fallback failed: {e}")

    return _fallback_answer(question, bundle)
