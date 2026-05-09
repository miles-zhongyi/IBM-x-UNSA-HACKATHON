from __future__ import annotations

from fastapi import APIRouter, HTTPException

from backend.ingestion.storage import get_document_by_id

router = APIRouter()


@router.get("/{document_id}")
def get_document(document_id: str) -> dict:
    doc = get_document_by_id(document_id)
    if not doc:
        raise HTTPException(status_code=404, detail="document not found")
    return doc
