"""Ukur seberapa konsisten label anotasi - prasyarat sebelum angka model berarti.

Kesepakatan anotator adalah **plafon** performa model: kalau dua kali pelabelan
atas review yang sama hanya cocok 70%, model yang mencapai F1 0.70 sudah mepet
langit-langit, bukan sedang gagal. Tanpa angka ini hasil evaluasi mana pun tidak
bisa ditafsirkan - dan rubrik mewajibkannya masuk lampiran proposal
(`context/11-annotation-rubric.md` bagian 7).

Dua langkah:

    python -m ml.calibration sample                 # batch tanpa label -> dilabeli ulang
    python -m ml.calibration score                  # bandingkan dengan label pertama

Berdua (kappa antar-anotator) maupun sendirian (test-retest, beri jeda >=30 menit
sebelum melabeli ulang) memakai perintah yang sama.
"""

from __future__ import annotations

import argparse
import json
import random
import sys
from collections import Counter
from dataclasses import dataclass, field
from pathlib import Path
from typing import Any

# sklearn menarik pandas; jangan impor torch di modul ini (lihat ml/evaluate.py).
from sklearn.metrics import cohen_kappa_score

REPO_ROOT = Path(__file__).resolve().parent.parent
sys.path.insert(0, str(REPO_ROOT))

from ml.dataset_io import ID2LABEL, RAGU, normalize_label  # noqa: E402

POOL_PATH = REPO_ROOT / "data" / "to_label.jsonl"
BATCH_PATH = REPO_ROOT / "data" / "calibration" / "batch.jsonl"
DEFAULT_SIZE = 100
DEFAULT_SEED = 20260818

AUDIT_FIELDS = ("annotated_by", "annotated_at")
CLASS_NAMES = (ID2LABEL[0], ID2LABEL[1], RAGU)

# Ambang dari context/11-annotation-rubric.md bagian 7.
MATCH_CONTINUE = 0.85
MATCH_SHARPEN = 0.70


class CalibrationError(ValueError):
    """Batch kalibrasi tidak bisa dibandingkan apa adanya."""


@dataclass(frozen=True)
class AgreementReport:
    """Hasil perbandingan dua kali pelabelan atas review yang sama."""

    compared: int
    percent_match: float
    kappa: float
    matrix: Counter = field(default_factory=Counter)
    disagreements: list[dict[str, Any]] = field(default_factory=list)

    @property
    def verdict(self) -> str:
        if self.percent_match >= MATCH_CONTINUE:
            return "lanjut"
        if self.percent_match >= MATCH_SHARPEN:
            return "tajamkan"
        return "berhenti"


def _class_name(label: int | str) -> str:
    return RAGU if label == RAGU else ID2LABEL[label]


# --------------------------------------------------------------------------
# Ambil sampel
# --------------------------------------------------------------------------


def sample_batch(pool: list[dict[str, Any]], size: int, seed: int) -> list[dict[str, Any]]:
    """Ambil `size` review berlabel, kosongkan labelnya, acak urutannya.

    Label pass pertama dan jejak anotatornya sengaja dibuang: kalau sempat
    terbaca saat pelabelan ulang, angka kesepakatan yang keluar mengukur ingatan,
    bukan ketajaman rubrik. Urutan ikut diacak karena urutan asli pun petunjuk.
    """
    if size <= 0:
        raise CalibrationError(f"ukuran batch harus positif, diminta {size}")

    labeled = [row for row in pool if normalize_label(row.get("label")) is not None]
    if len(labeled) < size:
        raise CalibrationError(
            f"kolam hanya {len(labeled)} review berlabel, diminta {size}. "
            "Labeli lebih dulu atau kecilkan --size."
        )

    chosen = random.Random(seed).sample(labeled, size)
    return [
        {**{key: value for key, value in row.items() if key not in AUDIT_FIELDS}, "label": None}
        for row in chosen
    ]


# --------------------------------------------------------------------------
# Bandingkan
# --------------------------------------------------------------------------


def _index_first_pass(first: list[dict[str, Any]]) -> dict[str, dict[str, Any]]:
    return {
        row["review_id"]: row
        for row in first
        if normalize_label(row.get("label")) is not None
    }


def _second_pass_label(row: dict[str, Any], position: int) -> int | str:
    label = normalize_label(row.get("label"))
    if label is None:
        raise CalibrationError(
            f"baris ke-{position} ({row.get('review_id')}) belum dilabeli. "
            "Selesaikan seluruh batch sebelum menghitung kesepakatan."
        )
    return label


def agreement(first: list[dict[str, Any]], second: list[dict[str, Any]]) -> AgreementReport:
    """Bandingkan pelabelan kedua terhadap pelabelan pertama, review per review.

    `first` adalah kolam penuh (`data/to_label.jsonl`); hanya review yang muncul
    di `second` yang ikut dihitung.
    """
    if not second:
        raise CalibrationError("batch kalibrasi kosong - tidak ada yang dibandingkan")

    indexed = _index_first_pass(first)
    matrix: Counter = Counter()
    disagreements: list[dict[str, Any]] = []
    agreed = 0

    for position, row in enumerate(second, start=1):
        review_id = row.get("review_id")
        original = indexed.get(review_id)
        if original is None:
            raise CalibrationError(
                f"review_id {review_id!r} tidak ada di pass pertama, atau belum "
                "dilabeli di sana - batch tidak sepadan dengan kolamnya."
            )

        first_label = normalize_label(original["label"])
        second_label = _second_pass_label(row, position)
        first_name, second_name = _class_name(first_label), _class_name(second_label)
        matrix[(first_name, second_name)] += 1

        if first_label == second_label:
            agreed += 1
        else:
            disagreements.append(
                {
                    "review_id": review_id,
                    "text": original["text"],
                    "first": first_name,
                    "second": second_name,
                }
            )

    names_first = [pair[0] for pair, count in matrix.items() for _ in range(count)]
    names_second = [pair[1] for pair, count in matrix.items() for _ in range(count)]

    return AgreementReport(
        compared=len(second),
        percent_match=agreed / len(second),
        kappa=float(cohen_kappa_score(names_first, names_second)),
        matrix=matrix,
        disagreements=disagreements,
    )


