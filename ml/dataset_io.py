"""Pembacaan dataset review bersama untuk ml/train.py dan ml/evaluate.py.

Dataset di repo ini memakai dua bentuk label:

- `data/*.jsonl` (pipeline `ml/build_dataset.py`) memakai integer `0`/`1`.
- `ml/data/annotations.jsonl` (dummy `ml/generate_dummy_data.py`) memakai
  string `"asli"`/`"bot"`.

Modul ini menormalkan keduanya ke integer supaya kedua sumber bisa dipakai
pipeline yang sama tanpa menyalin logika label ke tiap skrip.
"""

from __future__ import annotations

import json
from collections import Counter
from pathlib import Path
from typing import Any

LABEL2ID = {"asli": 0, "bot": 1}
ID2LABEL = {0: "asli", 1: "bot"}

# Kelas ketiga dari tool anotasi (ml/annotate.py:31). Bukan kelas latih:
# context/09-track-b-finetuning-pipeline.md menetapkan "ragu" di-exclude dari
# training. Tetap dipertahankan sebagai nilai tersendiri supaya tidak pernah
# tercampur diam-diam ke asli atau bot.
RAGU = "ragu"

UNLABELED_VALUES = (None, "")


class LabelError(ValueError):
    """Nilai label di luar skema bot/asli/ragu yang dikenal."""


def normalize_label(raw: Any) -> int | str | None:
    """Normalkan label anotasi.

    Kembalikan `0`/`1` untuk kelas latih, `RAGU` untuk keraguan anotator, dan
    `None` kalau baris belum dilabeli.
    """
    if raw in UNLABELED_VALUES:
        return None
    if isinstance(raw, bool):
        raise LabelError(f"label boolean tidak didukung: {raw!r}")
    if isinstance(raw, int):
        if raw in ID2LABEL:
            return raw
        raise LabelError(f"label integer di luar {sorted(ID2LABEL)}: {raw!r}")
    if isinstance(raw, str):
        key = raw.strip().lower()
        if key == RAGU:
            return RAGU
        if key in LABEL2ID:
            return LABEL2ID[key]
        if key.isdigit() and int(key) in ID2LABEL:
            return int(key)
        raise LabelError(f"label string tidak dikenal: {raw!r}")
    raise LabelError(f"tipe label tidak didukung: {type(raw).__name__}")


def load_records(path: str | Path) -> list[dict[str, Any]]:
    """Baca JSONL dan kembalikan salinan record dengan label ternormalisasi.

    Baris kosong dilewati. Baris tanpa label ikut terbawa dengan `label=None`
    supaya berkas seperti `data/to_label.jsonl` bisa diperiksa apa adanya.
    Berkas sumber tidak pernah ditulis ulang.
    """
    path = Path(path)
    records = []
    with path.open(encoding="utf-8") as f:
        for line_number, line in enumerate(f, start=1):
            line = line.strip()
            if not line:
                continue
            try:
                record = json.loads(line)
            except json.JSONDecodeError as exc:
                raise ValueError(f"{path.name} baris {line_number}: JSON rusak - {exc}") from exc
            try:
                label = normalize_label(record.get("label"))
            except LabelError as exc:
                raise LabelError(f"{path.name} baris {line_number}: {exc}") from exc
            records.append({**record, "label": label})
    return records


def load_labeled_records(path: str | Path) -> list[dict[str, Any]]:
    """Baris yang bisa dipakai training biner: hanya label 0/1, teks wajib terisi.

    Baris `None` (belum dilabeli) dan `RAGU` dilewati — keduanya bukan ground
    truth biner. Pakai `annotation_summary` kalau butuh hitungannya.
    """
    path = Path(path)
    if not path.exists():
        raise FileNotFoundError(f"dataset tidak ditemukan: {path}")

    labeled = []
    for position, record in enumerate(load_records(path), start=1):
        if record["label"] is None or record["label"] == RAGU:
            continue
        text = record.get("text")
        if not isinstance(text, str) or not text.strip():
            raise ValueError(
                f"{path.name} record ke-{position}: field 'text' kosong atau bukan string"
            )
        labeled.append(record)
    return labeled


def label_distribution(records: list[dict[str, Any]]) -> dict[str, int]:
    """Hitung jumlah per kelas, untuk dicetak sebelum training."""
    counts = Counter(ID2LABEL[r["label"]] for r in records)
    return dict(sorted(counts.items()))


def annotation_summary(path: str | Path) -> dict[str, int]:
    """Hitung kemajuan anotasi: asli / bot / ragu / belum, plus total.

    Rasio ragu terhadap yang sudah dilabeli dipakai untuk mengecek target
    rubrik (10-20%); di luar rentang itu kualitas label perlu diperiksa.
    """
    counts = {"asli": 0, "bot": 0, RAGU: 0, "belum": 0}
    records = load_records(path)
    for record in records:
        label = record["label"]
        if label is None:
            counts["belum"] += 1
        elif label == RAGU:
            counts[RAGU] += 1
        else:
            counts[ID2LABEL[label]] += 1
    return {**counts, "total": len(records)}
