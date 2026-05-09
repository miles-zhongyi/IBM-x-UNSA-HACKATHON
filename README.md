# IBM-x-UNSA-HACKATHON
# Ingestion Layer

Turns raw clinical note text **and document files (PDF, DOCX, DOC)** into
structured records + searchable vector chunks. Everything downstream (RAG,
timeline UI, safety) reads through the DAL functions in `storage.py`.

## Quick start

```bash
cd ingestion_layer

# 1. Create a virtual environment (recommended)
python -m venv .venv
source .venv/bin/activate        # Linux/macOS
# .venv\Scripts\activate         # Windows

# 2. Install all dependencies
pip install -r requirements.txt

# 3. (Optional) Copy and fill in credentials
cp .env.example .env             # edit .env with your watsonx keys

# 4. Run the full demo (text notes + document files)
python test_pipeline.py

# 5. Audit document ingestion specifically
python audit_ingestion.py
```

> **No API keys needed** — the pipeline auto-falls back to heuristic
> extraction and hashed-ngram embeddings. Set watsonx credentials for
> production-quality extraction.

## What it does

### Text input — `pipeline.ingest_text(text, patient_id)`

1. **Extracts structured data** — visit date, provider, diagnoses, medications,
   lab values, vitals, instructions. Two backends:
   - `watsonx` (production) — set `WATSONX_API_KEY` and `WATSONX_PROJECT_ID`
   - `heuristic` (default fallback) — regex/pattern based, deterministic, no API needed
2. **Persists to SQLite** — one row per visit + child rows for each diagnosis/med/lab
3. **Chunks the document** — section-aware (HPI, Assessment, Plan, etc.) with
   sliding-window fallback for long sections
4. **Embeds chunks** — `sentence-transformers/all-MiniLM-L6-v2` if available;
   deterministic hashed n-gram fallback if not (set `EMBEDDING_BACKEND=hashed` to force)
5. **Stores in ChromaDB** with metadata so RAG can filter by patient, date,
   document type, and section

### Document input — `pipeline.ingest_document(path, patient_id)`

Accepts PDF, DOCX, and DOC files. Extracts text automatically, then feeds it
through the same pipeline above. Multilingual content (CJK, Arabic, Cyrillic,
Devanagari, Latin, etc.) is handled transparently.

| Format | Library      | Notes                                     |
|--------|--------------|--------------------------------------------|
| `.pdf` | PyMuPDF      | Unicode-native, handles multilingual PDFs   |
| `.docx`| python-docx  | Reads paragraphs + table cells (UTF-8 XML)  |
| `.doc` | antiword     | Falls back to python-docx → binary strip     |

## File layout

```
models.py            — Pydantic schemas (the data contract)
storage.py           — SQLite + ChromaDB; exposes the DAL
extraction.py        — LLM and heuristic structured extraction
chunking.py          — Section-aware chunking
embedding.py         — sentence-transformers + hashed fallback
document_reader.py   — Text extraction from PDF/DOCX/DOC files
pipeline.py          — Orchestrator; two entry points: ingest_text(), ingest_document()
test_pipeline.py     — End-to-end demo (text notes + document files)
audit_ingestion.py   — Ingestion audit tool (checks every file in sample_pdf_notes/)
.env.example         — Template for environment variables
sample_notes/        — Three text-format sample notes (STEMI, ICU MVA, hospice)
sample_pdf_notes/    — Multi-format sample documents (PDFs + DOC)
```

## DAL — what RAG and the UI call

All read access goes through `storage.py`. **Don't touch SQLite or ChromaDB directly.**

```python
from storage import (
    # Timeline UI
    get_patient_timeline,        # all visits for a patient, newest first
    get_diagnoses,               # all diagnoses (active_only=True for current ones)
    get_active_medications,      # meds from the most recent visit
    get_all_labs,                # every lab value for the patient

    # RAG retrieval
    get_lab_trend,               # all values of one lab over time (for trend questions)
    search_chunks,               # semantic search; pass query_embedding from embedding.embed_query()

    # Citation expansion
    get_document_by_id,          # full document for "where did this come from?" clicks
)

from pipeline import ingest_text, ingest_document  # ingestion entry points
```

## Environment variables

| Variable            | Required | Default                                | Purpose                    |
|---------------------|----------|----------------------------------------|----------------------------|
| `WATSONX_API_KEY`   | No       | —                                      | watsonx extraction backend |
| `WATSONX_PROJECT_ID`| No       | —                                      | watsonx project            |
| `WATSONX_URL`       | No       | `https://us-south.ml.cloud.ibm.com`   | watsonx region endpoint    |
| `WATSONX_MODEL_ID`  | No       | `ibm/granite-3-8b-instruct`           | watsonx model              |
| `EMBEDDING_BACKEND` | No       | auto-detect                            | `hashed` to force fallback |

## System dependencies (optional)

For legacy `.doc` files, install `antiword`:
```bash
# Linux
sudo apt install antiword
# macOS
brew install antiword
```
Without it, `.doc` falls back to python-docx or a binary-strip heuristic.

## Reset / wipe

```python
from storage import reset_all
reset_all()  # nukes SQLite + ChromaDB; useful before re-ingesting fresh data
```
