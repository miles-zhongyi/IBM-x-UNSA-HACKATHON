"""
Storage layer: SQLite for structured data, ChromaDB for vector search.

This module owns all DB connections and exposes a clean DAL (data access layer)
that downstream code (RAG, UI) reads through. Don't poke at SQLite directly
from outside this module.
"""

import sqlite3
from datetime import date
from pathlib import Path
from typing import Optional

import chromadb
from chromadb.config import Settings

from .models import ExtractedDocument


# ---------------------------------------------------------------------------
# Paths
# ---------------------------------------------------------------------------
DATA_DIR = Path(__file__).parent / "data"
DATA_DIR.mkdir(exist_ok=True)
SQLITE_PATH = DATA_DIR / "patient_records.db"
CHROMA_PATH = str(DATA_DIR / "chroma")


# ---------------------------------------------------------------------------
# Schema
# ---------------------------------------------------------------------------
SCHEMA = """
CREATE TABLE IF NOT EXISTS documents (
    id TEXT PRIMARY KEY,
    patient_id TEXT NOT NULL,
    document_type TEXT,
    visit_date DATE,
    provider_name TEXT,
    provider_specialty TEXT,
    provider_facility TEXT,
    chief_complaint TEXT,
    summary TEXT,
    raw_text TEXT,
    source_label TEXT,
    created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
);

CREATE TABLE IF NOT EXISTS diagnoses (
    id INTEGER PRIMARY KEY AUTOINCREMENT,
    document_id TEXT REFERENCES documents(id) ON DELETE CASCADE,
    patient_id TEXT NOT NULL,
    name TEXT NOT NULL,
    icd_code TEXT,
    status TEXT,
    visit_date DATE
);

CREATE TABLE IF NOT EXISTS medications (
    id INTEGER PRIMARY KEY AUTOINCREMENT,
    document_id TEXT REFERENCES documents(id) ON DELETE CASCADE,
    patient_id TEXT NOT NULL,
    name TEXT NOT NULL,
    dose TEXT,
    frequency TEXT,
    purpose TEXT,
    visit_date DATE
);

CREATE TABLE IF NOT EXISTS lab_values (
    id INTEGER PRIMARY KEY AUTOINCREMENT,
    document_id TEXT REFERENCES documents(id) ON DELETE CASCADE,
    patient_id TEXT NOT NULL,
    name TEXT NOT NULL,
    value REAL,
    value_text TEXT,
    unit TEXT,
    reference_range TEXT,
    flag TEXT,
    test_date DATE
);

CREATE TABLE IF NOT EXISTS vitals (
    id INTEGER PRIMARY KEY AUTOINCREMENT,
    document_id TEXT REFERENCES documents(id) ON DELETE CASCADE,
    patient_id TEXT NOT NULL,
    blood_pressure TEXT,
    heart_rate TEXT,
    respiratory_rate TEXT,
    temperature TEXT,
    spo2 TEXT,
    visit_date DATE
);

CREATE TABLE IF NOT EXISTS instructions (
    id INTEGER PRIMARY KEY AUTOINCREMENT,
    document_id TEXT REFERENCES documents(id) ON DELETE CASCADE,
    patient_id TEXT NOT NULL,
    text TEXT NOT NULL,
    visit_date DATE
);

CREATE INDEX IF NOT EXISTS idx_labs_trend ON lab_values(patient_id, name, test_date);
CREATE INDEX IF NOT EXISTS idx_docs_patient ON documents(patient_id, visit_date);
CREATE INDEX IF NOT EXISTS idx_meds_patient ON medications(patient_id, visit_date);
CREATE INDEX IF NOT EXISTS idx_dx_patient ON diagnoses(patient_id, visit_date);
"""


# ---------------------------------------------------------------------------
# SQLite connection
# ---------------------------------------------------------------------------
def get_conn():
    conn = sqlite3.connect(SQLITE_PATH, detect_types=sqlite3.PARSE_DECLTYPES)
    conn.row_factory = sqlite3.Row
    conn.execute("PRAGMA foreign_keys = ON")
    return conn


def init_db():
    """Create schema. Idempotent."""
    conn = get_conn()
    try:
        conn.executescript(SCHEMA)
        conn.commit()
    finally:
        conn.close()


# ---------------------------------------------------------------------------
# ChromaDB
# ---------------------------------------------------------------------------
_chroma_client = None
_chroma_collection = None


def _noop_embedding_function():
    """Prevent ChromaDB from loading sentence-transformers as default embedder."""
    from chromadb.api.types import EmbeddingFunction, Documents, Embeddings

    class NoopEF(EmbeddingFunction):
        def __call__(self, input: Documents) -> Embeddings:
            raise RuntimeError("Use query_embeddings / embeddings params directly")

    return NoopEF()


