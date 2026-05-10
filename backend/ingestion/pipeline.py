"""
The ingestion pipeline.

Public entry points:
  - ingest_text(text, patient_id, source_label)
  - ingest_document(path, patient_id, source_label)  — PDF / DOCX / DOC

Flow:
  raw text  →  LLM extraction  →  SQLite (structured)
                              ↘
                                chunk + embed  →  ChromaDB (vectors)
"""

from __future__ import annotations

import uuid
from pathlib import Path
from typing import Optional, Union

from .chunking import chunk_document
from .document_reader import SUPPORTED_EXTENSIONS, read_document_safe
from .embedding import embed_texts
from .extraction_extensions import extract_structured_from_parsed
from .models import IngestionResult
from .storage import save_document, store_chunks_in_chroma, init_db


def ingest_text(
        text: str,
        patient_id: str,
        source_label: str = "pasted",
) -> IngestionResult:
    """
    Process a single clinical document and persist it to the stores.

    Args:
        text: Raw text of the note (any clinical document).
        patient_id: Identifier for the patient this document belongs to.
        source_label: Where the text came from (e.g., "pasted", "visit_2024_03.pdf").

    Returns:
        IngestionResult — document_id, summary, counts, and status.
    """
    # Lazy-init the DB schema. Idempotent.
    init_db()

    # Validate input
    text = (text or "").strip()
    if len(text) < 50:
        return IngestionResult(
            document_id="",
            patient_id=patient_id,
            status="failed",
            summary="",
            document_type="unknown",
            extracted_counts={},
            chunks_indexed=0,
            error="Document too short to process (must be at least 50 characters).",
        )

    document_id = str(uuid.uuid4())

    try:
        # 1. Extract structured data (the big LLM call, or heuristic fallback)
        extracted = extract_structured_from_parsed(text, source_label=source_label)

        # 2. Persist structured data to SQLite
        save_document(
            document_id=document_id,
            patient_id=patient_id,
            extracted=extracted,
            raw_text=text,
            source_label=source_label,
        )

        # 3. Chunk the document
        chunks = chunk_document(
            text=text,
            document_id=document_id,
            patient_id=patient_id,
            extracted=extracted,
        )

        # 4. Embed all chunks in one batch
        embeddings = embed_texts([c["text"] for c in chunks])

        # 5. Persist chunks + embeddings to ChromaDB
        store_chunks_in_chroma(chunks, embeddings)

        # 6. Build the result
        return IngestionResult(
            document_id=document_id,
            patient_id=patient_id,
            status="processed",
            summary=extracted.summary,
            document_type=extracted.document_type,
            visit_date=extracted.visit_date,
            extracted_counts={
                "diagnoses": len(extracted.diagnoses),
                "medications": len(extracted.medications),
                "lab_values": len(extracted.lab_values),
                "instructions": len(extracted.instructions_to_patient),
            },
            chunks_indexed=len(chunks),
        )

    except Exception as e:
        import traceback
        traceback.print_exc()
        return IngestionResult(
            document_id=document_id,
            patient_id=patient_id,
            status="failed",
            summary="",
            document_type="unknown",
            extracted_counts={},
            chunks_indexed=0,
            error=f"{type(e).__name__}: {e}",
        )


def ingest_document(
    path: Union[str, Path],
    patient_id: str,
    source_label: str = "",
) -> IngestionResult:
    """
    Extract text from PDF / DOCX / DOC and run through `ingest_text()`.
    """
    path = Path(path)
    label = source_label or path.name

    if path.suffix.lower() not in SUPPORTED_EXTENSIONS:
        return IngestionResult(
            document_id="",
            patient_id=patient_id,
            status="failed",
            summary="",
            document_type="unknown",
            extracted_counts={},
            chunks_indexed=0,
            error=(
                f"Unsupported file type '{path.suffix}'. "
                f"Supported: {', '.join(sorted(SUPPORTED_EXTENSIONS))}"
            ),
        )

    text, warning = read_document_safe(path)

    if warning and not text:
        return IngestionResult(
            document_id="",
            patient_id=patient_id,
            status="failed",
            summary="",
            document_type="unknown",
            extracted_counts={},
            chunks_indexed=0,
            error=warning,
        )

    if warning:
        print(f"[ingest_document] warning for {label!r}: {warning}")

    return ingest_text(text=text, patient_id=patient_id, source_label=label)
