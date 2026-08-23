"""Titik masuk penilaian keaslian review - memilih lapis mana yang menjawab.

Dua lapis memakai kontrak yang sama, `{score, source, reasons}`:

- Lapis 2 (`finetuned.py`) - IndoBERT fine-tuned, dipakai kalau berkas model ada.
- Lapis 1 (`embedding.py`) - heuristik near-duplicate + time clustering, selalu
  tersedia karena tidak butuh berkas apa pun.

Lapis 2 didahulukan, tapi kegagalannya tidak fatal: kalau model tidak terpasang
(berkas model tidak di-commit) atau tidak ada teks review yang bisa dinilai,
penilaian jatuh ke Lapis 1. Field `source` pada hasil menyebutkan lapis mana
yang benar-benar menjawab, jadi perbedaannya terbaca di keluaran, bukan tertelan
diam-diam.
"""

from __future__ import annotations

from typing import Any

from app.review_analysis.embedding import (
    get_review_authenticity_score as _heuristic_score,
)
from app.review_analysis.finetuned import run_finetuned_classifier

__all__ = ["get_review_authenticity_score"]


def get_review_authenticity_score(
    store_id: str, reviews: list[dict[str, Any]]
) -> dict[str, Any]:
    """Nilai keaslian review satu toko, lewat model kalau ada, heuristik kalau tidak."""
    from_model = run_finetuned_classifier(store_id, reviews)
    if from_model is not None:
        return from_model
    return _heuristic_score(store_id, reviews)
