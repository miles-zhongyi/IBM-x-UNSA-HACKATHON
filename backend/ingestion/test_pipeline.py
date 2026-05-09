"""
End-to-end demo of the ingestion layer.

Runs three sample documents through the pipeline (one per patient), then
exercises the DAL functions (timeline, labs, meds, dx) and a vector search,
showing exactly what RAG and the UI will receive downstream.
"""

import json
from pathlib import Path

from .embedding import embed_query
from .pipeline import ingest_text
from .storage import (
    get_active_medications,
    get_all_labs,
    get_diagnoses,
    get_document_by_id,
    get_lab_trend,
    get_patient_timeline,
    reset_all,
    search_chunks,
)


def banner(title: str):
    print("\n" + "=" * 72)
    print(f"  {title}")
    print("=" * 72)


def pretty(obj):
    """JSON dump that handles dates."""
    return json.dumps(obj, indent=2, default=str)


def main():
    # Start fresh so the demo is reproducible
    reset_all()

    # ---------------------------------------------------------------
    # 1. Ingest three documents — one per patient
    # ---------------------------------------------------------------
    banner("STAGE 1 — INGEST THREE CLINICAL DOCUMENTS")

    samples_dir = Path(__file__).parent / "sample_notes"
    cases = [
        ("patient_001_marcus", samples_dir / "note1_stemi.txt"),
        ("patient_002_emma", samples_dir / "note2_icu_mva.txt"),
        ("patient_003_dorothy", samples_dir / "note3_hospice.txt"),
    ]

    for patient_id, path in cases:
        text = path.read_text()
        result = ingest_text(text, patient_id=patient_id, source_label=path.name)
        print(f"\n--- {patient_id} ({path.name}) ---")
        print(pretty(result.model_dump()))

    # ---------------------------------------------------------------
    # 2. Exercise the structured DAL — what the timeline UI would see
    # ---------------------------------------------------------------
    banner("STAGE 2 — STRUCTURED DAL QUERIES (used by Timeline UI)")

    print("\n[get_patient_timeline] for patient_001_marcus:")
    timeline = get_patient_timeline("patient_001_marcus")
    print(pretty(timeline))

    print("\n[get_diagnoses] for patient_001_marcus:")
    dx = get_diagnoses("patient_001_marcus")
    print(pretty(dx))

    print("\n[get_active_medications] for patient_001_marcus:")
    meds = get_active_medications("patient_001_marcus")
    print(pretty(meds))

    print("\n[get_all_labs] for patient_001_marcus (sample of 5):")
    labs = get_all_labs("patient_001_marcus")
    print(pretty(labs[:5]))
    print(f"  ... ({len(labs)} total lab values)")

    # ---------------------------------------------------------------
    # 3. Exercise the trend lookup — used by RAG for trend questions
    # ---------------------------------------------------------------
    banner("STAGE 3 — TREND LOOKUP (used by RAG for 'has my X changed?')")

    print("\n[get_lab_trend] glucose for patient_001_marcus:")
    glucose_trend = get_lab_trend("patient_001_marcus", "glucose")
    print(pretty(glucose_trend))

    print("\n[get_lab_trend] troponin for patient_001_marcus:")
    trop = get_lab_trend("patient_001_marcus", "troponin")
    print(pretty(trop))

    # ---------------------------------------------------------------
    # 4. Exercise the vector search — what the RAG retriever uses
    # ---------------------------------------------------------------
    banner("STAGE 4 — SEMANTIC SEARCH (used by RAG retriever)")

    queries = [
        ("patient_001_marcus", "what did the doctors think was wrong with my heart"),
        ("patient_001_marcus", "what blood pressure medication am I on"),
        ("patient_002_emma", "what injuries did I have from the car accident"),
        ("patient_002_emma", "ventilator settings"),
        ("patient_003_dorothy", "what is my prognosis"),
        ("patient_003_dorothy", "pain medication"),
    ]

    for patient_id, q in queries:
        print(f"\n[search_chunks] patient={patient_id!r}  query={q!r}")
        q_emb = embed_query(q)
        results = search_chunks(patient_id=patient_id, query_embedding=q_emb, n_results=3)
        for i, hit in enumerate(results, 1):
            preview = hit["text"].replace("\n", " ")[:160]
            print(f"  {i}. [section={hit['metadata'].get('section')!r:25} "
                  f"distance={hit['distance']:.3f}]")
            print(f"     {preview}...")

    # ---------------------------------------------------------------
    # 5. Verify cross-patient isolation
    # ---------------------------------------------------------------
    banner("STAGE 5 — CROSS-PATIENT ISOLATION CHECK")
    print("\nSearching patient_001_marcus for 'pancreatic cancer'")
    print("(only patient_003_dorothy has this — patient_001 should return clean results)")
    q_emb = embed_query("pancreatic cancer chemotherapy")
    results = search_chunks(patient_id="patient_001_marcus", query_embedding=q_emb, n_results=2)
    for hit in results:
        print(f"  - doc_type={hit['metadata'].get('document_type')} "
              f"section={hit['metadata'].get('section')}")
        if "pancreatic" in hit["text"].lower() or "cancer" in hit["text"].lower():
            print("  ⚠️  LEAK DETECTED — this should not appear")
        else:
            print("  ✓ no leak (chunk is from patient_001's own records)")

    # ---------------------------------------------------------------
    # 6. Citation expansion — what the UI does when user clicks a citation
    # ---------------------------------------------------------------
    banner("STAGE 6 — CITATION EXPANSION")
    if timeline:
        first_doc_id = timeline[0]["id"]
        full = get_document_by_id(first_doc_id)
        print(f"\n[get_document_by_id] {first_doc_id!r}:")
        print(f"  visit_date: {full['visit_date']}")
        print(f"  document_type: {full['document_type']}")
        print(f"  provider: {full['provider_name']}")
        print(f"  summary: {full['summary']}")
        print(f"  raw_text (first 300 chars): {full['raw_text'][:300]}...")

    banner("DONE")
    print("\nAll three documents ingested. SQLite + ChromaDB are populated.")
    print("RAG and UI teammates can now read via the DAL functions in storage.py.")


if __name__ == "__main__":
    main()