def get_chroma_collection():
    """Lazy-init ChromaDB collection."""
    global _chroma_client, _chroma_collection
    if _chroma_collection is None:
        _chroma_client = chromadb.PersistentClient(
            path=CHROMA_PATH,
            settings=Settings(anonymized_telemetry=False),
        )
        _chroma_collection = _chroma_client.get_or_create_collection(
            name="patient_documents",
            metadata={"hnsw:space": "cosine"},
            embedding_function=_noop_embedding_function(),
        )
    return _chroma_collection


# ---------------------------------------------------------------------------
# Write operations (used by ingestion pipeline)
# ---------------------------------------------------------------------------
def save_document(
    document_id: str,
    patient_id: str,
    extracted: ExtractedDocument,
    raw_text: str,
    source_label: str,
):
    conn = get_conn()
    try:
        provider = extracted.provider
        conn.execute(
            """
            INSERT INTO documents
                (id, patient_id, document_type, visit_date, provider_name,
                 provider_specialty, provider_facility, chief_complaint,
                 summary, raw_text, source_label)
            VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?)
            """,
            (
                document_id,
                patient_id,
                extracted.document_type,
                extracted.visit_date,
                provider.name if provider else None,
                provider.specialty if provider else None,
                provider.facility if provider else None,
                extracted.chief_complaint,
                extracted.summary,
                raw_text,
                source_label,
            ),
        )

        visit_date = extracted.visit_date

        for dx in extracted.diagnoses:
            conn.execute(
                """
                INSERT INTO diagnoses
                    (document_id, patient_id, name, icd_code, status, visit_date)
                VALUES (?, ?, ?, ?, ?, ?)
                """,
                (document_id, patient_id, dx.name, dx.icd_code, dx.status, visit_date),
            )

        for med in extracted.medications:
            conn.execute(
                """
                INSERT INTO medications
                    (document_id, patient_id, name, dose, frequency, purpose, visit_date)
                VALUES (?, ?, ?, ?, ?, ?, ?)
                """,
                (
                    document_id,
                    patient_id,
                    med.name,
                    med.dose,
                    med.frequency,
                    med.purpose,
                    visit_date,
                ),
            )

        for lab in extracted.lab_values:
            conn.execute(
                """
                INSERT INTO lab_values
                    (document_id, patient_id, name, value, value_text, unit,
                     reference_range, flag, test_date)
                VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?)
                """,
                (
                    document_id,
                    patient_id,
                    lab.name,
                    lab.value,
                    lab.value_text,
                    lab.unit,
                    lab.reference_range,
                    lab.flag,
                    visit_date,
                ),
            )

        if extracted.vitals:
            v = extracted.vitals
            conn.execute(
                """
                INSERT INTO vitals
                    (document_id, patient_id, blood_pressure, heart_rate,
                     respiratory_rate, temperature, spo2, visit_date)
                VALUES (?, ?, ?, ?, ?, ?, ?, ?)
                """,
                (
                    document_id,
                    patient_id,
                    v.blood_pressure,
                    v.heart_rate,
                    v.respiratory_rate,
                    v.temperature,
                    v.spo2,
                    visit_date,
                ),
            )

        for instruction in extracted.instructions_to_patient:
            conn.execute(
                """
                INSERT INTO instructions (document_id, patient_id, text, visit_date)
                VALUES (?, ?, ?, ?)
                """,
                (document_id, patient_id, instruction, visit_date),
            )

        conn.commit()
    finally:
        conn.close()


def store_chunks_in_chroma(
    chunks: list[dict],
    embeddings: list[list[float]],
):
    """Store pre-embedded chunks in ChromaDB."""
    if not chunks:
        return

    collection = get_chroma_collection()

    # Chroma requires str|int|float|bool in metadata, no None
    cleaned_metadatas = []
    for c in chunks:
        meta = {k: v for k, v in c["metadata"].items() if v is not None}
        cleaned_metadatas.append(meta)

    collection.add(
        ids=[c["id"] for c in chunks],
        embeddings=embeddings,
        documents=[c["text"] for c in chunks],
        metadatas=cleaned_metadatas,
    )


# ---------------------------------------------------------------------------
# DAL — Data Access Layer (read-side, what RAG and UI use)
# ---------------------------------------------------------------------------
def get_patient_timeline(patient_id: str) -> list[dict]:
    """All documents for a patient, newest first."""
    conn = get_conn()
    try:
        rows = conn.execute(
            """
            SELECT id, document_type, visit_date, provider_name,
                   provider_specialty, chief_complaint, summary, source_label
            FROM documents
            WHERE patient_id = ?
            ORDER BY visit_date DESC NULLS LAST, created_at DESC
            """,
            (patient_id,),
        ).fetchall()
        return [dict(r) for r in rows]
    finally:
        conn.close()


