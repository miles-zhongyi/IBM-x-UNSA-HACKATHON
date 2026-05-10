from __future__ import annotations

from datetime import datetime, timezone
import json
import re
import time
from typing import Any
from uuid import uuid4

from fastapi import APIRouter, File, Form, HTTPException, Query, Response, UploadFile
from pydantic import BaseModel

from backend.chat.service import answer_patient_question
from backend.chat.translation_1 import detect_input_language, translate_if_needed
from backend.ingestion.pipeline import ingest_text
from backend.ingestion.storage import (
    get_active_medications,
    get_conn,
    get_diagnoses,
    get_patient_timeline,
)

router = APIRouter()

_DOCTOR_PROFILE = {
    "id": "doctor-demo",
    "name": "Dr. Sarah Chen",
    "specialty": "Internal Medicine",
    "qualifications": "MD, Board Certified Internal Medicine",
    "clinic": "UNSA Demo Clinic",
    "email": "sarah.chen@demo.local",
    "phone": "+1 555-0110",
    "avatar": "https://api.dicebear.com/9.x/thumbs/svg?seed=Dr%20Sarah%20Chen",
}

_PATIENT_SEEDS: dict[str, dict[str, Any]] = {
    "marcus-demo": {
        "name": "Marcus Hale",
        "age": 58,
        "sex": "M",
        "email": "marcus.hale@demo.local",
        "phone": "+1 555-0171",
    },
    "elena-demo": {
        "name": "Elena Ruiz",
        "age": 43,
        "sex": "F",
        "email": "elena.ruiz@demo.local",
        "phone": "+1 555-0132",
    },
    "dorothy-demo": {
        "name": "Dorothy Price",
        "age": 79,
        "sex": "F",
        "email": "dorothy.price@demo.local",
        "phone": "+1 555-0188",
    },
}

_THREADS: dict[str, dict[str, Any]] = {}
_MESSAGES: dict[str, list[dict[str, Any]]] = {}
_CHAT_CACHE: dict[tuple[str, str], tuple[float, dict[str, Any]]] = {}
_ANSWER_FIELD = re.compile(r'"answer"\s*:\s*"((?:[^"\\]|\\.)*)"', re.S)
_CTRL = re.compile(r"[\x00-\x08\x0B\x0C\x0E-\x1F\x7F]")
_BINARY_ARTIFACT = re.compile(r"(%PDF-|xref|endobj|stream|/Linearized|obj\s*<<)", re.I)


class QueryCreateBody(BaseModel):
    patient_id: str
    subject: str
    text: str


class QueryMessageBody(BaseModel):
    sender: str
    text: str


class AISuggestBody(BaseModel):
    thread_id: str


class AIChatBody(BaseModel):
    patient_id: str
    text: str
    session_id: str | None = None


class TranslateBody(BaseModel):
    text: str
    target_lang: str = "en"


class TtsBody(BaseModel):
    text: str


def _now_iso() -> str:
    return datetime.now(timezone.utc).isoformat()


def _avatar_for(patient_id: str, name: str) -> str:
    return f"https://api.dicebear.com/9.x/thumbs/svg?seed={patient_id}-{name.replace(' ', '-')}"


def _to_iso(value: Any) -> str:
    if value is None:
        return _now_iso()
    if isinstance(value, str):
        return value
    if hasattr(value, "isoformat"):
        return value.isoformat()
    return str(value)


def _patient_ids() -> list[str]:
    conn = get_conn()
    try:
        rows = conn.execute(
            "SELECT DISTINCT patient_id FROM documents ORDER BY patient_id ASC",
        ).fetchall()
        ids = [str(r["patient_id"]) for r in rows if r["patient_id"]]
    finally:
        conn.close()
    if not ids:
        return list(_PATIENT_SEEDS.keys())
    return ids


def _patient_seed(patient_id: str) -> dict[str, Any]:
    seed = _PATIENT_SEEDS.get(patient_id)
    if seed:
        return seed
    pretty = patient_id.replace("-", " ").replace("_", " ").title()
    return {
        "name": pretty,
        "age": 50,
        "sex": "N/A",
        "email": f"{patient_id}@demo.local",
        "phone": "+1 555-0100",
    }


