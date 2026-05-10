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
            text = (hit.get("text", "") or "").replace("\n", " ")[:320]
            parts.append(
                f"{i}. [{meta.get('title', 'topic')}] {text}\n"
                f"   Source: {meta.get('source', 'reference corpus')}\n"
            )

    if bundle.get("chunks"):
        parts.append("\n=== RELEVANT NOTE EXCERPTS (patient's records) ===\n")
        for i, hit in enumerate(bundle["chunks"][:3], 1):
            meta = hit.get("metadata") or {}
            text = (hit.get("text", "") or "").replace("\n", " ")[:360]
            parts.append(
                f"{i}. [Visit: {meta.get('visit_date', 'unknown')}] "
                f"[document_id={meta.get('document_id')}] [section={meta.get('section')}]\n"
                f"{text}\n"
            )

    return "\n".join(parts) if parts else "(No retrieved context — say you cannot find it in the records.)"


_JSON_BLOCK = re.compile(r"\{[\s\S]*\}\s*$")
_ANSWER_FIELD = re.compile(r'"answer"\s*:\s*"((?:[^"\\]|\\.)*)"', re.S)
_WATSONX_SKIP_UNTIL = 0.0


def _parse_generation_json(raw: str) -> tuple[str, list[dict[str, Any]]]:
    """Expect model to return JSON with answer + citations."""
    text = raw.strip()
    if text.startswith("```"):
        text = re.sub(r"^```(?:json)?\s*", "", text)
        text = re.sub(r"\s*```$", "", text)
    try:
        data = json.loads(text)
        answer = str(data.get("answer", "")).strip()
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
                    "chunk_excerpt": c.get("chunk_excerpt") or c.get("excerpt") or "",
                }
            )
        return answer, norm
    except json.JSONDecodeError:
        m = _JSON_BLOCK.search(text)
        if m:
            try:
                data = json.loads(m.group(0))
                return str(data.get("answer", text)).strip(), data.get("citations") or []
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
            return str(answer).strip(), []
        return text, []


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

    for hit in bundle.get("chunks") or []:
        meta = hit.get("metadata") or {}
        excerpt = (hit.get("text") or "")[:320]
        cites.append(
            {
                "visit_date": meta.get("visit_date"),
                "document_id": meta.get("document_id"),
                "chunk_excerpt": excerpt,
            }
        )

    if not lines and bundle.get("chunks"):
        lines.append("Here are the most relevant excerpts from your records:")
        for hit in bundle["chunks"][:3]:
            t = (hit.get("text") or "").replace("\n", " ")[:400]
            lines.append(f"- {t}")

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
    global _WATSONX_SKIP_UNTIL
    try:
        if time.time() >= _WATSONX_SKIP_UNTIL:
            from .watsonx_client import generate_text, watsonx_configured

            if watsonx_configured():
                raw = generate_text(prompt, max_new_tokens=420, temperature=0.2)
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
                            "max_tokens": 420,
                            "temperature": 0.2,
                        },
                        timeout=10,
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
