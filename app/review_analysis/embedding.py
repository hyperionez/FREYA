"""Modul Review Analysis — Lapis 1 heuristic pre-filter (Fase 2,
context/07-roadmap-milestone.md; algorithm spec: context/08-review-analysis-
module.md §2).

Always runs (free, fast, no API cost): embed reviews locally with
sentence-transformers, then flag near-duplicate text (cosine similarity) and
posting-time clustering. Lapis 2 (Gemini + RAG) is out of scope for Fase 2 —
ambiguous cases still return the Lapis 1 result rather than escalating.
"""
from __future__ import annotations

from datetime import datetime, timedelta
from functools import lru_cache
from typing import Any

EMBEDDING_MODEL_NAME = "paraphrase-multilingual-MiniLM-L12-v2"

DUPLICATE_SIMILARITY_THRESHOLD = 0.9
TIME_CLUSTER_WINDOW_MINUTES = 10
TIME_CLUSTER_MIN_COUNT = 5


@lru_cache(maxsize=1)
def _model():
    from sentence_transformers import SentenceTransformer

    return SentenceTransformer(EMBEDDING_MODEL_NAME)


def get_review_authenticity_score(store_id: str, reviews: list[dict[str, Any]]) -> dict[str, Any]:
    """Kontrak stabil ke scoring engine (context/08-review-analysis-module.md §5):
    selalu {score: int 0-100, source: str, reasons: list[str]}, apa pun sumbernya
    (heuristik di sini, atau nanti llm_l2 / finetuned_model dari Track B)."""
    if not reviews:
        return {
            "score": 50,
            "source": "heuristic_l1",
            "reasons": ["Belum ada review untuk dianalisis"],
        }

    texts = [r["text"] for r in reviews]
    embeddings = _model().encode(texts, normalize_embeddings=True)

    duplicate_pairs = _detect_near_duplicates(embeddings)
    duplicated_indices = {i for i, j, _ in duplicate_pairs} | {j for i, j, _ in duplicate_pairs}
    duplicate_ratio = len(duplicated_indices) / len(reviews)

    timestamps = [r["posted_at"] for r in reviews if r.get("posted_at")]
    time_cluster_flag = _detect_time_clustering(timestamps)

    score = _compute_heuristic_score(duplicate_ratio, time_cluster_flag)

    reasons = []
    if duplicate_pairs:
        reasons.append(
            f"{len(duplicated_indices)} dari {len(reviews)} review terdeteksi near-duplicate "
            f"(similarity > {DUPLICATE_SIMILARITY_THRESHOLD})"
        )
    if time_cluster_flag:
        reasons.append(
            f"Terdeteksi {TIME_CLUSTER_MIN_COUNT}+ review masuk dalam rentang "
            f"{TIME_CLUSTER_WINDOW_MINUTES} menit yang sama"
        )
    if not reasons:
        reasons.append("Tidak ditemukan pola duplikasi atau waktu posting mencurigakan")

    return {"score": score, "source": "heuristic_l1", "reasons": reasons}


def _detect_near_duplicates(
    embeddings, threshold: float = DUPLICATE_SIMILARITY_THRESHOLD
) -> list[tuple[int, int, float]]:
    """Cosine similarity between every review pair. Embeddings are
    L2-normalized (encode(..., normalize_embeddings=True)), so dot product
    equals cosine similarity."""
    duplicate_pairs = []
    n = len(embeddings)
    for i in range(n):
        for j in range(i + 1, n):
            sim = float(embeddings[i] @ embeddings[j])
            if sim > threshold:
                duplicate_pairs.append((i, j, sim))
    return duplicate_pairs


def _detect_time_clustering(
    timestamps: list[str],
    window_minutes: int = TIME_CLUSTER_WINDOW_MINUTES,
    min_count: int = TIME_CLUSTER_MIN_COUNT,
) -> bool:
    if len(timestamps) < min_count:
        return False

    parsed = sorted(datetime.fromisoformat(t) for t in timestamps)
    window = timedelta(minutes=window_minutes)

    for i in range(len(parsed)):
        count = 1
        for j in range(i + 1, len(parsed)):
            if parsed[j] - parsed[i] <= window:
                count += 1
            else:
                break
        if count >= min_count:
            return True
    return False


def _compute_heuristic_score(duplicate_ratio: float, time_cluster_flag: bool) -> int:
    score = 100
    score -= duplicate_ratio * 60
    if time_cluster_flag:
        score -= 20
    return max(0, min(100, round(score)))