def _ensure_demo_threads() -> None:
    if _THREADS:
        return
    for patient_id in _patient_ids():
        thread_id = str(uuid4())
        seed = _patient_seed(patient_id)
        created = _now_iso()
        _THREADS[thread_id] = {
            "id": thread_id,
            "patient_id": patient_id,
            "patient_name": seed["name"],
            "subject": "Question about my latest results",
            "status": "unanswered",
            "has_attachment": False,
            "last_message_at": created,
        }
        _MESSAGES[thread_id] = [
            {
                "id": str(uuid4()),
                "sender": "patient",
                "sender_name": seed["name"],
                "text": "Could you explain what changed in my latest labs?",
                "created_at": created,
            }
        ]


def _documents_for(patient_id: str) -> list[dict[str, Any]]:
    docs = []
    for item in get_patient_timeline(patient_id):
        docs.append(
            {
                "id": item.get("id"),
                "title": item.get("chief_complaint") or item.get("summary") or item.get("source_label") or "Clinical document",
                "doc_type": item.get("document_type") or "record",
                "created_at": _to_iso(item.get("visit_date")),
                # Keep not-completed to avoid dead download links in UI.
                "status": "ready",
                "storage_path": "",
            }
        )
    return docs


def _threads_for(patient_id: str) -> list[dict[str, Any]]:
    _ensure_demo_threads()
    out = [t for t in _THREADS.values() if t["patient_id"] == patient_id]
    out.sort(key=lambda x: x.get("last_message_at") or "", reverse=True)
    return out


def _patient_core(patient_id: str) -> dict[str, Any]:
    seed = _patient_seed(patient_id)
    timeline = get_patient_timeline(patient_id)
    diagnoses = get_diagnoses(patient_id)
    medications = get_active_medications(patient_id)
    threads = _threads_for(patient_id)

    conditions = sorted({d.get("name") for d in diagnoses if d.get("name")})[:6]
    meds = sorted({m.get("name") for m in medications if m.get("name")})[:6]
    last_activity = _to_iso(timeline[0].get("visit_date")) if timeline else _now_iso()
    pending = sum(1 for t in threads if t.get("status") in ("unanswered", "urgent"))
    summary_text = timeline[0].get("summary") if timeline else ""
    ai_summary = summary_text or "No AI summary yet."

    return {
        "id": patient_id,
        "name": seed["name"],
        "age": seed["age"],
        "sex": seed["sex"],
        "email": seed["email"],
        "phone": seed["phone"],
        "avatar": _avatar_for(patient_id, seed["name"]),
        "status": "active",
        "pending_questions": pending,
        "last_activity": last_activity,
        "conditions": conditions,
        "medications": meds,
        "allergies": ["No known allergies"],
        "ai_summary": ai_summary,
    }


@router.get("/patients")
def list_patients(
    search: str | None = Query(None),
    status: str | None = Query(None),
) -> list[dict[str, Any]]:
    rows = [_patient_core(pid) for pid in _patient_ids()]
    if search:
        low = search.lower()
        rows = [r for r in rows if low in r["name"].lower()]
    if status == "unread":
        rows = [r for r in rows if r["pending_questions"] > 0]
    elif status in {"active", "inactive"}:
        rows = [r for r in rows if r["status"] == status]
    return rows


@router.get("/patients/{patient_id}")
def get_patient_detail(patient_id: str) -> dict[str, Any]:
    patient = _patient_core(patient_id)
    return {
        "patient": patient,
        "documents": _documents_for(patient_id),
        "threads": _threads_for(patient_id),
    }


@router.get("/dashboard/patient/{patient_id}")
def get_patient_dashboard(patient_id: str) -> dict[str, Any]:
    patient = _patient_core(patient_id)
    docs = _documents_for(patient_id)
    threads = _threads_for(patient_id)
    return {
        "patient": patient,
        "recent_documents": docs[:6],
        "recent_threads": threads[:6],
    }


