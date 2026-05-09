# Backend (FastAPI + ingestion + RAG chat)

## Run locally

From the **repository root** (so `import backend` resolves):

```bash
pip install -r backend/requirements.txt
uvicorn backend.api.main:app --reload --host 0.0.0.0 --port 8000
```

- API docs: `http://127.0.0.1:8000/docs`
- Health: `GET /api/health`
- CORS allows `http://localhost:3000`

## Environment

Copy `backend/.env.example` to `.env` and set watsonx variables if you want LLM chat generation (otherwise chat uses a deterministic fallback from retrieved context).

## Demo patients (auto-seeded)

If `marcus-demo` has no visits on startup, the API ingests:

| `patient_id`   | Source |
|----------------|--------|
| `marcus-demo`  | `backend/ingestion/sample_notes/note1_stemi.txt` |
| `elena-demo`   | `demo_data/elena_visit_*.txt` |
| `dorothy-demo` | `backend/ingestion/sample_notes/note3_hospice.txt` |

Force a full reset + re-seed next boot:

```bash
set DEMO_SEED_FRESH=1
uvicorn backend.api.main:app --reload
```

Or run `python scripts/seed_demo_data.py`.

## Layout

- `ingestion/` — SQLite + Chroma ingestion (DAL); see `ingestion/DAL_REFERENCE.md`
- `chat/` — intent, safety, retrieval, generation, translation, watsonx client
- `api/` — FastAPI routes + startup seeding
- `reference_corpus/` — patient-education snippets (Chroma collection `patient_education_reference`)

## Tests

```bash
pytest -q
```
