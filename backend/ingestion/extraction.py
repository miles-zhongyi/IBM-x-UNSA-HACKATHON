"""
Structured extraction from raw note text.

Provides two backends:
  1. watsonx (production) — set WATSONX_API_KEY + WATSONX_PROJECT_ID
  2. heuristic (dev/demo fallback) — regex + pattern-based extractor

The pipeline calls extract_structured(text) and gets back an ExtractedDocument.
The two backends are interchangeable.
"""

from __future__ import annotations

import json
import os
import re
from datetime import date, datetime
from typing import Optional

from dateutil import parser as date_parser

from .models import (
    Diagnosis,
    ExtractedDocument,
    FollowUp,
    LabValue,
    Medication,
    Provider,
    Vitals,
)


# ---------------------------------------------------------------------------
# The extraction prompt — used by the watsonx backend.
# This is the most important prompt in the ingestion layer. It pins the JSON
# shape, demands null-when-missing, and forbids invention.
# ---------------------------------------------------------------------------
EXTRACTION_SYSTEM_PROMPT = """You are a clinical data extraction system. \
You read medical notes and return structured JSON. You never invent information \
that is not present in the source text. If a field is not stated, use null or \
an empty list."""


EXTRACTION_USER_PROMPT = """Extract structured data from this medical document.

Return ONLY valid JSON matching this exact schema. No commentary, no markdown.

{{
  "document_type": "visit_note | admission_note | icu_note | hospice_note | discharge_summary | lab_report | medication_list | referral_letter | imaging_report | unknown",
  "visit_date": "YYYY-MM-DD or null",
  "provider": {{
    "name": "string or null",
    "specialty": "string or null",
    "facility": "string or null"
  }},
  "chief_complaint": "1 sentence describing why the patient was seen, or null",
  "diagnoses": [
    {{
      "name": "human-readable diagnosis (e.g., 'Type 2 Diabetes')",
      "icd_code": "ICD-10 code if explicitly stated, else null",
      "status": "active | resolved | suspected | chronic | null"
    }}
  ],
  "medications": [
    {{
      "name": "drug name",
      "dose": "e.g., '500 mg' or null",
      "frequency": "e.g., 'twice daily' or null",
      "purpose": "what it treats, if stated, else null"
    }}
  ],
  "lab_values": [
    {{
      "name": "lab name (e.g., 'A1C', 'Troponin I')",
      "value": <number or null>,
      "value_text": "string for non-numeric (e.g., 'negative') or null",
      "unit": "e.g., 'mg/dL' or null",
      "reference_range": "e.g., '<7.0' or null",
      "flag": "high | low | normal | critical | null"
    }}
  ],
  "vitals": {{
    "blood_pressure": "e.g., '168/96' or null",
    "heart_rate": "e.g., '92' or null",
    "respiratory_rate": "e.g., '22' or null",
    "temperature": "e.g., '98.6 F' or null",
    "spo2": "e.g., '94% on room air' or null"
  }},
  "instructions_to_patient": ["short strings of instructions given to the patient"],
  "follow_up": {{
    "next_appointment": "string or null",
    "tests_ordered": ["list"],
    "referrals": ["list"]
  }},
  "summary": "1-2 sentences in plain language describing this visit/document"
}}

DOCUMENT:
---
{text}
---

JSON:"""


# ---------------------------------------------------------------------------
# Backend selection
# ---------------------------------------------------------------------------
def extract_structured(text: str) -> ExtractedDocument:
    """Public entry point. Routes to watsonx or heuristic backend."""
    if os.getenv("WATSONX_API_KEY") and os.getenv("WATSONX_PROJECT_ID"):
        try:
            return _extract_with_watsonx(text)
        except Exception as e:
            print(f"[extraction] watsonx failed ({e}), falling back to heuristic")
            return _extract_with_heuristics(text)
    return _extract_with_heuristics(text)