@router.get("/dashboard/doctor")
def get_doctor_dashboard() -> dict[str, Any]:
    patients = [_patient_core(pid) for pid in _patient_ids()]
    all_threads: list[dict[str, Any]] = []
    for p in patients:
        all_threads.extend(_threads_for(p["id"]))
    all_threads.sort(key=lambda x: x.get("last_message_at") or "", reverse=True)
    now = _now_iso()
    trend = [
        {"day": "Mon", "messages": 6, "uploads": 3},
        {"day": "Tue", "messages": 7, "uploads": 2},
        {"day": "Wed", "messages": 8, "uploads": 4},
        {"day": "Thu", "messages": 5, "uploads": 3},
        {"day": "Fri", "messages": 9, "uploads": 5},
        {"day": "Sat", "messages": 4, "uploads": 1},
        {"day": "Sun", "messages": 3, "uploads": 1},
    ]
    alerts = [
        {
            "id": "alert-missing-followup",
            "severity": "warning",
            "title": "Pending follow-up",
            "description": "One patient has an unanswered query older than 24h.",
            "created_at": now,
        }
    ] if any(t["status"] == "unanswered" for t in all_threads) else []
    activity = _build_activity(limit=20)

    return {
        "stats": {
            "total_patients": len(patients),
            "pending_questions": sum(1 for t in all_threads if t["status"] == "unanswered"),
            "urgent_queries": sum(1 for t in all_threads if t["status"] == "urgent"),
            "recent_uploads": sum(len(_documents_for(p["id"])[:3]) for p in patients),
            "failed_uploads": 0,
        },
        "alerts": alerts,
        "activity": activity,
        "trend": trend,
    }


def _build_activity(limit: int = 6) -> list[dict[str, Any]]:
    items: list[dict[str, Any]] = []
    for pid in _patient_ids():
        patient = _patient_core(pid)
        for d in _documents_for(pid)[:2]:
            items.append(
                {
                    "id": f"doc-{d['id']}",
                    "kind": "upload",
                    "title": f"{patient['name']} document added",
                    "description": d["title"],
                    "created_at": d["created_at"],
                }
            )
        for t in _threads_for(pid)[:2]:
            items.append(
                {
                    "id": f"thread-{t['id']}",
                    "kind": "message",
                    "title": f"Message from {patient['name']}",
                    "description": t["subject"],
                    "created_at": t["last_message_at"],
                }
            )
    items.sort(key=lambda x: x.get("created_at") or "", reverse=True)
    return items[:limit]


def _clean_display_text(text: Any) -> str:
    t = _CTRL.sub(" ", str(text or ""))
    t = t.replace("\r", " ").replace("\n", " ")
    return re.sub(r"\s+", " ", t).strip()


def _looks_noisy(text: str) -> bool:
    t = _clean_display_text(text)
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
    non_ascii = sum(1 for c in t if ord(c) > 127)
    weird = sum(1 for c in t if not (c.isalnum() or c.isspace() or c in ".,;:!?-()[]/%'\"+"))
    if (alpha_chars / total) < 0.45 and ((punct + digit_chars) / total) > 0.25:
        return True
    if (non_ascii / total) > 0.12:
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
    return False


def _normalize_ai_output(raw: dict[str, Any]) -> tuple[str, list[dict[str, Any]]]:
    reply = _clean_display_text(raw.get("answer") or "")
    cites = raw.get("citations") if isinstance(raw.get("citations"), list) else []
    if reply.startswith("{") and "\"answer\"" in reply:
        try:
            parsed = json.loads(reply)
            if isinstance(parsed, dict):
                reply = _clean_display_text(parsed.get("answer") or reply)
                parsed_cites = parsed.get("citations")
                if isinstance(parsed_cites, list) and not cites:
                    cites = parsed_cites
        except Exception:
            m = _ANSWER_FIELD.search(reply)
            if m:
                frag = m.group(1)
                try:
                    reply = json.loads(f'"{frag}"')
                except Exception:
                    reply = _clean_display_text(frag.replace('\\"', '"').replace("\\n", "\n"))
    cleaned_lines = []
    for line in reply.splitlines():
        if _looks_noisy(line):
            continue
        cleaned_lines.append(line)
    reply = "\n".join(cleaned_lines).strip() or "I could not parse a clear answer. Please try rephrasing your question."
    return reply, cites


