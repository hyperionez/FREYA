"""Linter rubrik anotasi - menegakkan aturan `context/11-annotation-rubric.md`
yang bisa diperiksa mekanis dari pasangan (teks, label).

    python -m ml.check_rubric annotations/annotations_mt.jsonl
    python -m ml.check_rubric annotations/*.jsonl

Latar: pada 500 review yang dilabeli tiga anotator, kappa berpasangan jatuh di
0.033-0.061 dan sepakat bulat hanya 24%. Penyebabnya bukan rubrik yang kabur,
melainkan urutan keputusan section 5 yang tidak dijalankan - keluhan eksplisit
dilabeli bot padahal langkah 2 memerintahkan asli. Aturan itu mekanis, jadi
seharusnya dijaga alat, bukan diserahkan ke disiplin manusia di jam keempat
melabeli.

Yang diperiksa:

- **Pelanggaran** (section 5 langkah 2) - ada keluhan tapi dilabeli bot. Ini
  keras: langkah 2 berhenti di `0`, tidak ada ruang tafsir.
- **Rasio ragu** (section 2) - di luar rentang yang diturunkan dari bentuk data.
  Terlalu rendah berarti review ambigu dipaksa dijawab.
- **Catatan** (section 4) - review pendek dilabeli bot. Bukan pelanggaran:
  review pendek BISA bot, tapi ">=2 sinyal section 3" sulit terpenuhi dalam
  teks sependek itu, jadi barisnya layak ditinjau ulang.
- **Catatan** (section 5 langkah 2) - ada keluhan tapi dilabeli ragu. Langkah 2
  memerintahkan asli, bukan ragu. Tetap bukan pelanggaran keras karena langkah 1
  mendahuluinya: keluhan di dalam teks rusak atau terpotong memang jatuh ke ragu.

Leksikon keluhannya sengaja beresolusi tinggi, bukan lengkap: alat ini menuduh
orang melanggar rubrik, jadi salah-tuduh lebih mahal daripada terlewat. Kata
bermakna ganda ("lama" bisa "lama pemakaian" yang justru penanda asli menurut
langkah 3, "kurang" bisa "kurang lebih") sengaja TIDAK dimasukkan. Angka yang
keluar karena itu adalah **batas bawah** jumlah pelanggaran sebenarnya.
"""

from __future__ import annotations

import argparse
import re
import sys
from collections import defaultdict
from pathlib import Path
from typing import Any

REPO_ROOT = Path(__file__).resolve().parent.parent
sys.path.insert(0, str(REPO_ROOT))

from ml.dataset_io import RAGU, load_records  # noqa: E402

# Rentang dari rubrik section 2, diturunkan dari bentuk data: 34% kolam adalah
# review pendek tanpa keluhan, yang seluruhnya jatuh ke langkah 5. Target lama
# 10-20% ditetapkan tanpa melihat distribusi panjang dan sudah dicabut. Hitung
# ulang kalau kolam datanya berganti.
RAGU_MIN = 0.20
RAGU_MAKS = 0.40

# Di bawah panjang ini, ">=2 sinyal section 3" praktis tidak bisa dibuktikan.
# Angkanya dari data: median review yang anotatornya terbelah adalah 58 karakter.
PANJANG_PENDEK = 60

# Hanya penanda yang maknanya tunggal di konteks review marketplace.
KELUHAN = re.compile(
    r"\b("
    r"kecewa|mengecewakan|menyesal|komplain|"
    r"rusak|cacat|sobek|bocor|penyok|retak|patah|pecah|bengkok|lecet|"
    r"jelek|buruk|palsu|luntur|zonk|basi|kadaluarsa|kedaluwarsa|expired|"
    r"lambat|telat|"
    r"nipu|menipu|penipu|"
    r"tidak sesuai|ga sesuai|gak sesuai|nggak sesuai|"
    r"tidak layak|tidak berfungsi|kurang ajar|"
    # "salah" hanya dihitung kalau objeknya jelas barang atau pengiriman;
    # "salah" telanjang terlalu sering muncul di kalimat non-keluhan.
    r"salah (kirim|barang|warna|ukuran|item)|barang (yang|yg) salah|"
    r"(tidak|ga|gak|nggak) bisa (dipakai|digunakan)|gabisa dipakai"
    r")\b",
    re.IGNORECASE,
)

# "bau" dan "kotor" butuh penjagaan ekstra: "bau harum" bukan keluhan. Dipisah
# supaya leksikon utama tetap terbaca sebagai daftar datar.
KELUHAN_KONDISI = re.compile(
    r"\b(bau|kotor)\b(?!\s+(harum|wangi|enak|sedap))",
    re.IGNORECASE,
)

# "rapih tidak cacat" adalah pujian. Tanpa cek ini, pencocokan kata polos
# membalik maknanya dan alat melaporkan pelanggaran yang tidak ada.
NEGASI = re.compile(r"\b(tidak|tdk|ga|gak|nggak|enggak|bukan|belum|tanpa|no)\s+$", re.IGNORECASE)

JANGKAUAN_NEGASI = 15


def mengandung_keluhan(text: str) -> bool:
    """Apakah teks memuat keluhan yang tidak dinegasikan."""
    for pola in (KELUHAN, KELUHAN_KONDISI):
        for cocok in pola.finditer(text):
            awalan = text[max(0, cocok.start() - JANGKAUAN_NEGASI) : cocok.start()]
            if NEGASI.search(awalan):
                continue
            return True
    return False