def get_lab_trend(patient_id: str, lab_name: str) -> list[dict]:
    """All values of a specific lab over time. Used by trend questions."""
    conn = get_conn()
    try:
        rows = conn.execute(
            """
            SELECT name, value, value_text, unit, reference_range, flag,
                   test_date, document_id
            FROM lab_values
            WHERE patient_id = ?
              AND LOWER(name) LIKE LOWER(?)
            ORDER BY test_date ASC
            """,
            (patient_id, f"%{lab_name}%"),
        ).fetchall()
        return [dict(r) for r in rows]
    finally:
        conn.close()


def get_all_labs(patient_id: str) -> list[dict]:
    """Every lab value for a patient. Used for the labs panel."""
    conn = get_conn()
    try:
        rows = conn.execute(
            """
            SELECT name, value, value_text, unit, reference_range, flag,
                   test_date, document_id
            FROM lab_values
            WHERE patient_id = ?
            ORDER BY test_date DESC, name ASC
            """,
            (patient_id,),
        ).fetchall()
        return [dict(r) for r in rows]
    finally:
        conn.close()


def get_active_medications(patient_id: str) -> list[dict]:
    """Medications from the most recent visit."""
    conn = get_conn()
    try:
        latest = conn.execute(
            """
            SELECT MAX(visit_date) as d
            FROM medications
            WHERE patient_id = ?
            """,
            (patient_id,),
        ).fetchone()
        if not latest or not latest["d"]:
            return []
        rows = conn.execute(
            """
            SELECT name, dose, frequency, purpose, visit_date, document_id
            FROM medications
            WHERE patient_id = ? AND visit_date = ?
            """,
            (patient_id, latest["d"]),
        ).fetchall()
        return [dict(r) for r in rows]
    finally:
        conn.close()


def get_diagnoses(patient_id: str, active_only: bool = False) -> list[dict]:
    conn = get_conn()
    try:
        if active_only:
            rows = conn.execute(
                """
                SELECT name, icd_code, status, visit_date, document_id
                FROM diagnoses
                WHERE patient_id = ?
                  AND (status IS NULL OR status IN ('active', 'chronic', 'suspected'))
                ORDER BY visit_date DESC
                """,
                (patient_id,),
            ).fetchall()
        else:
            rows = conn.execute(
                """
                SELECT name, icd_code, status, visit_date, document_id
                FROM diagnoses
                WHERE patient_id = ?
                ORDER BY visit_date DESC
                """,
                (patient_id,),
            ).fetchall()
        return [dict(r) for r in rows]
    finally:
        conn.close()


def get_document_by_id(document_id: str) -> Optional[dict]:
    """Full document for citation expansion."""
    conn = get_conn()
    try:
        row = conn.execute(
            "SELECT * FROM documents WHERE id = ?",
            (document_id,),
        ).fetchone()
        return dict(row) if row else None
    finally:
        conn.close()


def search_chunks(
    patient_id: str,
    query_embedding: list[float],
    n_results: int = 5,
    document_type: Optional[str] = None,
    after_date: Optional[date] = None,
    before_date: Optional[date] = None,
) -> list[dict]:
    """
    Semantic search over a patient's chunks. Used by the RAG retriever.

    Returns chunks sorted by relevance, each with text + metadata + distance.
    """
    collection = get_chroma_collection()

    where_filter: dict = {"patient_id": patient_id}
    if document_type:
        where_filter["document_type"] = document_type

    # ChromaDB supports `$gte`/`$lte` only inside `$and`/`$or`. To keep this
    # simple, we filter on equality in Chroma and post-filter dates in Python.
    results = collection.query(
        query_embeddings=[query_embedding],
        n_results=max(n_results * 3, n_results),  # over-fetch for date filtering
        where=where_filter,
    )

    out = []
    if not results["ids"] or not results["ids"][0]:
        return out

    for i in range(len(results["ids"][0])):
        meta = results["metadatas"][0][i]
        chunk_date_str = meta.get("visit_date")
        if chunk_date_str:
            try:
                chunk_date = date.fromisoformat(chunk_date_str)
            except (ValueError, TypeError):
                chunk_date = None
        else:
            chunk_date = None

        if after_date and chunk_date and chunk_date < after_date:
            continue
        if before_date and chunk_date and chunk_date > before_date:
            continue

        out.append(
            {
                "id": results["ids"][0][i],
                "text": results["documents"][0][i],
                "metadata": meta,
                "distance": results["distances"][0][i] if results.get("distances") else None,
            }
        )
        if len(out) >= n_results:
            break

    return out


def reset_all():
    """Wipe everything. Useful for development."""
    global _chroma_client, _chroma_collection

    if SQLITE_PATH.exists():
        SQLITE_PATH.unlink()

    if _chroma_client is not None:
        try:
            _chroma_client.delete_collection("patient_documents")
        except Exception:
            pass
        _chroma_client = None
        _chroma_collection = None

    # also remove chroma directory to be safe
    import shutil
    chroma_dir = Path(CHROMA_PATH)
    if chroma_dir.exists():
        shutil.rmtree(chroma_dir)

    init_db()