# --------------------------------------------------------------------------
# Berkas
# --------------------------------------------------------------------------


def _fail(message: str) -> None:
    print(f"[kalibrasi] {message}", file=sys.stderr)
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


# --------------------------------------------------------------------------
# Perintah
# --------------------------------------------------------------------------


def command_sample(args: argparse.Namespace) -> None:
    pool = _read_jsonl(args.pool)
    try:
        batch = sample_batch(pool, args.size, args.seed)
    except CalibrationError as error:
        _fail(str(error))

    _write_jsonl(args.out, batch)
    print(f"[kalibrasi] {len(batch)} review -> {args.out}")
    print("[kalibrasi] Labeli ulang field 'label' jadi 0, 1, atau ragu.")
    print(f"[kalibrasi] JANGAN buka {args.pool} sampai selesai - itu kunci jawabannya.")
    print(f"[kalibrasi] Lalu : python -m ml.calibration score --batch {args.out}")


def _print_matrix(matrix: Counter) -> None:
    print("\nMatriks kesepakatan (baris = pass 1, kolom = pass 2):")
    print(f"{'':>8}" + "".join(f"{name:>8}" for name in CLASS_NAMES))
    for first_name in CLASS_NAMES:
        cells = "".join(f"{matrix[(first_name, second)]:>8}" for second in CLASS_NAMES)
        print(f"{first_name:>8}{cells}")


def _print_disagreements(disagreements: list[dict[str, Any]], limit: int) -> None:
    if not disagreements:
        return
    print(f"\nTidak sepakat ({len(disagreements)}) - di sinilah rubrik perlu dipertajam:")
    for item in disagreements[:limit]:
        text = item["text"].replace("\n", " ")
        if len(text) > 110:
            text = text[:110] + "..."
        print(f"  {item['review_id']}  {item['first']:>4} -> {item['second']:<4}  {text}")
    if len(disagreements) > limit:
        print(f"  ... {len(disagreements) - limit} lagi (naikkan --show untuk melihat semua)")


VERDICT_MESSAGES = {
    "lanjut": (
        "LANJUT. Rubrik cukup tajam. Cantumkan angka ini di lampiran proposal, "
        "lalu pakai sebagai plafon saat membaca hasil model."
    ),
    "tajamkan": (
        "TAJAMKAN. Ada definisi yang kabur. Perbaiki bagian rubrik yang paling "
        "sering jadi sumber beda di bawah, labeli ulang review yang terdampak, "
        "baru lanjut."
    ),
    "berhenti": (
        "BERHENTI. Tugasnya belum terdefinisi. Melatih model di atas label ini "
        "hanya memproduksi kebisingan - perbaiki rubrik lebih dulu."
    ),
}


def print_report(report: AgreementReport, show: int) -> None:
    print("=" * 70)
    print(f"KALIBRASI - {report.compared} review dilabeli dua kali")
    print("=" * 70)
    print(f"Cocok       : {report.percent_match:.1%}  (rubrik: >=85% lanjut, <70% berhenti)")
    print(f"Cohen kappa : {report.kappa:.3f}  (>=0.6 substansial, <0.4 lemah)")
    _print_matrix(report.matrix)
    _print_disagreements(report.disagreements, show)
    print(f"\n{VERDICT_MESSAGES[report.verdict]}")


def command_score(args: argparse.Namespace) -> None:
    pool = _read_jsonl(args.pool)
    batch = _read_jsonl(args.batch)
    try:
        report = agreement(pool, batch)
    except CalibrationError as error:
        _fail(str(error))
    print_report(report, args.show)


def parse_args() -> argparse.Namespace:
    parser = argparse.ArgumentParser(description="Ukur kesepakatan anotasi")
    sub = parser.add_subparsers(dest="command", required=True)

    p_sample = sub.add_parser("sample", help="buat batch tanpa label untuk dilabeli ulang")
    p_sample.add_argument("--pool", type=Path, default=POOL_PATH)
    p_sample.add_argument("--out", type=Path, default=BATCH_PATH)
    p_sample.add_argument("--size", type=int, default=DEFAULT_SIZE)
    p_sample.add_argument("--seed", type=int, default=DEFAULT_SEED)
    p_sample.set_defaults(func=command_sample)

    p_score = sub.add_parser("score", help="bandingkan batch dengan label pertama")
    p_score.add_argument("--pool", type=Path, default=POOL_PATH)
    p_score.add_argument("--batch", type=Path, default=BATCH_PATH)
    p_score.add_argument("--show", type=int, default=25, help="jumlah ketidaksepakatan dicetak")
    p_score.set_defaults(func=command_score)

    return parser.parse_args()


def main() -> None:
    args = parse_args()
    args.func(args)


if __name__ == "__main__":
    main()
