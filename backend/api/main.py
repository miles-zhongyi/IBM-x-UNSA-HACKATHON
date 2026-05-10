from __future__ import annotations

import os
from pathlib import Path

try:
    from dotenv import load_dotenv
except Exception:
    load_dotenv = None

if load_dotenv is not None:
    # Load local development secrets from repo root (ignored by git).
    _REPO_ROOT = Path(__file__).resolve().parents[2]
    load_dotenv(_REPO_ROOT / ".env", override=False)

# Block all HuggingFace network calls — prevents sentence-transformers/chromadb
# from hanging when huggingface.co is unreachable.
os.environ["HF_HUB_OFFLINE"] = "1"
os.environ["TRANSFORMERS_OFFLINE"] = "1"
os.environ["HF_HUB_DISABLE_IMPLICIT_TOKEN"] = "1"
os.environ.setdefault("TOKENIZERS_PARALLELISM", "false")
os.environ.setdefault("EMBEDDING_BACKEND", "hashed")

from contextlib import asynccontextmanager

from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware

from .startup import run_startup
from .routes import compat, doctor, documents, patients


@asynccontextmanager
async def lifespan(app: FastAPI):
    run_startup()
    yield


app = FastAPI(title="IBM x UNSA — Patient Records API", lifespan=lifespan)

app.add_middleware(
    CORSMiddleware,
    allow_origins=[
        "http://localhost:3000",
        "http://127.0.0.1:3000",
        "http://localhost:3001",
        "http://127.0.0.1:3001",
        "http://localhost:3002",
        "http://127.0.0.1:3002",
    ],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

app.include_router(patients.router, prefix="/api/patients", tags=["patients"])
app.include_router(documents.router, prefix="/api/documents", tags=["documents"])
app.include_router(doctor.router, prefix="/api/doctor", tags=["doctor"])
app.include_router(compat.router, prefix="/api", tags=["frontend-compat"])


@app.get("/api/health")
def health() -> dict:
    return {"status": "ok"}
