"""
Pydantic models defining the data contract for ingestion outputs.

Everything downstream (RAG, UI, safety) reads through these shapes.
The LLM extraction is constrained to produce JSON matching ExtractedDocument.
"""

from datetime import date
from typing import Optional, Literal
from pydantic import BaseModel, Field


class Provider(BaseModel):
    name: Optional[str] = None
    specialty: Optional[str] = None
    facility: Optional[str] = None


class Diagnosis(BaseModel):
    name: str
    icd_code: Optional[str] = None
    status: Optional[Literal["active", "resolved", "suspected", "chronic"]] = None


class Medication(BaseModel):
    name: str
    dose: Optional[str] = None
    frequency: Optional[str] = None
    purpose: Optional[str] = None


class LabValue(BaseModel):
    name: str
    value: Optional[float] = None
    value_text: Optional[str] = None  # for non-numeric (e.g., "negative")
    unit: Optional[str] = None
    reference_range: Optional[str] = None
    flag: Optional[Literal["high", "low", "normal", "critical"]] = None


class Vitals(BaseModel):
    blood_pressure: Optional[str] = None
    heart_rate: Optional[str] = None
    respiratory_rate: Optional[str] = None
    temperature: Optional[str] = None
    spo2: Optional[str] = None


class FollowUp(BaseModel):
    next_appointment: Optional[str] = None
    tests_ordered: list[str] = Field(default_factory=list)
    referrals: list[str] = Field(default_factory=list)


DocumentType = Literal[
    "visit_note",
    "admission_note",
    "icu_note",
    "hospice_note",
    "discharge_summary",
    "lab_report",
    "medication_list",
    "referral_letter",
    "imaging_report",
    "unknown",
]


class ExtractedDocument(BaseModel):
    """The structured output from LLM extraction."""

    document_type: DocumentType = "unknown"
    visit_date: Optional[date] = None
    provider: Optional[Provider] = None
    chief_complaint: Optional[str] = None
    diagnoses: list[Diagnosis] = Field(default_factory=list)
    medications: list[Medication] = Field(default_factory=list)
    lab_values: list[LabValue] = Field(default_factory=list)
    vitals: Optional[Vitals] = None
    instructions_to_patient: list[str] = Field(default_factory=list)
    follow_up: Optional[FollowUp] = None
    summary: str = ""  # 1-2 sentence plain-language summary


class IngestionResult(BaseModel):
    """What the API returns after processing a document."""

    document_id: str
    patient_id: str
    status: Literal["processed", "failed"]
    summary: str
    document_type: DocumentType
    visit_date: Optional[date] = None
    extracted_counts: dict
    chunks_indexed: int
    error: Optional[str] = None


class Chunk(BaseModel):
    """A chunk of text with metadata, ready to embed."""

    text: str
    section: str
    chunk_index: int
    metadata: dict
