from __future__ import annotations

from typing import Any

AMAN_MIN_SCORE = 75
WASPADA_MIN_SCORE = 40

REASON_CONTRIBUTION_THRESHOLD = 10


def label_stores(stores: list[dict[str, Any]]) -> list[dict[str, Any]]:
    return [{**store, "assessment": label_store(store["scoring"])} for store in stores]


def label_store(scoring: dict[str, Any]) -> dict[str, Any]:
    return {
        "label": _score_to_label(scoring["score"]),
        "reasons": _build_reasons(scoring["contributions"]),
    }


def _score_to_label(score: int) -> str:
    if score >= AMAN_MIN_SCORE:
        return "Aman"
    if score >= WASPADA_MIN_SCORE:
        return "Waspada"
    return "Berbahaya"


def _build_reasons(contributions: list[dict[str, Any]]) -> list[str]:
    significant = [c for c in contributions if abs(c["contribution"]) >= REASON_CONTRIBUTION_THRESHOLD]
    significant.sort(key=lambda c: abs(c["contribution"]), reverse=True)
    reasons = [c["detail"] for c in significant]
    return reasons or ["Tidak ada sinyal signifikan terdeteksi — skor mendekati baseline netral"]
