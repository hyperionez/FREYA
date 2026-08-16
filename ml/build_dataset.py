"""Bangun dataset latih deteksi review bot (Bahasa Indonesia).

Tiga tahap, dijalankan terpisah supaya tahap mahal (generasi LLM) tidak
terulang saat tahap lain diperbaiki:

    python -m ml.build_dataset real  --input data/raw/reviews.csv --text-field review
    python -m ml.build_dataset synth --n 1500
    python -m ml.build_dataset pack
    python -m ml.build_dataset gold   # setelah to_label.jsonl dilabeli tangan

Jalankan dari root repo (bukan dari dalam ml/), supaya impor `ml.*` ketemu.

Keluaran akhir:
    data/train.jsonl          -> latih (label 0 = asli, 1 = bot)
    data/test_synthetic.jsonl -> uji in-distribution (holdout sintetik)
    data/to_label.jsonl       -> kolam review asli untuk DILABELI TANGAN
    data/test_real.jsonl      -> gold set dari label manusia (tahap `gold`)

`pack` aman dijalankan ulang: label manual yang sudah ada di to_label.jsonl
dibawa serta berdasarkan teksnya, jadi menaikkan TO_LABEL_SIZE tidak
menghanguskan kerja anotasi.
"""

from __future__ import annotations

import argparse
import json
import os
import random
import sys
import time
from pathlib import Path
from typing import Any, Iterator

from ml.anonymize import anonymize, normalize_for_dedup
from ml.synth_prompts import BOT_STYLES, build_prompt

DATA_DIR = Path("data")
INTERIM_DIR = DATA_DIR / "interim"
REAL_PATH = INTERIM_DIR / "real.jsonl"
SYNTH_PATH = INTERIM_DIR / "synth.jsonl"
TRAIN_PATH = DATA_DIR / "train.jsonl"
TEST_SYNTHETIC_PATH = DATA_DIR / "test_synthetic.jsonl"
TO_LABEL_PATH = DATA_DIR / "to_label.jsonl"
GOLD_PATH = DATA_DIR / "test_real.jsonl"

MIN_CHARS = 15
MAX_CHARS = 600
# Free tier membatasi JUMLAH REQUEST (20/hari/model), bukan jumlah teks, jadi
# batch besar jauh lebih hemat kuota daripada banyak batch kecil.
SYNTH_BATCH_SIZE = 100
MAX_UNPRODUCTIVE_BATCHES = 4
RETRY_BACKOFF_SECONDS = 5
SYNTH_HOLDOUT_RATIO = 0.15
# Kolam label manual. Dinaikkan 250 -> 500 untuk mengejar target GO/NO-GO
# (>=400 label). Seed tetap, jadi 250 pertama identik dengan kolam lama.
TO_LABEL_SIZE = 500
RANDOM_SEED = 42
DEFAULT_GEMINI_MODEL = "gemini-3.5-flash"
# Dicoba berurutan saat kuota model sebelumnya habis; tiap model punya jatah sendiri.
FALLBACK_MODELS = (
    "gemini-3.5-flash",
    "gemini-3.5-flash-lite",
    "gemini-3.1-flash-lite",
    "gemini-3.6-flash",
    "gemini-3.7-flash",
)

LABEL_ASLI = 0
LABEL_BOT = 1
LABEL_RAGU = "ragu"  # dibuang saat membangun gold set


# --------------------------------------------------------------------------
# Tahap 1: review asli dari dataset publik
# --------------------------------------------------------------------------


