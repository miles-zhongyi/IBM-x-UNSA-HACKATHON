from __future__ import annotations

from contextlib import asynccontextmanager

from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware

from .startup import run_startup
from .routes import doctor, documents, patients


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
    ],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

app.include_router(patients.router, prefix="/api/patients", tags=["patients"])
app.include_router(documents.router, prefix="/api/documents", tags=["documents"])
app.include_router(doctor.router, prefix="/api/doctor", tags=["doctor"])


@app.get("/api/health")
def health() -> dict:
    return {"status": "ok"}