# ---------------------------------------------------------------------------
# watsonx backend
# ---------------------------------------------------------------------------
def _extract_with_watsonx(text: str) -> ExtractedDocument:
    """Call IBM watsonx.ai Granite model and parse JSON output."""
    from ibm_watsonx_ai import Credentials  # lazy import
    from ibm_watsonx_ai.foundation_models import ModelInference

    credentials = Credentials(
        url=os.getenv("WATSONX_URL", "https://us-south.ml.cloud.ibm.com"),
        api_key=os.environ["WATSONX_API_KEY"],
    )
    model = ModelInference(
        model_id=os.getenv("WATSONX_MODEL_ID", "ibm/granite-3-8b-instruct"),
        credentials=credentials,
        project_id=os.environ["WATSONX_PROJECT_ID"],
        params={
            "decoding_method": "greedy",
            "max_new_tokens": 2000,
            "temperature": 0,
        },
    )

    prompt = (
        f"<|system|>\n{EXTRACTION_SYSTEM_PROMPT}\n"
        f"<|user|>\n{EXTRACTION_USER_PROMPT.format(text=text)}\n"
        f"<|assistant|>\n"
    )
    response = model.generate_text(prompt=prompt)
    raw = response.strip()

    # Strip code fences if the model added them
    if raw.startswith("```"):
        raw = re.sub(r"^```(?:json)?\s*", "", raw)
        raw = re.sub(r"\s*```$", "", raw)

    data = json.loads(raw)
    return _parse_extracted_json(data)


def _parse_extracted_json(data: dict) -> ExtractedDocument:
    """Convert raw JSON dict to validated ExtractedDocument."""
    # Date parsing — be tolerant
    if data.get("visit_date"):
        data["visit_date"] = _safe_parse_date(data["visit_date"])
    return ExtractedDocument(**data)


# ---------------------------------------------------------------------------
# Heuristic backend — works without API keys, good enough for demos
# ---------------------------------------------------------------------------
def _extract_with_heuristics(text: str) -> ExtractedDocument:
    """
    Pattern-based extraction. Not as good as an LLM but deterministic and free.
    Lets the rest of the pipeline run end-to-end without API credentials.
    """
    return ExtractedDocument(
        document_type=_classify_doc_type(text),
        visit_date=_extract_visit_date(text),
        provider=_extract_provider(text),
        chief_complaint=_extract_chief_complaint(text),
        diagnoses=_extract_diagnoses(text),
        medications=_extract_medications(text),
        lab_values=_extract_lab_values(text),
        vitals=_extract_vitals(text),
        instructions_to_patient=_extract_instructions(text),
        follow_up=_extract_follow_up(text),
        summary=_build_summary(text),
    )


def _classify_doc_type(text: str):
    t = text.lower()
    if "icu" in t or "intubated" in t or "ventilator" in t or "ventilated" in t:
        return "icu_note"
    if "hospice" in t or "palliative" in t or "comfort care" in t:
        return "hospice_note"
    if "admission" in t and ("admitted" in t or "reason for admission" in t):
        return "admission_note"
    if "discharge" in t and "summary" in t:
        return "discharge_summary"
    if "referral" in t and ("dear" in t or "letter" in t):
        return "referral_letter"
    if any(w in t for w in ["imaging", "ct ", "mri", "x-ray", "ultrasound"]) and "report" in t:
        return "imaging_report"
    return "visit_note"


def _safe_parse_date(s) -> Optional[date]:
    if not s:
        return None
    if isinstance(s, date):
        return s
    try:
        return date_parser.parse(str(s), fuzzy=True).date()
    except Exception:
        return None


def _extract_visit_date(text: str) -> Optional[date]:
    # Look for explicit "presenting at HH:MM" or "admitted ... at HH:MM" patterns
    # but also full dates like "March 15, 2024" or "2024-03-15"
    patterns = [
        r"\b(\d{4}-\d{2}-\d{2})\b",
        r"\b(\d{1,2}/\d{1,2}/\d{2,4})\b",
        r"\b((?:January|February|March|April|May|June|July|August|September|October|November|December)\s+\d{1,2},?\s+\d{4})\b",
    ]
    for pat in patterns:
        m = re.search(pat, text)
        if m:
            d = _safe_parse_date(m.group(1))
            if d:
                return d
    return None


