"""Clinical ingestion: SQLite + Chroma. Downstream reads via `storage` + `embedding` + `pipeline`."""

from .embedding import embed_query, embed_texts
from .models import IngestionResult
from .pipeline import ingest_document, ingest_text
from .storage import (
    get_active_medications,
    get_all_labs,
    get_diagnoses,
    get_document_by_id,
    get_lab_trend,
    get_patient_timeline,
    reset_all,
    search_chunks,
)

__all__ = [
    "embed_query",
    "embed_texts",
    "ingest_text",
    "ingest_document",
    "IngestionResult",
    "get_active_medications",
    "get_all_labs",
    "get_diagnoses",
    "get_document_by_id",
    "get_lab_trend",
    "get_patient_timeline",
    "reset_all",
    "search_chunks",
]
