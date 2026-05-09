# Ingestion layer — DAL reference (for Chat / API / Frontend)

**Source of truth:** `pipeline.py`, `storage.py`, `embedding.py`, `models.py`, `chunking.py`  
**Purpose:** One page so downstream code does not guess field names (`document_id` vs `id`, `visit_date` shapes, Chroma metadata keys).

---

## 1. Import paths (pick what matches your repo layout)

### A. Current repo layout (`ingestion_layer/` at repository root)

Run API/tests with **`ingestion_layer` on `PYTHONPATH`**, or `cd ingestion_layer` so local imports resolve the same way as `test_pipeline.py`:

```python
from pipeline import ingest_text
from storage import (
    get_patient_timeline,
    get_diagnoses,
    get_active_medications,
    get_all_labs,
    get_lab_trend,
    search_chunks,
    get_document_by_id,
    reset_all,
)
from embedding import embed_query, embed_texts
```

### B. Target layout from project brief (`backend.ingestion` package)

After packaging/migration, imports should become:

```python
from backend.ingestion.pipeline import ingest_text
from backend.ingestion.storage import (...)
from backend.ingestion.embedding import embed_query, embed_texts
```

**Rule:** Only callinto **`pipeline`**, **`storage`**, and **`embedding`**. Do not open SQLite or Chroma files directly.

---

## 2. `ingest_text` — write path

```python
def ingest_text(
    text: str,
    patient_id: str,
    source_label: str = "pasted",
) -> IngestionResult:
    ...
```

### `IngestionResult` (Pydantic — `models.py`)

| Field | Type | Notes |
|--------|------|--------|
| `document_id` | `str` | New UUID string per ingest; empty string if failed before assign |
| `patient_id` | `str` | Echo of argument |
| `status` | `"processed"` \| `"failed"` | |
| `summary` | `str` | Plain-language summary from extraction |
| `document_type` | `DocumentType` | e.g. `visit_note`, `lab_report`, `unknown`, … |
| `visit_date` | `date \| None` | Parsed visit date when extractor provides it |
| `extracted_counts` | `dict` | e.g. `{"diagnoses": 2, "medications": 3, "lab_values": 5, "instructions": 1}` |
| `chunks_indexed` | `int` | Chroma chunks written |
| `error` | `str \| None` | Set when `status == "failed"` |

**Example (success):**

```json
{
  "document_id": "a1b2c3d4-e5f6-7890-abcd-ef1234567890",
  "patient_id": "marcus-demo",
  "status": "processed",
  "summary": "67-year-old with STEMI; cath showed LAD occlusion.",
  "document_type": "admission_note",
  "visit_date": "2024-06-15",
  "extracted_counts": {
    "diagnoses": 3,
    "medications": 5,
    "lab_values": 8,
    "instructions": 2
  },
  "chunks_indexed": 12,
  "error": null
}
```

**Example (too short):**

```json
{
  "document_id": "",
  "patient_id": "marcus-demo",
  "status": "failed",
  "summary": "",
  "document_type": "unknown",
  "visit_date": null,
  "extracted_counts": {},
  "chunks_indexed": 0,
  "error": "Document too short to process (must be at least 50 characters)."
}
```

---

## 3. SQLite DAL — keys to use in UI / citations

SQLite rows are returned as **`dict`** keys matching **column names** (snake_case).

### `get_patient_timeline(patient_id: str) -> list[dict]`

One row per document, **newest first**.

| Key | Type | Meaning |
|-----|------|---------|
| **`id`** | `str` | **Document id** — same as `document_id` elsewhere |
| `document_type` | `str \| None` | |
| `visit_date` | `str \| None` | ISO date string `YYYY-MM-DD` or SQLite NULL → Python `None` |
| `provider_name` | `str \| None` | |
| `provider_specialty` | `str \| None` | |
| `chief_complaint` | `str \| None` | |
| `summary` | `str \| None` | |
| `source_label` | `str \| None` | e.g. `pasted`, filename |

**Example row:**

```json
{
  "id": "a1b2c3d4-e5f6-7890-abcd-ef1234567890",
  "document_type": "admission_note",
  "visit_date": "2024-06-15",
  "provider_name": "Dr. Smith",
  "provider_specialty": "Cardiology",
  "chief_complaint": "Chest pain",
  "summary": "STEMI with LAD occlusion.",
  "source_label": "pasted"
}
```

**Citation hint:** Use **`timeline_row["id"]`** when you need `document_id` for `get_document_by_id`.

---

### `get_document_by_id(document_id: str) -> dict | None`

`SELECT * FROM documents` — **`None`** if missing.

| Key | Notes |
|-----|--------|
| **`id`** | Document id |
| `patient_id` | |
| `document_type` | |
| `visit_date` | `str \| None` (ISO date) |
| `provider_name`, `provider_specialty`, `provider_facility` | |
| `chief_complaint`, `summary` | |
| **`raw_text`** | Full original note text — use for “expand citation” |
| `source_label` | |
| `created_at` | Timestamp string |

---

### `get_diagnoses(patient_id: str, active_only: bool = False) -> list[dict]`

