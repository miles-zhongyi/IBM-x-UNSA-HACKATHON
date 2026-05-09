"""
extraction_extensions.py — Drop-in additions for extraction.py

Two additions:
  1. normalize_language()   — detect + translate non-English text before extraction
  2. extract_structured_from_parsed() — document-type-aware wrapper around
                                        extract_structured() that picks the right
                                        heuristic pre-processor for lab reports,
                                        discharge summaries, Excel tables, etc.

HOW TO INTEGRATE:
  In pipeline.py, replace:
      extracted = extract_structured(text)
  With:
      from .extraction_extensions import extract_structured_from_parsed
      extracted = extract_structured_from_parsed(text, source_label=source_label)
"""

from __future__ import annotations

import os
import re
from typing import Optional

from .extraction import extract_structured, EXTRACTION_SYSTEM_PROMPT, EXTRACTION_USER_PROMPT, _parse_extracted_json
from .models import (
    Diagnosis,
    ExtractedDocument,
    FollowUp,
    LabValue,
    Medication,
)


# ---------------------------------------------------------------------------
# 1. Language normalization
# ---------------------------------------------------------------------------

def normalize_language(text: str, target_lang: str = "en") -> tuple[str, str]:
    """
    Detect the language of the text and translate to English if needed.
    Returns (translated_text, detected_lang_code).

    Uses Featherless AI API if FEATHERLESS_API_KEY is set,
    otherwise falls back to returning the original text.
    """
    detected = _detect_language(text)
    if detected == target_lang or detected == "en":
        return text, detected

    translated = _translate_via_featherless(text, source_lang=detected, target_lang=target_lang)
    return translated, detected


def _detect_language(text: str) -> str:
    """
    Detect language. Uses langdetect if available, otherwise simple heuristics.
    Returns a BCP-47 short code: 'en', 'es', 'fr', 'zh', etc.
    """
    try:
        from langdetect import detect
        return detect(text[:2000])  # sample first 2000 chars for speed
    except Exception:
        pass

    # Heuristic fallback — catches the most common non-English cases
    t = text.lower()
    if re.search(r"\b(el|la|los|las|medicamento|dolor|fiebre|paciente)\b", t):
        return "es"
    if re.search(r"\b(le|la|les|médicament|douleur|patient)\b", t):
        return "fr"
    if re.search(r"[\u4e00-\u9fff]", text):
        return "zh"
    if re.search(r"[\u0600-\u06ff]", text):
        return "ar"
    return "en"


def _translate_via_featherless(text: str, source_lang: str, target_lang: str = "en") -> str:
    """
    Translate text using Featherless AI API.
    Falls back to original text if the API key is missing or call fails.
    """
    api_key = os.getenv("FEATHERLESS_API_KEY")
    if not api_key:
        print("[extraction] FEATHERLESS_API_KEY not set — skipping translation.")
        return text

    lang_names = {
        "es": "Spanish", "fr": "French", "zh": "Chinese",
        "ar": "Arabic", "de": "German", "pt": "Portuguese",
    }
    src_name = lang_names.get(source_lang, source_lang)
    tgt_name = lang_names.get(target_lang, "English")

    try:
        import requests
        response = requests.post(
            "https://api.featherless.ai/v1/chat/completions",
            headers={
                "Authorization": f"Bearer {api_key}",
                "Content-Type": "application/json",
            },
            json={
                "model": "meta-llama/Llama-3.3-70B-Instruct",
                "messages": [
                    {
                        "role": "system",
                        "content": (
                            f"You are a medical translator. Translate the following clinical document "
                            f"from {src_name} to {tgt_name}. Preserve all medical terms, numbers, "
                            f"dates, and formatting. Output only the translated text."
                        ),
                    },
                    {"role": "user", "content": text},
                ],
                "max_tokens": 4000,
                "temperature": 0,
            },
            timeout=30,
        )
        return response.json()["choices"][0]["message"]["content"].strip()
    except Exception as e:
        print(f"[extraction] Translation failed ({e}) — using original text.")
        return text


# ---------------------------------------------------------------------------
# 2. Document-type-aware extraction wrapper
# ---------------------------------------------------------------------------

def extract_structured_from_parsed(
    text: str,
    source_label: str = "pasted",
) -> ExtractedDocument:
    """
    Drop-in replacement for extract_structured() that:
      1. Detects + translates non-English text
      2. Detects document type from source_label / content
      3. Routes to a type-specific pre-processor before LLM/heuristic extraction
    
    Args:
        text:         Plain text output from parser.py
        source_label: Original filename (e.g. "lab_report.pdf", "note.docx")

    Returns:
        ExtractedDocument
    """
    # Step 1: Language normalization
    text, detected_lang = normalize_language(text)

    # Step 2: Detect document type from filename + content
    doc_type_hint = _hint_doc_type(source_label, text)

    # Step 3: Pre-process based on doc type (normalize structure for LLM/heuristics)
    if doc_type_hint == "lab_report":
        text = _normalize_lab_report(text)
    elif doc_type_hint == "discharge_summary":
        text = _normalize_discharge_summary(text)
    elif doc_type_hint == "medication_list":
        text = _normalize_medication_list(text)
    elif doc_type_hint == "excel_table":
        text = _normalize_excel_table(text)
    # visit_note / admission_note / icu_note — pass through unchanged,
    # existing heuristics in extraction.py handle them well

    # Step 4: Run the main extractor (watsonx or heuristic fallback)
    result = extract_structured(text)

    # Step 5: Backfill document_type if extractor left it as "unknown"
    if result.document_type == "unknown" and doc_type_hint not in ("excel_table", "unknown"):
        result = result.model_copy(update={"document_type": doc_type_hint})

    return result