def _extract_provider(text: str) -> Optional[Provider]:
    # Look for "Dr. <Name>" mentions
    m = re.search(r"\bDr\.?\s+([A-Z][a-zA-Z]+(?:\s+[A-Z][a-zA-Z]+)?)", text)
    name = m.group(0) if m else None

    specialty = None
    for kw in [
        "Cardiology",
        "Oncology",
        "Trauma surgery",
        "Pulmonary medicine",
        "Neurology",
        "Internal medicine",
        "Family medicine",
        "Emergency medicine",
    ]:
        if kw.lower() in text.lower():
            specialty = kw
            break

    if not name and not specialty:
        return None
    return Provider(name=name, specialty=specialty)


def _extract_chief_complaint(text: str) -> Optional[str]:
    for label in [
        r"Reason for admission\s*[-:]\s*",
        r"Chief complaint\s*[-:]\s*",
        r"Presenting complaint\s*[-:]\s*",
    ]:
        m = re.search(label + r"(.+?)(?:\n\n|\n[A-Z])", text, re.IGNORECASE | re.DOTALL)
        if m:
            return m.group(1).strip().rstrip(".") + "."
    return None


def _extract_diagnoses(text: str) -> list[Diagnosis]:
    """
    Pull diagnoses from the Past medical history, Medical history, and
    Assessment sections.

    Tries each in order; uses a `seen` set so the same condition mentioned
    in PMH and Assessment doesn't get duplicated.
    """
    diagnoses: list[Diagnosis] = []
    seen: set[str] = set()

    # Past medical history → chronic conditions
    pmh_match = re.search(
        r"Past medical history\s*[-:]\s*(.+?)(?:\n\n|\nCurrent medications|\nSocial)",
        text,
        re.IGNORECASE | re.DOTALL,
    )
    if pmh_match:
        body = pmh_match.group(1)
        if "nil" not in body.lower():
            for item in _split_list(body):
                cleaned = _clean_diagnosis(item)
                if cleaned and cleaned.lower() not in seen:
                    seen.add(cleaned.lower())
                    diagnoses.append(Diagnosis(name=cleaned, status="chronic"))

    # Medical history (alternative section name, e.g. hospice notes)
    if not pmh_match:
        mh_match = re.search(
            r"Medical history\s*[-:]\s*(.+?)(?:\n\n|\nCurrent medications)",
            text,
            re.IGNORECASE | re.DOTALL,
        )
        if mh_match:
            # Take the first sentence as the primary diagnosis
            first_sentence = mh_match.group(1).split(".")[0].strip()
            cleaned = _clean_diagnosis(first_sentence)
            if cleaned and cleaned.lower() not in seen:
                seen.add(cleaned.lower())
                diagnoses.append(Diagnosis(name=cleaned, status="active"))

    # Assessment → active diagnoses for THIS visit
    assess_match = re.search(
        r"\nAssessment\s*[-:]?\s*\n(.+?)(?:\n\s*Plan\s*[-:\n])",
        text,
        re.IGNORECASE | re.DOTALL,
    )
    if assess_match:
        for line in assess_match.group(1).splitlines():
            cleaned = _clean_diagnosis(line)
            if cleaned and cleaned.lower() not in seen:
                seen.add(cleaned.lower())
                diagnoses.append(Diagnosis(name=cleaned, status="active"))

    return diagnoses


def _split_list(s: str) -> list[str]:
    parts = re.split(r"[,;\n]| and ", s)
    return [p.strip() for p in parts if p.strip()]


# Lines starting with these labels are NOT diagnoses
_NON_DIAGNOSIS_PREFIXES = (
    "plan", "assessment", "patient", "the ", "no ", "nil",
    "karnofsky", "pps", "adls", "mobility", "nutritional status",
    "ecg", "ct ", "mri", "investigations", "vital", "general",
    "ventilator", "mode", "tidal", "peep", "fio2", "rr", "rass",
    "cardiovascular", "respiratory", "abdominal", "extremities",
    "neurological", "heent", "skin", "current",
)


