"""Pisahkan label yang lahir dari pertanyaan yang salah, sisakan yang masih sah.

Pass pertama `data/to_label.jsonl` dilabeli dengan pertanyaan "komentar ini
negatif atau bukan", bukan "review ini bot atau asli". Terbukti dari silang
dengan kolom `Sentiment` bawaan PRDECT-ID: 464 dari 480 label biner mengikuti
kolom itu persis.

Tapi tidak semuanya perlu diulang. Rubrik bagian 5 langkah 2 berbunyi "ada
keluhan atau kritik -> Asli" tanpa syarat, jadi review negatif yang dilabeli
`asli` kebetulan sudah benar menurut rubrik - lewat jalan berbeda, dengan hasil
yang sama. Yang harus diulang adalah review positif: rubrik bagian 4 menyebut
"positif" secara eksplisit sebagai BUKAN bukti, jadi label bot di sana diambil
tanpa dasar.

    python -m ml.relabel_queue plan                      # lihat rencana, tanpa menulis
    python -m ml.relabel_queue apply --annotator michael # kerjakan

`apply` menaruh label yang dipertahankan ke `data/annotations.jsonl` dan
mengosongkan sisanya di `data/to_label.jsonl`. Efeknya `ml/annotate.py` langsung
melanjutkan tepat di review yang perlu diulang, bukan mengulang dari nomor satu.
"""

from __future__ import annotations

import argparse
import csv
import json
import sys
from collections import Counter
from dataclasses import dataclass, field
from datetime import datetime
from pathlib import Path
from typing import Any

REPO_ROOT = Path(__file__).resolve().parent.parent
sys.path.insert(0, str(REPO_ROOT))

from ml.anonymize import normalize_for_dedup  # noqa: E402
from ml.dataset_io import ID2LABEL, RAGU, normalize_label  # noqa: E402

POOL_PATH = REPO_ROOT / "data" / "to_label.jsonl"
ANNOTATIONS_PATH = REPO_ROOT / "data" / "annotations.jsonl"
SOURCE_CSV = REPO_ROOT / "data" / "raw" / "PRDECT-ID.csv"

TEXT_COLUMN = "Customer Review"
SENTIMENT_COLUMN = "Sentiment"

NEGATIVE = "Negative"
POSITIVE = "Positive"
SENTIMENTS = (NEGATIVE, POSITIVE)

AUDIT_FIELDS = ("annotated_by", "annotated_at")

# Label yang tetap sah untuk review negatif (rubrik bagian 5 langkah 2).
KEEPABLE_LABELS = (0, RAGU)


class RelabelError(ValueError):
    """Antrean pelabelan ulang tidak bisa disusun apa adanya."""


@dataclass(frozen=True)
class RelabelPlan:
    """Pembagian kolam: yang dipertahankan vs yang dikembalikan ke antrean."""

    keep: list[dict[str, Any]] = field(default_factory=list)
    redo: list[dict[str, Any]] = field(default_factory=list)

    @property
    def redo_ids(self) -> set[str]:
        return {row["review_id"] for row in self.redo}


# --------------------------------------------------------------------------
# Pemilihan
# --------------------------------------------------------------------------


def _normalise_sentiment_map(sentiment: dict[str, str]) -> dict[str, str]:
    normalised = {}
    for text, value in sentiment.items():
        if value not in SENTIMENTS:
            raise RelabelError(
                f"nilai sentimen tidak dikenal: {value!r}. Yang didukung: {list(SENTIMENTS)}"
            )
        normalised[normalize_for_dedup(text)] = value
    return normalised


