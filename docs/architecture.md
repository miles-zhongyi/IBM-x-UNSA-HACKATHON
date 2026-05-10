# Architecture

## System diagram (Mermaid)

```mermaid
flowchart LR
  subgraph Client
    FE[Next.js 14 frontend]
  end

  subgraph API
    FA[FastAPI]
  end

  subgraph Chat
    IN[intent.py]
    SA[safety.py]
    RT[retrieval.py]
    GN[generation.py]
    TR[translation.py]
    WX[watsonx_client.py]
  end

  subgraph Data
    SQL[(SQLite)]
    CHR[(Chroma: patient chunks)]
    REF[(Chroma: education snippets)]
  end

  FE -->|REST JSON| FA
  FA --> IN
  IN --> SA
  SA -->|blocked| FE
  SA --> RT
  RT --> SQL
  RT --> CHR
  RT --> REF
  RT --> GN
  GN --> WX
  GN --> FE
```

## Data flow (ingestion)

```mermaid
sequenceDiagram
  participant U as User
  participant API as FastAPI
  participant P as pipeline.ingest_text
  participant S as storage
  U->>API: POST /api/patients/{id}/documents
  API->>P: ingest_text(text, patient_id)
  P->>S: SQLite rows + Chroma chunks
  API-->>U: IngestionResult (document_id, counts)
```

## PNG diagram

If you need a slide‑ready raster, paste the first Mermaid block into [mermaid.live](https://mermaid.live) and export PNG as `docs/architecture_diagram.png`.
