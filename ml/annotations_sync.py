"""Jembatan antara berkas anotasi dan kolam review.

`ml/annotate.py` menulis hasil pelabelan ke `data/annotations.jsonl` (append-only,
lengkap dengan `annotated_by`/`annotated_at`), sedangkan `command_gold` di
`ml/build_dataset.py` membaca label dari `data/to_label.jsonl`. Tanpa langkah
penggabungan, hasil anotasi tidak pernah sampai ke gold set.

Dua berkas sengaja dipertahankan: `annotations.jsonl` jadi jejak audit siapa
melabeli apa dan kapan - bahan lampiran proposal - sementara `to_label.jsonl`
tetap jadi kolam yang dibaca tahap berikutnya.

Fungsi di sini murni: menerima list-of-dict, mengembalikan list baru. Pembacaan
dan penulisan berkas ditangani pemanggil di `ml/build_dataset.py`.
"""

from __future__ import annotations

from dataclasses import dataclass
from typing import Any

from ml.anonymize import normalize_for_dedup
from ml.dataset_io import RAGU, normalize_label

AUDIT_FIELDS = ("annotated_by", "annotated_at")


@dataclass(frozen=True)
class MergeReport:
    """Ringkasan hasil penggabungan, untuk dicetak ke terminal."""

    applied: int = 0
    untouched: int = 0
    orphaned: int = 0
    matched_by_text: int = 0


def _validate(annotation: dict[str, Any], position: int) -> None:
    if not annotation.get("review_id"):
        raise ValueError(f"anotasi ke-{position}: tidak ada field 'review_id'")
    label = annotation.get("label")
    if normalize_label(label) is None:
        raise ValueError(f"anotasi ke-{position}: label kosong ({label!r})")


def _latest_by_id(annotations: list[dict[str, Any]]) -> dict[str, dict[str, Any]]:
    """Anotasi terakhir menang - berkasnya append-only, bukan ditimpa di tempat."""
    latest: dict[str, dict[str, Any]] = {}
    for position, annotation in enumerate(annotations, start=1):
        _validate(annotation, position)
        latest[annotation["review_id"]] = annotation
    return latest


def merge_annotations(
    pool: list[dict[str, Any]], annotations: list[dict[str, Any]]
) -> tuple[list[dict[str, Any]], MergeReport]:
    """Tempelkan label + jejak anotator dari `annotations` ke baris `pool`.

    Dicocokkan lewat `review_id`; kalau tidak ketemu, jatuh ke teks yang
    dinormalisasi, karena `review_id` bersifat posisional dan bergeser setiap
    `pack` dijalankan ulang (lihat `ml/build_dataset.py:341`).
    """
    by_id = _latest_by_id(annotations)
    by_text = {normalize_for_dedup(a["text"]): a for a in by_id.values() if a.get("text")}

    merged: list[dict[str, Any]] = []
    applied = untouched = matched_by_text = 0
    used_ids: set[str] = set()

    for row in pool:
        annotation = by_id.get(row.get("review_id"))
        if annotation is None and row.get("text"):
            annotation = by_text.get(normalize_for_dedup(row["text"]))
            if annotation is not None:
                matched_by_text += 1

        if annotation is None:
            merged.append({**row})
            untouched += 1
            continue

        used_ids.add(annotation["review_id"])
        applied += 1
        audit = {field: annotation[field] for field in AUDIT_FIELDS if field in annotation}
        merged.append({**row, "label": normalize_label(annotation["label"]), **audit})

    return merged, MergeReport(
        applied=applied,
        untouched=untouched,
        orphaned=len(by_id) - len(used_ids),
        matched_by_text=matched_by_text,
    )


def clear_labels(pool: list[dict[str, Any]]) -> tuple[list[dict[str, Any]], int]:
    """Kosongkan label dan jejak anotator, siap dilabeli ulang dari nol.

    Dipakai saat label lama tidak lagi dipercaya dan seluruh batch perlu diulang
    sesuai rubrik. Berkas sumber tidak disentuh - pemanggil yang menulis.
    """
    cleared, count = [], 0
    for row in pool:
        if row.get("label") is not None:
            count += 1
        kept = {key: value for key, value in row.items() if key not in AUDIT_FIELDS}
        cleared.append({**kept, "label": None})
    return cleared, count


def label_counts(pool: list[dict[str, Any]]) -> dict[str, int]:
    """Hitung isi kolam per kelas, termasuk yang belum dilabeli."""
    counts = {"asli": 0, "bot": 0, RAGU: 0, "belum": 0}
    names = {0: "asli", 1: "bot", RAGU: RAGU}
    for row in pool:
        label = normalize_label(row.get("label"))
        counts["belum" if label is None else names[label]] += 1
    return counts