def command_real(args: argparse.Namespace) -> None:
    input_path = Path(args.input)
    if not input_path.exists():
        _fail(f"File tidak ditemukan: {input_path}. Unduh dulu (lihat data/README.md).")

    store_names = tuple(args.store_names.split(",")) if args.store_names else ()
    rows = list(_read_any(input_path, args.text_field))
    if not any(isinstance(row, str) and row.strip() for row in rows):
        available = _available_fields(input_path)
        hint = f" Field tersedia: {available}." if available else ""
        _fail(
            f"Tidak ada teks terbaca dari {len(rows)} baris. "
            f"--text-field sekarang '{args.text_field}'.{hint}"
        )

    records = []
    seen: set[str] = set()
    for raw_text in rows:
        record = _make_record(raw_text, LABEL_ASLI, "hf_ecommerce_id", None, store_names, seen)
        if record:
            records.append(record)
        if args.limit and len(records) >= args.limit:
            break

    if not records:
        _fail(
            f"{len(rows)} baris terbaca tapi semuanya tersaring habis "
            f"(panjang di luar {MIN_CHARS}-{MAX_CHARS} karakter, atau duplikat). "
            "Tidak ada yang ditulis."
        )

    _write_jsonl(REAL_PATH, _reindex(records, "real"))
    print(f"[real] {len(rows)} baris masuk -> {len(records)} review bersih -> {REAL_PATH}")


# --------------------------------------------------------------------------
# Tahap 2: review bot sintetik via Gemini
# --------------------------------------------------------------------------


