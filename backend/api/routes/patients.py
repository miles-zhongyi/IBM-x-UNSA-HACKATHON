from __future__ import annotations

import tempfile
from pathlib import Path

from fastapi import APIRouter, File, HTTPException, Query, UploadFile

from backend.chat.service import answer_patient_question
from backend.ingestion.models import IngestionResult
from backend.ingestion.pipeline import ingest_document, ingest_text
from backend.ingestion.storage import (
    get_active_medications,
    get_all_labs,
    get_diagnoses,
    get_lab_trend,
    get_patient_timeline,
)

from ..schemas import ChatRequest, ChatResponse, CitationOut, DocumentIngestBody, EscalateBody, EscalateResponse
from ..escalation_store import create_escalation

router = APIRouter()


@router.post("/{patient_id}/documents", response_model=IngestionResult)
def post_document(patient_id: str, body: DocumentIngestBody) -> IngestionResult:
    return ingest_text(body.text, patient_id=patient_id, source_label=body.source_label)


@router.post("/{patient_id}/documents/file", response_model=IngestionResult)
async def post_document_file(patient_id: str, file: UploadFile = File(...)) -> IngestionResult:
    """Upload PDF / DOCX / DOC; text is extracted then ingested like pasted notes."""
    suffix = Path(file.filename or "").suffix.lower() or ".pdf"
    raw = await file.read()
    if not raw:
        raise HTTPException(status_code=400, detail="empty file")
    tmp = tempfile.NamedTemporaryFile(delete=False, suffix=suffix)
    tmp_path = tmp.name
    try:
        tmp.write(raw)
        tmp.flush()
    finally:
        tmp.close()
    try:
        return ingest_document(
            tmp_path,
            patient_id=patient_id,
            source_label=file.filename or "upload",
        )
    finally:
        Path(tmp_path).unlink(missing_ok=True)


@router.get("/{patient_id}/timeline")
def get_timeline(patient_id: str) -> list[dict]:
    return get_patient_timeline(patient_id)


@router.get("/{patient_id}/diagnoses")
def get_diagnoses_route(
    patient_id: str,
    active_only: bool = Query(False),
) -> list[dict]:
    return get_diagnoses(patient_id, active_only=active_only)


@router.get("/{patient_id}/medications")
def get_medications_route(patient_id: str) -> list[dict]:
    return get_active_medications(patient_id)


@router.get("/{patient_id}/labs")
def get_labs_route(patient_id: str) -> list[dict]:
    return get_all_labs(patient_id)


@router.get("/{patient_id}/labs/trend")
def get_labs_trend_route(patient_id: str, lab_name: str = Query(..., min_length=1)) -> list[dict]:
    return get_lab_trend(patient_id, lab_name)


@router.post("/{patient_id}/chat", response_model=ChatResponse)
def post_chat(patient_id: str, body: ChatRequest) -> ChatResponse:
    raw = answer_patient_question(
        patient_id,
        body.question,
        language=body.language,
        detail_level=body.detail_level,
    )
    cites = [CitationOut(**c) for c in raw.get("citations", [])]
    return ChatResponse(
        answer=raw.get("answer", ""),
        citations=cites,
        escalated=raw.get("escalated", False),
        safety_triggered=raw.get("safety_triggered", False),
        trend=raw.get("trend"),
    )


@router.post("/{patient_id}/escalate", response_model=EscalateResponse)
def post_escalate(patient_id: str, body: EscalateBody) -> EscalateResponse:
    if not (body.question or "").strip():
        raise HTTPException(status_code=400, detail="question is required")
    ticket_id = create_escalation(patient_id, body.question.strip(), body.context)
    return EscalateResponse(ticket_id=ticket_id, status="queued")
