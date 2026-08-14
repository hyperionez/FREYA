from __future__ import annotations

from datetime import datetime, timedelta
from typing import Any

from app.embedding_model import encode

DUPLICATE_SIMILARITY_THRESHOLD = 0.9
TIME_CLUSTER_WINDOW_MINUTES = 10
TIME_CLUSTER_MIN_COUNT = 5


def get_review_authenticity_score(store_id: str, reviews: list[dict[str, Any]]) -> dict[str, Any]:
    if not reviews:
        return {
            "score": 50,
            "source": "heuristic_l1",
            "reasons": ["Belum ada review untuk dianalisis"],
        }

    texts = [r["text"] for r in reviews]
    embeddings = encode(texts)

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