def select_for_relabel(pool: list[dict[str, Any]], sentiment: dict[str, str]) -> RelabelPlan:
    """Bagi kolam jadi label yang masih sah dan label yang harus diulang.

    Dipertahankan hanya kalau dua syarat terpenuhi sekaligus: sumbernya review
    **negatif**, dan labelnya `asli` atau `ragu`. Selebihnya - seluruh review
    positif, review negatif yang dilabeli bot, review yang tak terlacak ke
    sumber, dan yang belum dilabeli - kembali ke antrean.
    """
    lookup = _normalise_sentiment_map(sentiment)
    plan = RelabelPlan(keep=[], redo=[])

    for row in pool:
        label = normalize_label(row.get("label"))
        source = lookup.get(normalize_for_dedup(row.get("text", "")))
        if source == NEGATIVE and label in KEEPABLE_LABELS:
            plan.keep.append(row)
        else:
            plan.redo.append(row)

    return plan


# --------------------------------------------------------------------------
# Penulisan ulang
# --------------------------------------------------------------------------


def blank_labels(pool: list[dict[str, Any]], ids: set[str]) -> list[dict[str, Any]]:
    """Kosongkan label review di `ids`, sisanya lewat tanpa disentuh.

    Jejak anotator ikut dibuang untuk baris yang dikosongkan - kalau ditinggal,
    baris itu terlihat seperti sudah dikerjakan orang padahal belum.
    """
    blanked = []
    for row in pool:
        if row["review_id"] not in ids:
            blanked.append({**row})
            continue
        kept = {key: value for key, value in row.items() if key not in AUDIT_FIELDS}
        blanked.append({**kept, "label": None})
    return blanked


def seed_annotations(
    kept: list[dict[str, Any]], annotator: str, at: str | None = None
) -> list[dict[str, Any]]:
    """Ubah label yang dipertahankan jadi baris `annotations.jsonl`.

    Tanpa langkah ini `ml/annotate.py` menghitung nol review selesai dan
    menyodorkan seluruh kolam dari awal, termasuk yang labelnya masih sah.
    """
    if not annotator.strip():
        raise RelabelError("nama anotator wajib diisi - itu yang dicatat di tiap baris")

    stamp = at or datetime.now().isoformat(timespec="seconds")
    records = []
    for row in kept:
        label = normalize_label(row.get("label"))
        if label is None:
            raise RelabelError(f"{row['review_id']} belum dilabeli, tidak bisa jadi seed")
        records.append(
            {
                "review_id": row["review_id"],
                "text": row["text"],
                "label": label,
                "annotated_by": annotator.strip(),
                "annotated_at": stamp,
            }
        )
    return records


# --------------------------------------------------------------------------
# Berkas
# --------------------------------------------------------------------------


def _fail(message: str) -> None:
    print(f"[relabel] {message}", file=sys.stderr)
    raise SystemExit(1)


def _read_jsonl(path: Path) -> list[dict[str, Any]]:
    if not path.exists():
        _fail(f"{path} tidak ada.")
    lines = path.read_text(encoding="utf-8").splitlines()
    return [json.loads(line) for line in lines if line.strip()]


def _write_jsonl(path: Path, records: list[dict[str, Any]]) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    with path.open("w", encoding="utf-8") as handle:
        for record in records:
            handle.write(json.dumps(record, ensure_ascii=False) + "\n")


def load_sentiment(path: Path) -> dict[str, str]:
    """Baca peta teks review -> sentimen dari CSV sumber."""
    if not path.exists():
        _fail(f"{path} tidak ada - sumber sentimen tidak bisa dibaca.")
    with path.open(encoding="utf-8") as handle:
        reader = csv.DictReader(handle)
        missing = {TEXT_COLUMN, SENTIMENT_COLUMN} - set(reader.fieldnames or [])
        if missing:
            _fail(f"{path} tidak punya kolom {sorted(missing)}.")
        return {row[TEXT_COLUMN]: row[SENTIMENT_COLUMN] for row in reader}


# --------------------------------------------------------------------------
# Laporan
# --------------------------------------------------------------------------


def _label_name(label: int | str | None) -> str:
    if label is None:
        return "belum"
    return RAGU if label == RAGU else ID2LABEL[label]


