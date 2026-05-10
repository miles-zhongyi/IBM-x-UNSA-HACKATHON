"""IBM x UNSA hackathon — backend (ingestion, chat, API)."""

import os as _os
import sys as _sys
import types as _types
from pathlib import Path as _Path

# Load .env from repo root.
_env_path = _Path(__file__).resolve().parents[1] / ".env"
if _env_path.exists():
    for _line in _env_path.read_text(encoding="utf-8").splitlines():
        _line = _line.strip()
        if not _line or _line.startswith("#"):
            continue
        if "=" in _line:
            _k, _, _v = _line.partition("=")
            _k = _k.strip()
            _v = _v.strip().strip("'\"")
            if _k and not _k.startswith("#") and _v:
                _os.environ.setdefault(_k, _v)

# Force offline mode for HuggingFace Hub.
_os.environ["HF_HUB_OFFLINE"] = "1"
_os.environ["TRANSFORMERS_OFFLINE"] = "1"
_os.environ["HF_HUB_DISABLE_IMPLICIT_TOKEN"] = "1"
_os.environ.setdefault("TOKENIZERS_PARALLELISM", "false")
_os.environ.setdefault("EMBEDDING_BACKEND", "hashed")

# When running with hashed embeddings, block sentence_transformers from loading
# (chromadb tries to import it for its default embedding function).
if _os.environ.get("EMBEDDING_BACKEND", "").lower() == "hashed":
    if "sentence_transformers" not in _sys.modules:
        _fake = _types.ModuleType("sentence_transformers")
        _fake.__path__ = []

        class _FakeST:
            def __init__(self, *a, **kw):
                raise ImportError("sentence_transformers blocked by EMBEDDING_BACKEND=hashed")
        _fake.SentenceTransformer = _FakeST
        _sys.modules["sentence_transformers"] = _fake