def _clean_diagnosis(s: str) -> Optional[str]:
    s = s.strip().rstrip(".").strip()
    s = re.sub(r"^[\d\.\)\-•\s]+", "", s)  # strip list markers
    if not s or len(s) < 3 or len(s) > 120:
        return None
    lower = s.lower()
    if lower.startswith(_NON_DIAGNOSIS_PREFIXES):
        return None
    # Lines containing ":" with a numeric value are usually scores/labs, not Dx
    if ":" in s and re.search(r"\d+\s*%", s):
        return None
    return s


def _extract_medications(text: str) -> list[Medication]:
    meds: list[Medication] = []
    section = re.search(
        r"Current medications\s*[-:]\s*(.+?)(?:\n\n|\nSocial|\nFamily|\nPhysical|\nReason)",
        text,
        re.IGNORECASE | re.DOTALL,
    )
    if not section:
        return meds

    body = section.group(1).strip().rstrip(".")

    # Split on commas but respect medication patterns
    items = [x.strip() for x in re.split(r",\s*(?=[a-zA-Z])", body) if x.strip()]
    for item in items:
        # name dose frequency, e.g., "Metformin 500 mg BID"
        m = re.match(
            r"([A-Za-z][A-Za-z0-9\-/\s]+?)\s+([\d\.]+\s*(?:mg|mcg|g|mL|units|U|%|mg/mL))(?:\s+([A-Za-z\s]+?))?(?:\.|$)",
            item,
        )
        if m:
            name = m.group(1).strip()
            dose = m.group(2).strip()
            freq = m.group(3).strip() if m.group(3) else None
            meds.append(Medication(name=name, dose=dose, frequency=freq))
        else:
            # Fallback: take the first 1-3 words as name
            words = item.split()
            if words:
                meds.append(Medication(name=" ".join(words[:3])))
    return meds


def _extract_lab_values(text: str) -> list[LabValue]:
    """
    Heuristic lab extraction. Looks for known labs and pulls the number
    immediately following.
    """
    labs: list[LabValue] = []

    # Common lab patterns: "Name <value> <unit>" with optional flag
    patterns = [
        # ECG findings get pulled as text-only
        (r"ECG\s*[:\-]\s*([^.\n]+)", "ECG", None, "value_text"),
        (r"Troponin\s*I?\s*[:\-]?\s*([\d\.]+)\s*(ng/mL)?", "Troponin I", "ng/mL", "value"),
        (r"BNP\s*[:\-]?\s*([\d\.]+)\s*(pg/mL)?", "BNP", "pg/mL", "value"),
        (r"WBC\s+([\d\.]+)", "WBC", "x10^9/L", "value"),
        (r"Hgb\s+([\d\.]+)", "Hgb", "g/dL", "value"),
        (r"Plt\s+([\d\.]+)", "Platelets", "x10^9/L", "value"),
        (r"\bNa\s+([\d\.]+)", "Sodium", "mmol/L", "value"),
        (r"\bK\s+([\d\.]+)", "Potassium", "mmol/L", "value"),
        (r"\bCl\s+([\d\.]+)", "Chloride", "mmol/L", "value"),
        (r"\bCO2\s+([\d\.]+)", "CO2", "mmol/L", "value"),
        (r"\bBUN\s+([\d\.]+)", "BUN", "mg/dL", "value"),
        (r"\bCr\s+([\d\.]+)", "Creatinine", "mg/dL", "value"),
        (r"Glucose\s+([\d\.]+)", "Glucose", "mg/dL", "value"),
        (r"Lactate\s*[:\-]?\s*([\d\.]+)", "Lactate", "mmol/L", "value"),
        (r"pH\s+([\d\.]+)", "pH", None, "value"),
        (r"pCO2\s+([\d\.]+)", "pCO2", "mmHg", "value"),
        (r"pO2\s+([\d\.]+)", "pO2", "mmHg", "value"),
        (r"HCO3\s+([\d\.]+)", "HCO3", "mmol/L", "value"),
        (r"ALT\s+([\d\.]+)", "ALT", "U/L", "value"),
        (r"AST\s+([\d\.]+)", "AST", "U/L", "value"),
        (r"ALP\s+([\d\.]+)", "ALP", "U/L", "value"),
        (r"Total bilirubin\s+([\d\.]+)", "Total Bilirubin", "mg/dL", "value"),
        (r"PT/INR\s*[:\-]?\s*[\d\.]+/([\d\.]+)", "INR", None, "value"),
        (r"PTT\s+([\d\.]+)", "PTT", "s", "value"),
        (r"A1C\s*[:\-]?\s*([\d\.]+)", "A1C", "%", "value"),
        (r"LDL\s*[:\-]?\s*([\d\.]+)", "LDL", "mg/dL", "value"),
    ]

    seen = set()
    for pat, name, unit, kind in patterns:
        for m in re.finditer(pat, text):
            key = (name, m.group(1))
            if key in seen:
                continue
            seen.add(key)
            try:
                if kind == "value":
                    val = float(m.group(1))
                    labs.append(LabValue(name=name, value=val, unit=unit))
                else:
                    labs.append(LabValue(name=name, value_text=m.group(1).strip()))
            except (ValueError, IndexError):
                pass

    return labs


