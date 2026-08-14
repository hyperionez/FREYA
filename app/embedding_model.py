from __future__ import annotations

from functools import lru_cache

EMBEDDING_MODEL_NAME = "paraphrase-multilingual-MiniLM-L12-v2"


@lru_cache(maxsize=1)
def _model():
    from sentence_transformers import SentenceTransformer

    return SentenceTransformer(EMBEDDING_MODEL_NAME)


def encode(texts: list[str]):
    return _model().encode(texts, normalize_embeddings=True)
