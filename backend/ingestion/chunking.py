"""
Chunking strategy for clinical notes.

Two-tier approach:
  1. If standard sections are detected (HPI, Assessment, Plan, etc.),
     chunk by section.
  2. Otherwise, fall back to a sliding window with overlap.

Each chunk carries metadata that lets RAG filter by date, document type,
section, and conditions mentioned.
"""

from __future__ import annotations

import re
from typing import Optional

from .models import ExtractedDocument


# Common SOAP/clinical note section headers. Order matters for splitting.
SECTION_HEADERS = [
    "Patient information",
    "Reason for admission",
    "Referral source",
    "History of presenting illness",
    "Past medical history",
    "Medical history",
    "Current medications",
    "Social and family history",
    "Social history",
    "Family history",
    "Spiritual needs",
    "Family situation",
    "Functional assessment",
    "Physical examination",
    "Vital Signs",
    "Investigations",
    "Ventilator settings",
    "Current Blood Gas Values",
    "Prognosis",
    "Assessment",
    "Plan",
    "HPI",
    "ROS",
    "Subjective",
    "Objective",
]


def chunk_document(
    text: str,
    document_id: str,
    patient_id: str,
    extracted: ExtractedDocument,
    target_chunk_chars: int = 1200,
    overlap_chars: int = 200,
) -> list[dict]:
    """
    Split a document into chunks ready for embedding.

    Returns list of dicts: {id, text, metadata}
    where metadata includes patient_id, document_id, document_type, visit_date,
    provider, section, chunk_index, conditions.
    """
    sections = _split_into_sections(text)

    base_metadata = _base_metadata(document_id, patient_id, extracted)

    chunks: list[dict] = []
    chunk_index = 0

    if sections:
        for section_name, section_text in sections:
            # If a section is huge (e.g., long HPI), sub-chunk it
            sub_chunks = _split_long_text(
                section_text,
                target_chars=target_chunk_chars,
                overlap_chars=overlap_chars,
            )
            for sub in sub_chunks:
                chunks.append(
                    _make_chunk(
                        text=sub,
                        section=section_name,
                        chunk_index=chunk_index,
                        document_id=document_id,
                        base_metadata=base_metadata,
                    )
                )
                chunk_index += 1
    else:
        # Fallback: sliding window over the whole document
        for sub in _split_long_text(text, target_chunk_chars, overlap_chars):
            chunks.append(
                _make_chunk(
                    text=sub,
                    section="full_document",
                    chunk_index=chunk_index,
                    document_id=document_id,
                    base_metadata=base_metadata,
                )
            )
            chunk_index += 1

    return chunks


def _base_metadata(
    document_id: str, patient_id: str, extracted: ExtractedDocument
) -> dict:
    conditions = ",".join(d.name for d in extracted.diagnoses) if extracted.diagnoses else None
    return {
        "patient_id": patient_id,
        "document_id": document_id,
        "document_type": extracted.document_type,
        "visit_date": extracted.visit_date.isoformat() if extracted.visit_date else None,
        "provider": extracted.provider.name if extracted.provider else None,
        "conditions": conditions,
    }


def _make_chunk(
    text: str,
    section: str,
    chunk_index: int,
    document_id: str,
    base_metadata: dict,
) -> dict:
    metadata = {**base_metadata, "section": _normalize_section(section), "chunk_index": chunk_index}
    return {
        "id": f"{document_id}_{chunk_index}",
        "text": text.strip(),
        "metadata": metadata,
    }


def _normalize_section(name: str) -> str:
    return re.sub(r"[^a-z0-9]+", "_", name.strip().lower()).strip("_")


def _split_into_sections(text: str) -> list[tuple[str, str]]:
    """
    Find section headers and split the document accordingly.

    Returns list of (section_name, section_text). Empty list if no clear
    section structure is detected.
    """
    # Build a regex that matches any known header at line start, optionally
    # followed by ':' or '-' (handle both 'Plan' and 'Plan -' and 'Plan:').
    header_pattern = (
        r"(?:^|\n)("
        + "|".join(re.escape(h) for h in SECTION_HEADERS)
        + r")\s*[-:]?\s*(?=\n|\s)"
    )

    matches = list(re.finditer(header_pattern, text, flags=re.IGNORECASE))
    if len(matches) < 2:
        return []

    sections: list[tuple[str, str]] = []
    for i, m in enumerate(matches):
        section_name = m.group(1)
        body_start = m.end()
        body_end = matches[i + 1].start() if i + 1 < len(matches) else len(text)
        body = text[body_start:body_end].strip()
        if body:
            # Include the header in the chunk text — it helps the embedder
            # and gives the LLM context when this chunk gets retrieved.
            chunk_text = f"{section_name}: {body}"
            sections.append((section_name, chunk_text))

    return sections


def _split_long_text(
    text: str,
    target_chars: int = 1200,
    overlap_chars: int = 200,
) -> list[str]:
    """
    Sliding window over long text, splitting on paragraph/sentence boundaries
    when possible.
    """
    text = text.strip()
    if len(text) <= target_chars:
        return [text] if text else []

    chunks: list[str] = []
    start = 0
    while start < len(text):
        end = min(start + target_chars, len(text))

        # If we're not at the end of the doc, prefer breaking on a paragraph
        # then sentence boundary near `end`.
        if end < len(text):
            window = text[start:end]
            for sep in ["\n\n", "\n", ". ", "; "]:
                idx = window.rfind(sep)
                if idx > target_chars * 0.5:
                    end = start + idx + len(sep)
                    break

        chunk = text[start:end].strip()
        if chunk:
            chunks.append(chunk)

        if end >= len(text):
            break
        start = max(end - overlap_chars, start + 1)

    return chunks