@router.get("/activity")
def get_activity(limit: int = Query(6, ge=1, le=100)) -> list[dict[str, Any]]:
    return _build_activity(limit=limit)


@router.get("/doctors/me")
def get_doctor_me() -> dict[str, Any]:
    return _DOCTOR_PROFILE


@router.get("/queries")
def list_queries(
    status: str | None = Query(None),
    patient_id: str | None = Query(None),
) -> list[dict[str, Any]]:
    _ensure_demo_threads()
    rows = list(_THREADS.values())
    if patient_id:
        rows = [r for r in rows if r["patient_id"] == patient_id]
    if status and status != "all":
        rows = [r for r in rows if r["status"] == status]
    rows.sort(key=lambda x: x.get("last_message_at") or "", reverse=True)
    return rows


@router.get("/queries/{thread_id}")
def get_query_thread(thread_id: str) -> dict[str, Any]:
    _ensure_demo_threads()
    thread = _THREADS.get(thread_id)
    if not thread:
        # Frontend can hold stale IDs across backend restarts in dev.
        # Return a safe empty thread payload instead of 404 to prevent UI crashes.
        return {
            "thread": {
                "id": thread_id,
                "patient_id": "",
                "patient_name": "Unknown patient",
                "subject": "Conversation unavailable",
                "status": "archived",
                "has_attachment": False,
                "last_message_at": _now_iso(),
            },
            "messages": [],
        }
    return {
        "thread": thread,
        "messages": _MESSAGES.get(thread_id, []),
    }


@router.post("/queries")
def create_query(body: QueryCreateBody) -> dict[str, Any]:
    _ensure_demo_threads()
    patient = _patient_core(body.patient_id)
    tid = str(uuid4())
    created = _now_iso()
    thread = {
        "id": tid,
        "patient_id": body.patient_id,
        "patient_name": patient["name"],
        "subject": body.subject.strip(),
        "status": "unanswered",
        "has_attachment": False,
        "last_message_at": created,
    }
    _THREADS[tid] = thread
    _MESSAGES[tid] = [
        {
            "id": str(uuid4()),
            "sender": "patient",
            "sender_name": patient["name"],
            "text": body.text.strip(),
            "created_at": created,
        }
    ]
    return thread


@router.post("/queries/{thread_id}/messages")
def post_query_message(thread_id: str, body: QueryMessageBody) -> dict[str, Any]:
    _ensure_demo_threads()
    thread = _THREADS.get(thread_id)
    if not thread:
        return {"ok": False, "detail": "thread not found"}
    sender = body.sender if body.sender in {"patient", "doctor"} else "patient"
    sender_name = _DOCTOR_PROFILE["name"] if sender == "doctor" else thread["patient_name"]
    created = _now_iso()
    msg = {
        "id": str(uuid4()),
        "sender": sender,
        "sender_name": sender_name,
        "text": body.text.strip(),
        "created_at": created,
    }
    _MESSAGES.setdefault(thread_id, []).append(msg)
    thread["last_message_at"] = created
    thread["status"] = "answered" if sender == "doctor" else "unanswered"
    return {"ok": True}


@router.post("/ai/suggest-reply")
def ai_suggest_reply(body: AISuggestBody) -> dict[str, str]:
    thread = _THREADS.get(body.thread_id)
    if not thread:
        return {
            "suggestion": "I reviewed your message. Based on current records, please monitor your symptoms and contact your care team if they worsen."
        }
    subject = thread.get("subject") or "their message"
    return {
        "suggestion": f"Thanks for your question about {subject.lower()}. I reviewed your records and recommend we continue monitoring your symptoms. If anything worsens, please contact us immediately."
    }


