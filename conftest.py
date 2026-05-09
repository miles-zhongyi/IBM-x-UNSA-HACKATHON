import os

# Fast deterministic embeddings for the whole pytest session.
os.environ.setdefault("EMBEDDING_BACKEND", "hashed")
