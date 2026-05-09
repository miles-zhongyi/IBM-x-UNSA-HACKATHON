"""
Embedding generation.

Two backends, selected automatically:
  1. sentence-transformers (PRODUCTION) — high-quality semantic embeddings.
     Used when the model can be downloaded or is cached locally.
  2. hashed n-gram (FALLBACK) — deterministic, no network, no dependencies.
     Lower retrieval quality but lets the full pipeline run anywhere.

For the hackathon, install sentence-transformers and let it cache the model
on first run. The fallback exists so the code is provably end-to-end runnable
in any environment.

To force the fallback (e.g., in CI), set EMBEDDING_BACKEND=hashed.
"""

from __future__ import annotations

import math
import os
import re
from collections import Counter

_st_model = None  # cached sentence-transformer model
_BACKEND = None   # decided lazily


def _decide_backend() -> str:
    """Pick which embedder to use. Cached after first call."""
    global _BACKEND
    if _BACKEND is not None:
        return _BACKEND

    forced = os.getenv("EMBEDDING_BACKEND", "").lower()
    if forced in ("hashed", "st", "sentence-transformers"):
        _BACKEND = "hashed" if forced == "hashed" else "st"
        return _BACKEND

    # Try sentence-transformers; fall back if unavailable
    try:
        from sentence_transformers import SentenceTransformer

        global _st_model
        _st_model = SentenceTransformer("all-MiniLM-L6-v2")
        _BACKEND = "st"
    except Exception as e:
        print(f"[embedding] sentence-transformers unavailable ({type(e).__name__}); "
              "using hashed n-gram fallback.")
        _BACKEND = "hashed"
    return _BACKEND


def embed_texts(texts: list[str]) -> list[list[float]]:
    """Embed a list of texts. Returns list of float vectors."""
    if not texts:
        return []
    backend = _decide_backend()
    if backend == "st":
        return _embed_with_st(texts)
    return [_hashed_ngram_embed(t) for t in texts]


def embed_query(query: str) -> list[float]:
    """Embed a single query string. Used by RAG retrieval."""
    return embed_texts([query])[0]


# ---------------------------------------------------------------------------
# Backend 1: sentence-transformers
# ---------------------------------------------------------------------------
def _embed_with_st(texts: list[str]) -> list[list[float]]:
    embeddings = _st_model.encode(
        texts,
        batch_size=32,
        show_progress_bar=False,
        convert_to_numpy=True,
        normalize_embeddings=True,
    )
    return embeddings.tolist()


# ---------------------------------------------------------------------------
# Backend 2: hashed n-gram TF (deterministic, no network)
# ---------------------------------------------------------------------------
_HASHED_DIM = 384  # match MiniLM dim so downstream code is identical


def _tokenize(text: str) -> list[str]:
    """Lowercase + word-character tokens, plus character bigrams for medical
    terms (helps match e.g. 'A1C' to 'A1c' or 'STEMI' to 'stemi')."""
    text = text.lower()
    words = re.findall(r"[a-z0-9]+", text)
    tokens = list(words)
    # add bigrams of words
    for i in range(len(words) - 1):
        tokens.append(f"{words[i]}_{words[i+1]}")
    # char trigrams from longer tokens (helps medical jargon)
    for w in words:
        if len(w) >= 5:
            for i in range(len(w) - 2):
                tokens.append(f"#{w[i:i+3]}")
    return tokens


def _hashed_ngram_embed(text: str, dim: int = _HASHED_DIM) -> list[float]:
    """
    Hashed n-gram embedding. Maps each token to a bucket via stable hash,
    accumulates TF, then L2-normalizes. Cosine similarity on these vectors
    correlates with token overlap — good enough for hackathon retrieval.
    """
    tokens = _tokenize(text)
    if not tokens:
        return [0.0] * dim
    counts = Counter(tokens)
    vec = [0.0] * dim
    for tok, c in counts.items():
        h = _stable_hash(tok)
        bucket = h % dim
        # signed hash to prevent collisions canceling out too aggressively
        sign = 1.0 if (h // dim) % 2 == 0 else -1.0
        # log-scale TF
        vec[bucket] += sign * (1.0 + math.log(c))
    # L2 normalize
    norm = math.sqrt(sum(v * v for v in vec))
    if norm > 0:
        vec = [v / norm for v in vec]
    return vec


def _stable_hash(s: str) -> int:
    """FNV-1a 64-bit hash. Deterministic across processes (unlike Python hash())."""
    h = 0xCBF29CE484222325
    for ch in s.encode("utf-8"):
        h ^= ch
        h = (h * 0x100000001B3) & 0xFFFFFFFFFFFFFFFF
    return h

