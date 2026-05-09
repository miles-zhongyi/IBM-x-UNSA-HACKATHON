"""
Load vetted patient-education snippets into a dedicated Chroma collection.

Collection name: `patient_education_reference` (same persistent path as ingestion Chroma).
"""

from __future__ import annotations

import json
from pathlib import Path

import chromadb
from chromadb.config import Settings

from backend.ingestion.embedding import embed_texts
from backend.ingestion.storage import DATA_DIR

COLLECTION_NAME = "patient_education_reference"
_SNIPPETS_PATH = Path(__file__).resolve().parent / "medlineplus_snippets.json"


def _client():
    return chromadb.PersistentClient(
        path=str(DATA_DIR / "chroma"),
        settings=Settings(anonymized_telemetry=False),
    )


def get_reference_collection():
    return _client().get_or_create_collection(
        name=COLLECTION_NAME,
        metadata={"hnsw:space": "cosine"},
    )


def load_corpus_if_empty() -> int:
    """
    If the reference collection is empty, embed and index all snippets.
    Returns number of vectors indexed (0 if already populated).
    """
    coll = get_reference_collection()
    if coll.count() > 0:
        return 0

    if not _SNIPPETS_PATH.exists():
        return 0

    rows = json.loads(_SNIPPETS_PATH.read_text(encoding="utf-8"))
    if not isinstance(rows, list) or not rows:
        return 0

    ids: list[str] = []
    documents: list[str] = []
    metadatas: list[dict] = []
    for i, row in enumerate(rows):
        topic_id = str(row.get("topic_id") or f"topic_{i}")
        title = str(row.get("title") or "Health topic")
        body = str(row.get("text") or "").strip()
        if not body:
            continue
        ids.append(f"ref_row_{i}")
        documents.append(f"{title}\n\n{body}")
        meta = {
            "topic_id": topic_id,
            "title": title,
            "source": str(row.get("source") or "Patient education snippet (demo corpus)"),
        }
        url = row.get("source_url")
        if url:
            meta["source_url"] = str(url)
        metadatas.append(meta)

    if not ids:
        return 0

    embeddings = embed_texts(documents)
    coll.add(ids=ids, documents=documents, embeddings=embeddings, metadatas=metadatas)
    return len(ids)


def query_reference_collection(query_embedding: list[float], n_results: int = 5) -> list[dict]:
    coll = get_reference_collection()
    if coll.count() == 0:
        return []
    results = coll.query(query_embeddings=[query_embedding], n_results=n_results)
    out: list[dict] = []
    if not results["ids"] or not results["ids"][0]:
        return out
    for i in range(len(results["ids"][0])):
        out.append(
            {
                "id": results["ids"][0][i],
                "text": results["documents"][0][i],
                "metadata": results["metadatas"][0][i],
                "distance": results["distances"][0][i] if results.get("distances") else None,
            }
        )
    return out


def reset_reference_corpus() -> None:
    """Delete the reference collection (dev/demo reset)."""
    try:
        _client().delete_collection(COLLECTION_NAME)
    except Exception:
        pass