def _breakdown(pool: list[dict[str, Any]], sentiment: dict[str, str]) -> Counter:
    lookup = _normalise_sentiment_map(sentiment)
    counts: Counter = Counter()
    for row in pool:
        source = lookup.get(normalize_for_dedup(row.get("text", ""))) or "tak terlacak"
        counts[(source, _label_name(normalize_label(row.get("label"))))] += 1
    return counts


def _print_plan(plan: RelabelPlan, counts: Counter) -> None:
    print("=" * 70)
    print("RENCANA PELABELAN ULANG")
    print("=" * 70)
    print("\nSumber sentimen  x  label pass pertama:")
    for (source, label), total in sorted(counts.items()):
        keepable = source == NEGATIVE and label in ("asli", RAGU)
        print(f"  {source:>13}  {label:<6} {total:>4}   {'dipertahankan' if keepable else 'DIULANG'}")
    print(f"\nDipertahankan : {len(plan.keep)}")
    print(f"Diulang       : {len(plan.redo)}")


# --------------------------------------------------------------------------
# Perintah
# --------------------------------------------------------------------------


def _build_plan(args: argparse.Namespace) -> tuple[list[dict[str, Any]], RelabelPlan, Counter]:
    pool = _read_jsonl(args.pool)
    sentiment = load_sentiment(args.source)
    try:
        return pool, select_for_relabel(pool, sentiment), _breakdown(pool, sentiment)
    except RelabelError as error:
        _fail(str(error))


def command_plan(args: argparse.Namespace) -> None:
    _, plan, counts = _build_plan(args)
    _print_plan(plan, counts)
    print("\nBelum ada yang ditulis. Jalankan 'apply --annotator NAMA' untuk mengerjakan.")


def command_apply(args: argparse.Namespace) -> None:
    pool, plan, counts = _build_plan(args)
    _print_plan(plan, counts)

    if args.annotations.exists() and args.annotations.stat().st_size > 0 and not args.force:
        _fail(
            f"{args.annotations} sudah berisi anotasi. Menimpanya akan menghapus "
            "jejak kerja yang ada. Pindahkan dulu, atau pakai --force kalau memang "
            "isinya yang mau diganti."
        )

    try:
        seeds = seed_annotations(plan.keep, args.annotator)
    except RelabelError as error:
        _fail(str(error))

    _write_jsonl(args.annotations, seeds)
    _write_jsonl(args.pool, blank_labels(pool, plan.redo_ids))

    print(f"\n[relabel] seed  : {len(seeds)} label dipertahankan -> {args.annotations}")
    print(f"[relabel] kolam : {len(plan.redo)} label dikosongkan -> {args.pool}")
    print("\nLangkah berikutnya:")
    print("  1. Baca ulang context/11-annotation-rubric.md bagian 2-5.")
    print("  2. streamlit run ml/annotate.py   (lanjut otomatis di review yang kosong)")
    print("  3. python -m ml.build_dataset sync")
    print("  4. python -m ml.build_dataset gold")


def parse_args() -> argparse.Namespace:
    parser = argparse.ArgumentParser(description="Susun antrean pelabelan ulang")
    parser.add_argument("--pool", type=Path, default=POOL_PATH)
    parser.add_argument("--source", type=Path, default=SOURCE_CSV)
    parser.add_argument("--annotations", type=Path, default=ANNOTATIONS_PATH)
    sub = parser.add_subparsers(dest="command", required=True)

    p_plan = sub.add_parser("plan", help="tampilkan rencana tanpa menulis apa pun")
    p_plan.set_defaults(func=command_plan)

    p_apply = sub.add_parser("apply", help="tulis seed anotasi dan kosongkan sisanya")
    p_apply.add_argument("--annotator", required=True, help="nama pelabel pass pertama")
    p_apply.add_argument("--force", action="store_true", help="timpa annotations.jsonl yang ada")
    p_apply.set_defaults(func=command_apply)

    return parser.parse_args()


def main() -> None:
    args = parse_args()
    args.func(args)


if __name__ == "__main__":
    main()
