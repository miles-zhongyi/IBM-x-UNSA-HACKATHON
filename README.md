# IBM-x-UNSA-HACKATHON

pipeline.ingest_text(text, patient_id)
      │
      ├─→ extraction.extract_structured()   →  ExtractedDocument (Pydantic)
      │       ├─ watsonx backend (production, set env vars)
      │       └─ heuristic backend (regex fallback, works today)
      │
      ├─→ storage.save_document()           →  SQLite (timeline, dx, meds, labs, vitals)
      │
      ├─→ chunking.chunk_document()         →  Section-aware chunks
      │       ├─ Splits on known headers (HPI, Assessment, Plan, etc.)
      │       └─ Sliding-window fallback for long sections
      │
      ├─→ embedding.embed_texts()           →  384-dim vectors
      │       ├─ sentence-transformers (production)
      │       └─ hashed n-gram (fallback, works offline)
      │
      └─→ storage.store_chunks_in_chroma()  →  ChromaDB with rich metadata
