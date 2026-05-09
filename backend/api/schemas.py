from __future__ import annotations

from typing import Any, Literal, Optional

from pydantic import BaseModel, Field


class DocumentIngestBody(BaseModel):
    text: str
    source_label: str = "pasted"


class ChatRequest(BaseModel):
    question: str
    language: Optional[str] = None
    detail_level: Literal["full", "basic"] = "full"


class CitationOut(BaseModel):
    document_id: str
    visit_date: Optional[str] = None
    chunk_text: str


class ChatResponse(BaseModel):
    answer: str
    citations: list[CitationOut] = Field(default_factory=list)
    escalated: bool = False
    safety_triggered: bool = False
    trend: Optional[list[dict[str, Any]]] = None


class EscalateBody(BaseModel):
    question: str
    context: Optional[str] = None


class EscalateResponse(BaseModel):
    ticket_id: str
    status: Literal["queued"] = "queued"
