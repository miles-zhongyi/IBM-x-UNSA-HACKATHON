"""
audit_ingestion.py — verify document ingestion end-to-end.

Run:
    python audit_ingestion.py

What it does:
  1. Ingests every file in sample_pdf_notes/ using ingest_document().
  2. For each file prints a structured audit report:
       - Extraction status (processed / failed)
       - Document type detected
       - Counts: diagnoses, medications, lab values, vitals, instructions
       - Whether the raw text was stored in SQLite
       - Whether chunks were indexed in ChromaDB (semantic search test)
       - A one-liner content preview
  3. Prints a summary table at the end so you can spot which files failed
     or produced empty extractions.

No API keys required — uses heuristic extraction fallback.
"""

from __future__ import annotations

import json
from pathlib import Path

from document_reader import read_document_safe, SUPPORTED_EXTENSIONS
from embedding import embed_query
from pipeline import ingest_document
from storage import (
    get_document_by_id,
    get_patient_timeline,
    reset_all,
    search_chunks,
)


# ── helpers ─────────────────────────────────────────────────────────────────

def banner(title: str):
    print("\n" + "=" * 72)
    print(f"  {title}")
    print("=" * 72)


PASS = "✓"
FAIL = "✗"
WARN = "⚠"


def _check(condition: bool, label: str, detail: str = "") -> str:
    icon = PASS if condition else FAIL
    line = f"  {icon}  {label}"
    if detail:
        line += f"  ({detail})"
    return line


# ── per-file audit ───────────────────────────────────────────────────────────

def audit_file(doc_path: Path, patient_id: str) -> dict:
    """
    Ingest one file and return an audit record.
    """
    print(f"\n{'─'*72}")
    print(f"  FILE : {doc_path.name}")
    print(f"  PATIENT: {patient_id}")
    print(f"{'─'*72}")

    record = {
        "file": doc_path.name,
        "patient_id": patient_id,
        "text_extracted": False,
        "status": "not_run",
        "document_type": "",
        "diagnoses": 0,
        "medications": 0,
        "lab_values": 0,
        "vitals": False,
        "instructions": 0,
        "chunks_indexed": 0,
        "raw_text_stored": False,
        "vector_searchable": False,
        "error": "",
    }

    # ── Step 1: Text extraction check (before pipeline) ──────────────────
    text, warn = read_document_safe(doc_path)
    record["text_extracted"] = bool(text and len(text) > 50)
    print(_check(record["text_extracted"], "Text extraction",
                 f"{len(text)} chars" if text else warn or "empty"))
    if warn:
        print(f"       {WARN}  Warning: {warn}")

    # ── Step 2: Ingest through pipeline ──────────────────────────────────
    result = ingest_document(doc_path, patient_id=patient_id)
    r = result.model_dump()

    record["status"] = r["status"]
    record["document_type"] = r["document_type"]
    record["diagnoses"] = r["extracted_counts"].get("diagnoses", 0)
    record["medications"] = r["extracted_counts"].get("medications", 0)
    record["lab_values"] = r["extracted_counts"].get("lab_values", 0)
    record["instructions"] = r["extracted_counts"].get("instructions", 0)
    record["chunks_indexed"] = r["chunks_indexed"]
    record["error"] = r.get("error") or ""

    ok = r["status"] == "processed"
    print(_check(ok, f"Pipeline ingestion — {r['status']}",
                 r.get("error") or r["document_type"]))

    if ok:
        # ── Step 3: Confirm SQLite storage ────────────────────────────────
        doc_row = get_document_by_id(r["document_id"])
        raw_text_len = len(doc_row["raw_text"]) if doc_row and doc_row.get("raw_text") else 0
        raw_stored = raw_text_len > 0
        record["raw_text_stored"] = raw_stored
        print(_check(raw_stored, "Raw text in SQLite",
                     f"{raw_text_len} chars" if raw_stored else "MISSING"))

        # ── Step 4: Extraction summary ────────────────────────────────────
        print(f"       Diagnoses    : {record['diagnoses']}")
        print(f"       Medications  : {record['medications']}")
        print(f"       Lab values   : {record['lab_values']}")
        print(f"       Instructions : {record['instructions']}")
        print(f"       Chunks       : {record['chunks_indexed']}")

        # ── Step 5: ChromaDB semantic search test ─────────────────────────
        probe_queries = [
            "patient diagnosis condition",
            "medication treatment",
            "physical examination",
        ]
        found = False
        for q in probe_queries:
            q_emb = embed_query(q)
            hits = search_chunks(patient_id=patient_id,
                                 query_embedding=q_emb,
                                 n_results=1)
            if hits:
                found = True
                break
        record["vector_searchable"] = found
        print(_check(found, "ChromaDB vector search",
                     f"returned results for query: '{q}'"))

        # ── Step 6: Content preview ───────────────────────────────────────
        summary = r.get("summary") or ""
        if summary:
            print(f"\n  Preview: {summary[:200]}")

    return record