# ---------------------------------------------------------------------------
# Document type detection
# ---------------------------------------------------------------------------

def _hint_doc_type(source_label: str, text: str) -> str:
    """
    Guess document type from filename and content.
    Returns one of the DocumentType literals or 'excel_table'.
    """
    label = (source_label or "").lower()
    t = text.lower()

    # Filename signals
    if re.search(r"lab|result|blood|panel|cbc|bmp|lft|lipid", label):
        return "lab_report"
    if re.search(r"discharge|disch|summary", label):
        return "discharge_summary"
    if re.search(r"med|medication|rx|prescription", label):
        return "medication_list"
    if re.search(r"\.xlsx|\.xls|sheet", label):
        return "excel_table"
    if re.search(r"referral|letter", label):
        return "referral_letter"
    if re.search(r"imaging|radiology|ct|mri|xray|x-ray|ultrasound", label):
        return "imaging_report"

    # Content signals (fallback)
    if re.search(r"\b(reference range|flag|result|test date)\b", t):
        return "lab_report"
    if re.search(r"\bdischarge\b.{0,50}\b(summary|diagnosis|instructions)\b", t):
        return "discharge_summary"
    if re.search(r"sheet:", t):  # from Excel parser
        return "excel_table"

    return "unknown"


# ---------------------------------------------------------------------------
# Pre-processors: normalize non-SOAP formats into SOAP-like text
# so the existing heuristic extractor can parse them
# ---------------------------------------------------------------------------

def _normalize_lab_report(text: str) -> str:
    """
    Lab reports often look like tables: Name | Value | Unit | Range | Flag
    Reformat into a clean "Investigations" section that the heuristic extractor
    and the LLM prompt both understand well.
    """
    lines = text.splitlines()
    lab_lines: list[str] = []
    other_lines: list[str] = []

    # Detect table rows: lines with 2+ pipe separators or tab-separated numbers
    for line in lines:
        stripped = line.strip()
        if not stripped:
            continue
        if stripped.count("|") >= 2 or (
            re.search(r"\d", stripped) and re.search(r"\t", stripped)
        ):
            lab_lines.append(stripped)
        else:
            other_lines.append(stripped)

    if not lab_lines:
        return text  # nothing to normalize — return as-is

    # Parse table rows into "Name: Value Unit (Flag)" format
    parsed_labs: list[str] = []
    for row in lab_lines:
        cols = [c.strip() for c in re.split(r"\||\t", row) if c.strip()]
        if len(cols) >= 2:
            name = cols[0]
            value = cols[1] if len(cols) > 1 else ""
            unit = cols[2] if len(cols) > 2 else ""
            flag = cols[4] if len(cols) > 4 else ""
            entry = f"{name}: {value} {unit}".strip()
            if flag and flag.upper() in ("H", "L", "HIGH", "LOW", "CRITICAL", "C"):
                entry += f" [{flag.upper()}]"
            parsed_labs.append(entry)

    # Reassemble: preserve header lines, then add a clean Investigations block
    header = "\n".join(other_lines[:10])  # date, patient info, etc.
    investigations = "Investigations -\n" + "\n".join(parsed_labs)
    return f"{header}\n\n{investigations}"


def _normalize_discharge_summary(text: str) -> str:
    """
    Discharge summaries often have headers like 'Discharge Diagnosis',
    'Hospital Course', 'Discharge Medications', 'Follow-up Instructions'.
    Map these to SOAP equivalents the extractor recognizes.
    """
    replacements = {
        r"Discharge Diagnosis[es]*\s*[:\-]": "Assessment -",
        r"Hospital Course\s*[:\-]": "History of presenting illness -",
        r"Discharge Medications?\s*[:\-]": "Current medications -",
        r"Discharge Instructions?\s*[:\-]": "Plan\n",
        r"Follow[- ]up\s*[:\-]": "Plan -",
        r"Attending Physician\s*[:\-]": "Provider -",
    }
    for pat, replacement in replacements.items():
        text = re.sub(pat, replacement, text, flags=re.IGNORECASE)
    return text


def _normalize_medication_list(text: str) -> str:
    """
    A standalone medication list (e.g. from pharmacy printout).
    Wraps it in a 'Current medications' section so the extractor picks it up.
    """
    if re.search(r"current medications", text, re.IGNORECASE):
        return text  # already has the right header

    lines = [ln.strip() for ln in text.splitlines() if ln.strip()]
    # Find lines that look like medications (start with a capitalized drug name + dose)
    med_lines = [
        ln for ln in lines
        if re.match(r"[A-Z][a-z]+.{0,50}\d+\s*(?:mg|mcg|g|mL|units)", ln)
    ]
    if med_lines:
        header_lines = [ln for ln in lines if ln not in med_lines]
        med_section = "Current medications - " + ", ".join(med_lines)
        return "\n".join(header_lines) + "\n\n" + med_section
    return text


def _normalize_excel_table(text: str) -> str:
    """
    Excel output from parser.py looks like:
        Sheet: Lab Results
        Test Name\tValue\tUnit\tRef Range\tFlag
        ...
    Convert to a pseudo-lab-report that extract_structured() can handle.
    """
    lines = text.splitlines()
    output_sections: list[str] = []
    current_sheet: list[str] = []
    sheet_name = ""

    for line in lines:
        if line.startswith("Sheet:"):
            if current_sheet:
                output_sections.append(_normalize_lab_report("\n".join(current_sheet)))
            sheet_name = line.replace("Sheet:", "").strip()
            current_sheet = []
        else:
            current_sheet.append(line)

    if current_sheet:
        output_sections.append(_normalize_lab_report("\n".join(current_sheet)))

    return "\n\n".join(output_sections)