| Key | Notes |
|-----|--------|
| `name` | |
| `icd_code` | |
| `status` | |
| `visit_date` | `str \| None` |
| **`document_id`** | Links to document |

---

### `get_active_medications(patient_id: str) -> list[dict]`

Only medications from the **single latest `visit_date`** in `medications` for that patient.

| Key | Notes |
|-----|--------|
| `name`, `dose`, `frequency`, `purpose` | |
| `visit_date` | `str \| None` |
| **`document_id`** | |

---

### `get_all_labs(patient_id: str) -> list[dict]`

All labs, **newest first** (by `test_date`, then name).

| Key | Notes |
|-----|--------|
| `name` | Lab name |
| `value` | `float \| None` |
| `value_text` | e.g. `"negative"` when not numeric |
| `unit`, `reference_range`, `flag` | |
| **`test_date`** | `str \| None` — here used as the lab row date |
| **`document_id`** | |

---

### `get_lab_trend(patient_id: str, lab_name: str) -> list[dict]`

Filter: `LOWER(name) LIKE LOWER('%' || lab_name || '%')`. Ordered **oldest → newest** for charting.

Same keys as `get_all_labs` row; use **`test_date`** on the x-axis and **`value` / `value_text`** for y.

---

## 4. Vector search — `search_chunks`

```python
def search_chunks(
    patient_id: str,
    query_embedding: list[float],
    n_results: int = 5,
    document_type: str | None = None,
    after_date: date | None = None,
    before_date: date | None = None,
) -> list[dict]:
    ...
```

**You must embed the user query first:**

```python
from datetime import date
from embedding import embed_query
from storage import search_chunks

q = embed_query("What was my A1C in November?")
hits = search_chunks(
    "elena-demo",
    q,
    n_results=5,
    after_date=date(2024, 1, 1),
)
```

### Each hit (`list[dict]`)

| Key | Type | Meaning |
|-----|------|---------|
| **`id`** | `str` | Chroma chunk id — format **`{document_id}_{chunk_index}`** (see `chunking.py`) |
| **`text`** | `str` | Chunk body |
| **`metadata`** | `dict` | Filterable fields (see below) |
| **`distance`** | `float \| None` | Chroma distance (lower = closer, if present) |

### Chunk **`metadata`** — authoritative keys

Built in `chunking._base_metadata` + section/chunk index:

| Key | Type | Meaning |
|-----|------|---------|
| **`patient_id`** | `str` | |
| **`document_id`** | `str` | Join to SQLite `documents.id` |
| **`document_type`** | `str` | Same vocabulary as `ExtractedDocument.document_type` |
| **`visit_date`** | `str` | **ISO `YYYY-MM-DD`** when known; **key may be omitted** if extraction left date `None` (Chroma stores no `None`) |
| **`provider`** | `str` | Provider **name** only (single string) |
| **`conditions`** | `str` | Comma-separated diagnosis names, or omitted |
| **`section`** | `str` | Normalized header, e.g. `history_of_presenting_illness`, `full_document` |
| **`chunk_index`** | `int` | 0-based index within that document |

**Example hit:**

```json
{
  "id": "a1b2c3d4-e5f6-7890-abcd-ef1234567890_3",
  "text": "Assessment: Type 2 diabetes mellitus with improving glycemic control...",
  "metadata": {
    "patient_id": "elena-demo",
    "document_id": "a1b2c3d4-e5f6-7890-abcd-ef1234567890",
    "document_type": "visit_note",
    "visit_date": "2024-03-10",
    "provider": "Dr. Lee",
    "conditions": "Type 2 diabetes mellitus,Hypertension",
    "section": "assessment",
    "chunk_index": 3
  },
  "distance": 0.42
}
```

**Date filters:** `after_date` / `before_date` are applied **after** the Chroma query, using `metadata["visit_date"]` parsed as ISO date. If `visit_date` is missing on a chunk, date filtering may not exclude it — design retrieval accordingly.

---

## 5. Embeddings

```python
def embed_query(query: str) -> list[float]: ...
def embed_texts(texts: list[str]) -> list[list[float]]: ...
```

Use **`embed_query`** for RAG queries. **`embed_texts`** is used inside ingestion for chunk batches. Dimension is **384** (MiniLM or hashed fallback matching same dim).

---

## 6. Reset (dev/demo only)

```python
def reset_all() -> None:
    """Deletes SQLite DB + Chroma collection/dir, then re-inits empty schema."""
```

---

## 7. Quick mapping cheat sheet

| You need | Use |
|----------|-----|
| Stable document id | SQLite / timeline: **`id`** or **`document_id`** (same value); Chroma metadata: **`document_id`** |
| Visit date for citations | Timeline / documents / labs: **`visit_date`** (string or None); Chroma: **`metadata["visit_date"]`** ISO string, may be absent |
| Full note text | **`get_document_by_id(id)["raw_text"]`** |
| Chunk for LLM context | **`search_chunks` → `text` + `metadata`** |
| Trend series | **`get_lab_trend`** → rows with **`test_date`**, **`value`**, **`value_text`** |

---

*Generated from ingestion layer source; if behavior changes, update this file in the same PR.*