def command_synth(args: argparse.Namespace) -> None:
    dotenv_ready = _load_env_file()
    api_key = os.getenv("GEMINI_API_KEY")
    if not api_key and not dotenv_ready:
        _fail(
            "GEMINI_API_KEY kosong DAN paket python-dotenv belum terpasang, jadi .env "
            "tidak pernah dibaca. Pasang dulu: pip install -r requirements.txt"
        )
    if not api_key:
        _fail(
            "GEMINI_API_KEY kosong. Cek .env di root repo berisi baris "
            "GEMINI_API_KEY=xxx (tanpa tanda kutip, tanpa spasi sekitar '=')."
        )

    client = _gemini_client(api_key)
    per_style = max(1, args.n // len(BOT_STYLES))

    # Kuota free tier dihitung per model per hari, jadi kalau satu model habis
    # kita pindah ke model berikutnya alih-alih menyerah.
    models = [args.model] + [m for m in FALLBACK_MODELS if m != args.model]
    model_idx = 0

    records, seen = _resume_synth(args.resume)
    done_per_style = _count_by_style(records)

    for style in BOT_STYLES:
        collected = done_per_style.get(style["name"], 0)
        if collected:
            print(f"[synth] {style['name']}: {collected} sudah ada, lanjut dari sini")
        unproductive = 0
        while collected < per_style:
            batch = min(SYNTH_BATCH_SIZE, per_style - collected)
            texts, quota_exhausted = _generate_batch(client, models[model_idx], style, batch)

            if quota_exhausted and model_idx + 1 < len(models):
                model_idx += 1
                print(f"  > kuota habis, pindah ke model '{models[model_idx]}'")
                continue

            accepted = 0
            for text in texts:
                record = _make_record(text, LABEL_BOT, "llm_synthetic", style["name"], (), seen)
                if record:
                    records.append(record)
                    collected += 1
                    accepted += 1

            # Batch tak produktif = API gagal ATAU semua teks tersaring habis
            # (duplikat/panjang). Keduanya bikin `collected` mandek, jadi tanpa
            # batas ini gaya bertekstur sempit seperti generic_short bisa
            # memutar `while` selamanya.
            if accepted:
                unproductive = 0
                continue
            unproductive += 1
            if unproductive >= MAX_UNPRODUCTIVE_BATCHES:
                print(f"  ! '{style['name']}' berhenti: {unproductive} batch nihil berturut-turut")
                break
            wait = RETRY_BACKOFF_SECONDS * unproductive
            print(f"  ! batch nihil ({unproductive}/{MAX_UNPRODUCTIVE_BATCHES}), ulang dalam {wait}s")
            time.sleep(wait)
        print(f"[synth] {style['name']}: {collected} review")

    if not records:
        _fail(
            "Tidak ada review sintetik yang berhasil dihasilkan; file tidak ditulis. "
            f"Baca baris '!' di atas: biasanya nama model salah (--model {args.model}) "
            "atau kuota API habis."
        )

    _write_jsonl(SYNTH_PATH, _reindex(records, "syn"))
    print(f"[synth] total {len(records)} review bot -> {SYNTH_PATH}")


def _load_env_file() -> bool:
    """Muat .env dari root repo. Tanpa ini os.getenv tidak melihat isi .env.

    Kembalikan False kalau python-dotenv belum terpasang: tanpa paket itu .env
    tidak pernah dibaca sama sekali, dan pemanggil perlu tahu bedanya supaya
    pesan errornya tidak menyalahkan .env yang sebenarnya sudah benar.
    """
    try:
        from dotenv import load_dotenv
    except ImportError:
        return False  # boleh saja kalau user meng-export var secara manual
    load_dotenv()
    return True


def _gemini_client(api_key: str):
    try:
        from google import genai
    except ImportError:
        _fail("Paket google-genai belum terpasang. Jalankan: pip install -r requirements.txt")
    return genai.Client(api_key=api_key)


def _resume_synth(resume: bool) -> tuple[list[dict[str, Any]], set[str]]:
    """Muat hasil generasi sebelumnya supaya kuota yang sudah terpakai tidak hangus."""
    if not resume:
        return [], set()
    existing = _read_jsonl(SYNTH_PATH)
    if existing:
        print(f"[synth] resume: {len(existing)} review dari {SYNTH_PATH}")
    return existing, {normalize_for_dedup(row["text"]) for row in existing}


def _count_by_style(records: list[dict[str, Any]]) -> dict[str, int]:
    counts: dict[str, int] = {}
    for record in records:
        name = record.get("style")
        if name:
            counts[name] = counts.get(name, 0) + 1
    return counts


def _generate_batch(
    client, model: str, style: dict[str, str], count: int
) -> tuple[list[str], bool]:
    """Kembalikan (teks, kuota_habis). Flag kedua memicu pindah model, bukan menyerah."""
    prompt = build_prompt(style, count)
    try:
        response = client.models.generate_content(model=model, contents=prompt)
    except Exception as exc:  # noqa: BLE001 - laporkan, jangan hentikan seluruh run
        detail = str(exc)
        print(f"  ! panggilan Gemini gagal ({exc.__class__.__name__}): {detail[:150]}")
        return [], "RESOURCE_EXHAUSTED" in detail
    return _parse_json_array(response.text or ""), False


def _parse_json_array(raw: str) -> list[str]:
    """Ambil array JSON dari respons, toleran terhadap pembungkus blok kode."""
    text = raw.strip()
    start, end = text.find("["), text.rfind("]")
    if start == -1 or end == -1 or end <= start:
        print("  ! respons tidak memuat array JSON, dilewati")
        return []
    body = text[start : end + 1]
    try:
        parsed = json.loads(body)
    except json.JSONDecodeError:
        return _parse_loose_lines(body)
    return [item for item in parsed if isinstance(item, str)]


def _parse_loose_lines(body: str) -> list[str]:
    """Selamatkan respons yang menulis satu review per baris TANPA tanda kutip.

    Model kelas 'lite' kerap mengabaikan permintaan JSON dan membalas
    `[<newline>review satu,<newline>review dua]`. Membuang batch seperti ini
    berarti membakar jatah request harian percuma padahal teksnya masih layak.
    """
    items: list[str] = []
    for line in body.strip().lstrip("[").rstrip("]").splitlines():
        cleaned = line.strip().rstrip(",").strip()
        if len(cleaned) >= 2 and cleaned[0] == cleaned[-1] == '"':
            cleaned = cleaned[1:-1].strip()
        if cleaned:
            items.append(cleaned)
    if items:
        print(f"  > respons bukan JSON ketat, diselamatkan {len(items)} baris")
    return items


# --------------------------------------------------------------------------
# Tahap 3: gabung, seimbangkan, pecah
# --------------------------------------------------------------------------


def command_pack(_: argparse.Namespace) -> None:
    real = _read_jsonl(REAL_PATH)
    synth = _read_jsonl(SYNTH_PATH)
    if not real or not synth:
        _fail(f"Butuh {REAL_PATH} dan {SYNTH_PATH}. Jalankan tahap 'real' dan 'synth' dulu.")

    rng = random.Random(RANDOM_SEED)
    rng.shuffle(real)
    rng.shuffle(synth)

    holdout_size = int(len(synth) * SYNTH_HOLDOUT_RATIO)
    synth_holdout, synth_train = synth[:holdout_size], synth[holdout_size:]

    # Sisihkan kolam label manual SEBELUM menyeimbangkan, supaya review yang
    # dilabeli tangan tidak pernah ikut terlatih (mencegah kebocoran).
    to_label_size = min(TO_LABEL_SIZE, len(real) // 2)
    to_label_pool, real_remaining = real[:to_label_size], real[to_label_size:]

    n = min(len(real_remaining), len(synth_train))
    if n == 0:
        _fail("Data tidak cukup untuk menyeimbangkan kelas. Tambah review asli atau sintetik.")
    train = real_remaining[:n] + synth_train[:n]
    rng.shuffle(train)

    rows = [_to_label_row(r, i) for i, r in enumerate(to_label_pool, 1)]
    rows, kept, orphaned = _carry_over_labels(rows, _read_jsonl(TO_LABEL_PATH))

    _write_jsonl(TRAIN_PATH, train)
    _write_jsonl(TEST_SYNTHETIC_PATH, synth_holdout)
    _write_jsonl(TO_LABEL_PATH, rows)

    print(f"[pack] train            : {len(train)} ({n} asli + {n} bot) -> {TRAIN_PATH}")
    print(f"[pack] test_synthetic   : {len(synth_holdout)} -> {TEST_SYNTHETIC_PATH}")
    print(f"[pack] to_label (MANUAL): {len(rows)} -> {TO_LABEL_PATH}")
    if kept:
        sisa = len(rows) - kept
        print(f"[pack]   label lama dipertahankan: {kept}, sisa belum dilabeli: {sisa}")
    if orphaned:
        print(
            f"[pack] ! {orphaned} label lama TIDAK ketemu di kolam baru dan hilang. "
            "Pulihkan to_label.jsonl dari git sebelum lanjut.",
            file=sys.stderr,
        )
    if n < 500:
        print(f"[pack] ! hanya {n} per kelas. Target sehat >= 750 per kelas.")


def _carry_over_labels(
    rows: list[dict[str, Any]], previous: list[dict[str, Any]]
) -> tuple[list[dict[str, Any]], int, int]:
    """Bawa label manual dari to_label.jsonl lama ke kolam yang baru dibentuk.

    Dicocokkan lewat teks yang dinormalisasi, bukan review_id, karena id
    bersifat posisional -- menaikkan TO_LABEL_SIZE menggeser penomoran.
    """
    by_text = {
        normalize_for_dedup(row["text"]): row["label"]
        for row in previous
        if row.get("text") and row.get("label") is not None
    }
    if not by_text:
        return rows, 0, 0

    merged, kept = [], 0
    for row in rows:
        label = by_text.pop(normalize_for_dedup(row["text"]), None)
        if label is None:
            merged.append(row)
            continue
        merged.append({**row, "label": label})
        kept += 1
    return merged, kept, len(by_text)


def _to_label_row(record: dict[str, Any], index: int) -> dict[str, Any]:
    """Bentuk baris untuk pelabelan tangan.

    Nama field sengaja mengikuti tests/fixtures/sample_stores.json supaya
    hasil labelnya langsung cocok dengan pipeline yang sudah ada.
    """
    return {
        "review_id": f"t-{index:04d}",
        "store_id": None,  # isi tangan kalau sumbernya punya info toko
        "text": record["text"],
        "posted_at": None,
        "reviewer_rating": None,
        "label": None,  # 0 = asli, 1 = bot, "ragu" = buang saat evaluasi
    }


# --------------------------------------------------------------------------
# Tahap 4: bekukan label manusia jadi gold set
# --------------------------------------------------------------------------


def command_gold(_: argparse.Namespace) -> None:
    """Ubah label manual jadi test set — satu-satunya ukuran jujur model.

    train.jsonl berlabel otomatis (real=asli, sintetik=bot), jadi tidak bisa
    dipakai membuktikan apa pun. Hanya label manusia di sini yang boleh
    dijadikan dasar klaim "fine-tuned mengalahkan heuristik".
    """
    rows = _read_jsonl(TO_LABEL_PATH)
    if not rows:
        _fail(f"{TO_LABEL_PATH} kosong. Jalankan 'pack' lalu labeli tangan dulu.")

    gold = [row for row in rows if row.get("label") in (LABEL_ASLI, LABEL_BOT)]
    ragu = sum(1 for row in rows if row.get("label") == LABEL_RAGU)
    belum = len(rows) - len(gold) - ragu
    if not gold:
        _fail(f"Belum ada label 0/1 di {TO_LABEL_PATH}.")

    bocor = _leaked_into_train(gold)
    if bocor:
        _fail(
            f"{bocor} baris gold set juga ada di {TRAIN_PATH}. Gold set yang bocor "
            "membuat evaluasi tidak sah. Jalankan 'pack' ulang lalu 'gold' lagi."
        )

    _write_jsonl(GOLD_PATH, gold)

    asli = sum(1 for row in gold if row["label"] == LABEL_ASLI)
    print(f"[gold] gold set : {len(gold)} ({asli} asli + {len(gold) - asli} bot) -> {GOLD_PATH}")
    print(f"[gold] dibuang  : {ragu} ragu, {belum} belum dilabeli")
    if len(gold) < 200:
        print(f"[gold] ! {len(gold)} baris terlalu sedikit; metrik per kelas akan goyah.")
    if ragu == 0:
        print(
            "[gold] ! nol label 'ragu'. Rubrik menargetkan 10-20% -- "
            "kasus ambigu yang dipaksa jadi 0/1 menambah noise ke gold set."
        )


def _leaked_into_train(gold: list[dict[str, Any]]) -> int:
    """Berapa baris gold set yang juga muncul di data latih."""
    train_keys = {
        normalize_for_dedup(row["text"]) for row in _read_jsonl(TRAIN_PATH) if row.get("text")
    }
    if not train_keys:
        return 0
    return sum(1 for row in gold if normalize_for_dedup(row["text"]) in train_keys)


# --------------------------------------------------------------------------
# Util
# --------------------------------------------------------------------------


def command_stats(_: argparse.Namespace) -> None:
    for path in (REAL_PATH, SYNTH_PATH, TRAIN_PATH, TEST_SYNTHETIC_PATH, TO_LABEL_PATH, GOLD_PATH):
        if not path.exists():
            print(f"{path}: belum ada")
            continue
        rows = _read_jsonl(path)
        labels: dict[Any, int] = {}
        for row in rows:
            labels[row.get("label")] = labels.get(row.get("label"), 0) + 1
        print(f"{path}: {len(rows)} baris, distribusi label {labels}")


def _make_record(
    raw_text: Any,
    label: int,
    source: str,
    style: str | None,
    store_names: tuple[str, ...],
    seen: set[str],
) -> dict[str, Any] | None:
    if not isinstance(raw_text, str):
        return None
    text = anonymize(raw_text, store_names)
    if not MIN_CHARS <= len(text) <= MAX_CHARS:
        return None
    key = normalize_for_dedup(text)
    if not key or key in seen:
        return None
    seen.add(key)
    return {"id": None, "text": text, "label": label, "source": source, "style": style}


def _reindex(records: list[dict[str, Any]], prefix: str) -> list[dict[str, Any]]:
    return [{**record, "id": f"{prefix}-{i:06d}"} for i, record in enumerate(records, 1)]


def _read_any(path: Path, text_field: str) -> Iterator[str]:
    suffix = path.suffix.lower()
    if suffix == ".jsonl":
        for line in path.read_text(encoding="utf-8").splitlines():
            if line.strip():
                yield json.loads(line).get(text_field, "")
    elif suffix == ".json":
        payload = json.loads(path.read_text(encoding="utf-8"))
        rows = payload if isinstance(payload, list) else payload.get("data", [])
        for row in rows:
            yield row.get(text_field, "") if isinstance(row, dict) else ""
    elif suffix == ".csv":
        import csv

        with path.open(encoding="utf-8", newline="") as handle:
            reader = csv.DictReader(handle)
            if reader.fieldnames and text_field not in reader.fieldnames:
                _fail(f"Kolom '{text_field}' tidak ada. Kolom tersedia: {reader.fieldnames}")
            for row in reader:
                yield row.get(text_field, "")
    else:
        _fail(f"Format '{suffix}' tidak didukung. Pakai .csv, .json, atau .jsonl.")


def _available_fields(path: Path) -> list[str] | None:
    """Nama field pada baris pertama, untuk pesan error yang bisa ditindaklanjuti."""
    suffix = path.suffix.lower()
    try:
        if suffix == ".jsonl":
            for line in path.read_text(encoding="utf-8").splitlines():
                if line.strip():
                    return list(json.loads(line).keys())
        elif suffix == ".json":
            payload = json.loads(path.read_text(encoding="utf-8"))
            rows = payload if isinstance(payload, list) else payload.get("data", [])
            if rows and isinstance(rows[0], dict):
                return list(rows[0].keys())
    except (json.JSONDecodeError, OSError, AttributeError):
        return None
    return None


def _read_jsonl(path: Path) -> list[dict[str, Any]]:
    if not path.exists():
        return []
    lines = path.read_text(encoding="utf-8").splitlines()
    return [json.loads(line) for line in lines if line.strip()]


def _write_jsonl(path: Path, records: list[dict[str, Any]]) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    with path.open("w", encoding="utf-8") as handle:
        for record in records:
            handle.write(json.dumps(record, ensure_ascii=False) + "\n")


def _fail(message: str) -> None:
    print(f"ERROR: {message}", file=sys.stderr)
    raise SystemExit(1)


def main() -> None:
    parser = argparse.ArgumentParser(
        description=__doc__, formatter_class=argparse.RawDescriptionHelpFormatter
    )
    sub = parser.add_subparsers(dest="command", required=True)

    p_real = sub.add_parser("real", help="olah review asli dari dataset publik")
    p_real.add_argument("--input", required=True, help="path .csv/.json/.jsonl hasil unduhan")
    p_real.add_argument("--text-field", default="review", help="nama kolom teks review")
    p_real.add_argument("--limit", type=int, default=3000, help="ambil maksimal N review bersih")
    p_real.add_argument("--store-names", default="", help="nama toko dipisah koma, untuk disensor")
    p_real.set_defaults(func=command_real)

    p_synth = sub.add_parser("synth", help="generate review bot sintetik via Gemini")
    p_synth.add_argument("--n", type=int, default=1500, help="target jumlah review bot")
    p_synth.add_argument("--model", default=DEFAULT_GEMINI_MODEL)
    p_synth.add_argument(
        "--resume",
        action="store_true",
        help="lanjutkan dari synth.jsonl yang ada (hemat kuota setelah run terpotong)",
    )
    p_synth.set_defaults(func=command_synth)

    p_pack = sub.add_parser("pack", help="gabung jadi train/test/to_label")
    p_pack.set_defaults(func=command_pack)

    p_gold = sub.add_parser("gold", help="bekukan label manual jadi data/test_real.jsonl")
    p_gold.set_defaults(func=command_gold)

    p_stats = sub.add_parser("stats", help="tampilkan jumlah & distribusi label")
    p_stats.set_defaults(func=command_stats)

    args = parser.parse_args()
    args.func(args)


if __name__ == "__main__":
    main()
