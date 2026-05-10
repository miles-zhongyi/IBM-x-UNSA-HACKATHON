# Project brief — HealthChat / IBM × UNSA (hackathon)

## Goal

Help patients understand their own health records through a **grounded chat** and **timeline UI**, with **safety gates** and **citations** back to visit notes. Clinician view supports demo intake and escalations.

## Architecture (high level)

1. **Ingestion** (`backend/ingestion`) — text → structured SQLite + Chroma chunks (DAL in `storage.py`).
2. **Chat / RAG** (`backend/chat`) — intent routing, safety preflight, retrieval, generation (watsonx optional), translation.
3. **API** (`backend/api`) — FastAPI REST for the Next.js client.
4. **Frontend** (`frontend`) — Next.js 14 App Router, mobile-first, accessibility options, voice (Web Speech API).

## Demo personas

| `patient_id`   | Story |
|----------------|--------|
| `marcus-demo`  | Post‑MI / STEMI sample note |
| `elena-demo`   | Type 2 diabetes — multi‑visit synthetic notes (`demo_data/`) |
| `dorothy-demo` | Hospice sample note |

## Non‑goals (demo)

- No real authentication.
- Not a medical device; not for clinical decisions.

## Key env vars

- **watsonx** (optional): `WATSONX_API_KEY`, `WATSONX_PROJECT_ID`, `WATSONX_URL`, `WATSONX_MODEL_ID`
- **Embeddings**: `EMBEDDING_BACKEND=hashed` for fast CI / offline
- **Reseed**: `DEMO_SEED_FRESH=1` on API boot (see `backend/README.md`)

## Run commands (cheat sheet)

```bash
# API
pip install -r backend/requirements.txt
uvicorn backend.api.main:app --reload --port 8000

# Web
cd frontend && npm install && npm run dev
```

Tests: `pytest -q` from repo root.