def _ringkas(text: str, batas: int = 90) -> str:
    rapat = " ".join(text.split())
    return rapat if len(rapat) <= batas else rapat[:batas] + "..."


def check_records(records: list[dict[str, Any]]) -> dict[str, Any]:
    """Periksa record beranotasi terhadap aturan rubrik yang mekanis."""
    pelanggaran: list[dict[str, Any]] = []
    catatan_pendek: list[dict[str, Any]] = []
    catatan_keluhan_ragu: list[dict[str, Any]] = []
    per_anotator: dict[str, dict[str, int]] = defaultdict(
        lambda: {"total": 0, "pelanggaran": 0, "ragu": 0}
    )

    jumlah_ragu = 0
    jumlah_berlabel = 0

    for record in records:
        label = record.get("label")
        if label is None:
            continue

        text = record.get("text") or ""
        anotator = record.get("annotated_by") or "(tanpa nama)"
        jumlah_berlabel += 1
        per_anotator[anotator]["total"] += 1

        if label == RAGU:
            jumlah_ragu += 1
            per_anotator[anotator]["ragu"] += 1
            if mengandung_keluhan(text):
                catatan_keluhan_ragu.append(
                    {
                        "review_id": record.get("review_id"),
                        "annotated_by": anotator,
                        "text": _ringkas(text),
                        "aturan": "section 5 langkah 2 mengarah ke asli, bukan ragu - tinjau ulang",
                    }
                )
            continue

        if label == 1 and mengandung_keluhan(text):
            pelanggaran.append(
                {
                    "review_id": record.get("review_id"),
                    "annotated_by": anotator,
                    "text": _ringkas(text),
                    "aturan": "section 5 langkah 2: ada keluhan -> wajib asli",
                }
            )
            per_anotator[anotator]["pelanggaran"] += 1

        if label == 1 and len(" ".join(text.split())) < PANJANG_PENDEK:
            catatan_pendek.append(
                {
                    "review_id": record.get("review_id"),
                    "annotated_by": anotator,
                    "text": _ringkas(text),
                    "aturan": "section 4: pendek bukan bukti bot - tinjau ulang",
                }
            )

    rasio = jumlah_ragu / jumlah_berlabel if jumlah_berlabel else 0.0
    return {
        "total": len(records),
        "berlabel": jumlah_berlabel,
        "pelanggaran": pelanggaran,
        "catatan_pendek": catatan_pendek,
        "catatan_keluhan_ragu": catatan_keluhan_ragu,
        "ragu": {
            "jumlah": jumlah_ragu,
            "rasio": rasio,
            "dalam_target": RAGU_MIN <= rasio <= RAGU_MAKS,
        },
        "per_anotator": dict(per_anotator),
    }


def check_file(path: str | Path) -> dict[str, Any]:
    return check_records(load_records(path))


def format_report(path: str | Path, laporan: dict[str, Any], contoh: int = 5) -> str:
    baris = [
        "=" * 70,
        f"{Path(path).name}  -  {laporan['berlabel']} baris berlabel dari {laporan['total']}",
        "=" * 70,
    ]

    ragu = laporan["ragu"]
    tanda = "OK" if ragu["dalam_target"] else "DI LUAR TARGET"
    baris.append(
        f"Rasio ragu: {ragu['rasio']:.1%} ({ragu['jumlah']} baris) - "
        f"target {RAGU_MIN:.0%}-{RAGU_MAKS:.0%} [{tanda}]"
    )

    n = len(laporan["pelanggaran"])
    baris.append(f"Pelanggaran section 5 langkah 2: {n}")
    for p in laporan["pelanggaran"][:contoh]:
        baris.append(f'  - [{p["annotated_by"]}] {p["review_id"]}: "{p["text"]}"')
    if n > contoh:
        baris.append(f"  ... {n - contoh} lagi")

    baris.append(f"Catatan review pendek dilabeli bot: {len(laporan['catatan_pendek'])}")
    baris.append(f"Catatan keluhan dilabeli ragu: {len(laporan['catatan_keluhan_ragu'])}")

    if len(laporan["per_anotator"]) > 1:
        baris.append("Per anotator:")
        for nama, s in sorted(laporan["per_anotator"].items()):
            r = s["ragu"] / s["total"] if s["total"] else 0.0
            baris.append(
                f"  {nama:12s} n={s['total']:4d}  pelanggaran={s['pelanggaran']:3d}  ragu={r:.1%}"
            )

    return "\n".join(baris)


def main() -> int:
    parser = argparse.ArgumentParser(description=__doc__.splitlines()[0])
    parser.add_argument("paths", nargs="+", help="berkas anotasi .jsonl")
    parser.add_argument("--contoh", type=int, default=5, help="jumlah contoh pelanggaran dicetak")
    args = parser.parse_args()

    ada_pelanggaran = False
    for path in args.paths:
        laporan = check_file(path)
        print(format_report(path, laporan, args.contoh))
        print()
        if laporan["pelanggaran"]:
            ada_pelanggaran = True

    return 1 if ada_pelanggaran else 0


if __name__ == "__main__":
    raise SystemExit(main())
