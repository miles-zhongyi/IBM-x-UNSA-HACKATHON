"""
The ingestion pipeline. Two public functions:
  - ingest_text()     — process raw text directly.
  - ingest_document() — extract text from a file (PDF/DOCX/DOC) then process.

Flow:
  raw text  →  LLM extraction  →  SQLite (structured)
                              ↘
                                chunk + embed  →  ChromaDB (vectors)

The functions return an IngestionResult with everything the UI needs to
show "processed N items" and the document_id for follow-up queries.
"""

from __future__ import annotations

import uuid
from pathlib import Path
from typing import Union

from chunking import chunk_document
from document_reader import read_document_safe, SUPPORTED_EXTENSIONS
from embedding import embed_texts
from extraction import extract_structured
from models import IngestionResult
from storage import save_document, store_chunks_in_chroma, init_db


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
        extracted = extract_structured(text)

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
    Extract text from a document file and run it through the ingestion pipeline.

    Supported formats: PDF (.pdf), Word (.docx, .doc).
    Multilingual documents (CJK, Arabic, Cyrillic, etc.) are handled
    transparently by the underlying readers.

    Args:
        path:         Path to the document file.
        patient_id:   Patient this document belongs to.
        source_label: Human-readable label stored with the record.
                      Defaults to the filename if not provided.

    Returns:
        IngestionResult — same shape as ingest_text().
    """
    path = Path(path)
    label = source_label or path.name

    # --- Validate extension before touching the pipeline ---
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

    # --- Extract text from the document ---
    text, warning = read_document_safe(path)

    if warning and not text:
        # Extraction completely failed
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

    # --- Hand off to the text pipeline ---
    result = ingest_text(text=text, patient_id=patient_id, source_label=label)
    return result