# ── summary table ────────────────────────────────────────────────────────────

def print_summary(records: list[dict]):
    banner("AUDIT SUMMARY")

    header = (
        f"{'FILE':<52} {'STATUS':<10} {'TYPE':<22} "
        f"{'DX':>3} {'MED':>4} {'LAB':>4} {'CHK':>4} {'VEC':>4}"
    )
    print(header)
    print("─" * len(header))

    ok_count = 0
    for r in records:
        status_icon = PASS if r["status"] == "processed" else FAIL
        vec_icon = PASS if r["vector_searchable"] else (FAIL if r["status"] == "processed" else "─")
        row = (
            f"{r['file'][:51]:<52} "
            f"{status_icon} {r['status']:<8} "
            f"{r['document_type']:<22} "
            f"{r['diagnoses']:>3} "
            f"{r['medications']:>4} "
            f"{r['lab_values']:>4} "
            f"{r['chunks_indexed']:>4} "
            f"{vec_icon:>4}"
        )
        print(row)
        if r["status"] == "processed":
            ok_count += 1
        if r["error"]:
            print(f"       ERROR: {r['error']}")

    print("─" * len(header))
    print(f"\n  {ok_count}/{len(records)} files ingested successfully.")

    skipped = [r for r in records if not r["text_extracted"] and r["status"] != "processed"]
    if skipped:
        print(f"\n  {WARN}  Files with empty/failed text extraction:")
        for r in skipped:
            print(f"      - {r['file']}: {r['error']}")

    empty_extraction = [
        r for r in records
        if r["status"] == "processed"
        and r["diagnoses"] == 0
        and r["medications"] == 0
        and r["lab_values"] == 0
    ]
    if empty_extraction:
        print(f"\n  {WARN}  Files processed but zero structured data extracted")
        print( "       (content still in ChromaDB via raw text — vector search works):")
        for r in empty_extraction:
            print(f"      - {r['file']}  (type: {r['document_type']})")
        print( "       Tip: if watsonx credentials are set, LLM extraction will pick up more.")


# ── main ────────────────────────────────────────────────────────────────────

def main():
    # Wipe previous test state for a clean run
    reset_all()

    pdf_dir = Path(__file__).parent / "sample_pdf_notes"

    # Discover all supported files automatically
    files = sorted(
        f for f in pdf_dir.iterdir()
        if f.is_file() and f.suffix.lower() in SUPPORTED_EXTENSIONS
    )

    if not files:
        print(f"No supported files found in {pdf_dir}")
        print(f"Supported extensions: {', '.join(sorted(SUPPORTED_EXTENSIONS))}")
        return

    banner(f"INGESTION AUDIT — {len(files)} files in sample_pdf_notes/")
    print("  Formats: PDF (PyMuPDF), DOCX (python-docx), DOC (antiword/fallback)")
    print("  Extraction backend: watsonx (if env vars set) else heuristic\n")

    records: list[dict] = []
    for i, doc_path in enumerate(files):
        patient_id = f"audit_patient_{i+1:03d}"
        record = audit_file(doc_path, patient_id)
        records.append(record)

    print_summary(records)

    banner("DONE")
    print("  To run the full pipeline demo (text + documents):")
    print("    python test_pipeline.py")
    print("\n  To install missing dependencies:")
    print("    pip install pymupdf python-docx")
    print("  For .doc support (antiword):")
    print("    Linux: sudo apt install antiword")
    print("    macOS: brew install antiword")


if __name__ == "__main__":
    main()