@router.post("/ai/chat")
def ai_chat(body: AIChatBody) -> dict[str, Any]:
    cache_key = (body.patient_id, (body.text or "").strip().lower())
    now = time.time()
    cached = _CHAT_CACHE.get(cache_key)
    if cached and now - cached[0] < 300:
        payload = dict(cached[1])
        fixed_reply, _ = _normalize_ai_output({"answer": payload.get("reply", ""), "citations": []})
        payload["reply"] = fixed_reply
        payload["session_id"] = body.session_id or str(uuid4())
        return payload

    try:
        raw = answer_patient_question(body.patient_id, body.text, detail_level="basic")
    except Exception:
        timeline = get_patient_timeline(body.patient_id)
        fallback = (
            timeline[0].get("summary")
            if timeline and timeline[0].get("summary")
            else "I could not run full retrieval right now, but your records are available and your care team can help with specific concerns."
        )
        raw = {"answer": fallback, "citations": []}
    reply_text, raw_citations = _normalize_ai_output(raw)
    sources = []
    seen: set[tuple[str, str, str]] = set()
    for i, c in enumerate(raw_citations, 1):
        doc_id = str(c.get("document_id") or "")
        date = str(c.get("visit_date") or "unknown date")
        excerpt = _clean_display_text(c.get("chunk_text") or c.get("chunk_excerpt") or "")
        if _looks_noisy(excerpt):
            continue
        dedupe_key = (doc_id, date, excerpt[:120])
        if dedupe_key in seen:
            continue
        seen.add(dedupe_key)
        sources.append(
            {
                "id": f"c{i}",
                "index": len(sources) + 1,
                "label": f"[{len(sources) + 1}]",
                "document_id": doc_id or None,
                "visit_date": date,
                "excerpt": excerpt[:280],
            }
        )
        if len(sources) >= 4:
            break
    payload = {
        "session_id": body.session_id or str(uuid4()),
        "reply": reply_text,
        "sources": sources,
    }
    _CHAT_CACHE[cache_key] = (now, {k: v for k, v in payload.items() if k != "session_id"})
    return payload


@router.post("/translate")
def translate(body: TranslateBody) -> dict[str, str]:
    src = detect_input_language(body.text or "")
    translated = translate_if_needed(body.text or "", source_lang=src, target_lang=body.target_lang or "en")
    return {"translated": translated}


@router.post("/upload")
async def upload_document(
    patient_id: str = Form(...),
    doc_type: str = Form("other"),
    title: str = Form("Uploaded document"),
    file: UploadFile = File(...),
) -> dict[str, Any]:
    raw = await file.read()
    text = raw.decode("utf-8", errors="ignore").strip()
    # Avoid indexing binary artifacts (e.g., raw PDF bytes decoded as text).
    if raw[:5] == b"%PDF-" or _looks_noisy(text):
        text = (
            f"{title}\n\nUploaded file: {file.filename or title}. "
            "This file format could not be parsed into clean text in demo mode."
        )
    if not text:
        text = f"{title}\n\nDocument type: {doc_type}. Uploaded file: {file.filename}."
    result = ingest_text(text, patient_id=patient_id, source_label=file.filename or title)
    return {"ok": True, "document_id": result.document_id, "status": result.status}


@router.get("/files/{storage_path:path}")
def files_proxy(storage_path: str) -> dict[str, str]:
    raise HTTPException(status_code=404, detail=f"file not available: {storage_path}")


@router.post("/voice/transcribe")
async def voice_transcribe(file: UploadFile = File(...)) -> dict[str, str]:
    _ = await file.read()
    return {"text": ""}


@router.post("/voice/tts")
def voice_tts(body: TtsBody) -> Response:
    # Minimal silent WAV header + silence payload so the UI audio control still works.
    _ = body.text
    wav = (
        b"RIFF$\x00\x00\x00WAVEfmt "
        b"\x10\x00\x00\x00\x01\x00\x01\x00@\x1f\x00\x00@\x1f\x00\x00"
        b"\x01\x00\x08\x00data\x00\x00\x00\x00"
    )
    return Response(content=wav, media_type="audio/wav")
