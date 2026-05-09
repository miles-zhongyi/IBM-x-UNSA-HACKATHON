# IBM-x-UNSA-HACKATHON
# Ingestion Layer

Turns raw clinical note text into structured records + searchable vector chunks.
Everything downstream (RAG, timeline UI, safety) reads through the DAL functions
in `storage.py`.

## Quick start

```bash
pip install -r requirements.txt
python test_pipeline.py
```

## What it does

For each note text submitted via `pipeline.ingest_text()`:

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

## File layout

```
models.py       — Pydantic schemas (the data contract)
storage.py      — SQLite + ChromaDB; exposes the DAL
extraction.py   — LLM and heuristic structured extraction
chunking.py     — Section-aware chunking
embedding.py    — sentence-transformers + hashed fallback
pipeline.py     — Orchestrates the whole flow; one entry point: ingest_text()
test_pipeline.py — End-to-end demo
sample_notes/   — Three real-format sample notes (STEMI, ICU MVA, hospice)
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
```

## Production switch

To use real watsonx instead of the heuristic extractor:

```bash
export WATSONX_API_KEY=...
export WATSONX_PROJECT_ID=...
export WATSONX_URL=https://us-south.ml.cloud.ibm.com   # or your region
export WATSONX_MODEL_ID=ibm/granite-3-8b-instruct      # or current model
```

The pipeline auto-detects the env vars and uses watsonx; if the call fails it
falls back to the heuristic so demos never break.

## Reset / wipe

```python
from storage import reset_all
reset_all()  # nukes SQLite + ChromaDB; useful before re-ingesting fresh data
```