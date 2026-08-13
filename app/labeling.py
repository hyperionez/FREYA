"""STEP 4 — labeling (Fase 3, context/07-roadmap-milestone.md).

Maps the numeric score from scoring.py to a deterministic label
(Aman/Waspada/Berbahaya) plus concrete reasons (context/02-architecture-ipo.md
§2 STEP 4; thresholds from context/04-fraud-signal-features.md §5). Reasons
are built only from contributions with |contribution| >= 10 — small nudges
don't get surfaced, only material ones. A label is never returned without at
least one reason ("Explainable by default", context/02-architecture-ipo.md §3).
"""
from __future__ import annotations

from typing import Any

AMAN_MIN_SCORE = 75
WASPADA_MIN_SCORE = 40

REASON_CONTRIBUTION_THRESHOLD = 10


def label_stores(stores: list[dict[str, Any]]) -> list[dict[str, Any]]:
    """STEP 4 entry point. Returns each store with an added "assessment" dict."""
    return [{**store, "assessment": label_store(store["scoring"])} for store in stores]


def label_store(scoring: dict[str, Any]) -> dict[str, Any]:
    """Returns {"label": str, "reasons": list[str]}."""
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