def _extract_vitals(text: str) -> Optional[Vitals]:
    section = re.search(
        r"Vital Signs?\s*[:\-]?\s*(.+?)(?:\n\n|\nGeneral|\nNeurological|\nHEENT)",
        text,
        re.IGNORECASE | re.DOTALL,
    )
    if not section:
        return None
    body = section.group(1)

    bp = re.search(r"BP\s*([\d]+/[\d]+)", body)
    hr = re.search(r"HR\s*([\d]+)", body)
    rr = re.search(r"RR\s*([\d]+)(?:\s*\([^)]+\))?", body)
    temp = re.search(r"Temp\s*([\d\.]+\s*°?[FC])", body)
    spo2 = re.search(r"SpO2\s*([\d]+%[^,\n.]*)", body)

    return Vitals(
        blood_pressure=bp.group(1) if bp else None,
        heart_rate=hr.group(1) if hr else None,
        respiratory_rate=rr.group(1) if rr else None,
        temperature=temp.group(1).strip() if temp else None,
        spo2=spo2.group(1).strip() if spo2 else None,
    )


def _extract_instructions(text: str) -> list[str]:
    """Pull bullet-style items from the Plan section."""
    section = re.search(
        r"\nPlan\s*\n(.+?)(?:\Z|\n\n[A-Z][a-z]+\s+(?:Admission|Note))",
        text,
        re.IGNORECASE | re.DOTALL,
    )
    if not section:
        return []
    items = []
    for line in section.group(1).splitlines():
        line = line.strip()
        line = re.sub(r"^[\d\.\)\-•\s]+", "", line)
        if line and 5 < len(line) < 200:
            items.append(line.rstrip("."))
    return items[:15]  # cap


def _extract_follow_up(text: str) -> Optional[FollowUp]:
    consults_match = re.search(r"Consults?\s*[:\-]\s*([^\n]+)", text, re.IGNORECASE)
    referrals = []
    if consults_match:
        referrals = _split_list(consults_match.group(1))
    if not referrals:
        return None
    return FollowUp(referrals=referrals)


def _build_summary(text: str) -> str:
    """Generate a 1-2 sentence summary heuristically."""
    cc = _extract_chief_complaint(text)
    diagnoses = _extract_diagnoses(text)

    parts = []
    if cc:
        parts.append(cc)
    if diagnoses:
        active = [d.name for d in diagnoses if d.status == "active"][:3]
        if active:
            parts.append(f"Working diagnoses: {', '.join(active)}.")
    if not parts:
        # Fallback: first non-empty line
        first_line = next((ln.strip() for ln in text.splitlines() if ln.strip()), "")
        return first_line[:200]
    return " ".join(parts)
