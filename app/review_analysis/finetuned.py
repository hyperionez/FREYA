"""Lapis 2 - klasifikasi keaslian review dengan IndoBERT yang di-fine-tune.

Model bekerja per review, sementara kontrak `get_review_authenticity_score()`
menuntut satu skor per toko. Modul ini menutup jarak itu: klasifikasi tiap
review, lalu agregasi jadi satu `{score, source, reasons}` yang bentuknya sama
persis dengan keluaran heuristik Lapis 1, supaya `features.py` tidak perlu tahu
lapis mana yang menjawab.

Model TIDAK di-commit (lihat `.gitignore`: `/ml/model`). Kalau berkasnya tidak
ada - termasuk saat juri menjalankan `docker compose up` dari repo bersih -
modul ini mengembalikan None dan pemanggil jatuh ke heuristik. Kegagalan itu
disengaja dan terlihat lewat field `source`, bukan disembunyikan.

Torch sengaja diimpor di dalam fungsi, bukan di kepala modul: impor torch lebih
dulu daripada sklearn pernah menyebabkan heap corruption di mesin dev proyek ini
(lihat commit 4c33aff).
"""

from __future__ import annotations

from functools import lru_cache
from pathlib import Path
from typing import Any

# Gerbang Lapis 2 - dimatikan berdasarkan evaluasi 23 Agustus 2026 terhadap
# data/test_real.jsonl (97 review teradjudikasi, 75 asli / 22 bot):
#
#     recall bot model         0.0%  (0 dari 22)   macro F1 0.436
#     penebak kelas mayoritas                      macro F1 0.436
#     heuristik Lapis 1        4.5%  (1 dari 22)   macro F1 0.477
#
# Model memprediksi "asli" untuk seluruh 97 review. Di test_synthetic.jsonl
# recall botnya justru 99,6% - yang dipelajari adalah "apakah teks ini ditulis
# LLM", bukan "apakah review ini bot", karena kelas bot di train.jsonl seluruhnya
# review sintetik hasil Gemini sementara bot marketplace nyata adalah copy-paste
# manusia. Mengirim lapis ini menyala berarti mengirim lapis yang terbukti lebih
# buruk daripada menebak kelas mayoritas.
#
# Menyalakan kembali menuntut bukti baru, bukan keyakinan: jalankan
# `python ml/evaluate.py --test data/test_real.jsonl` dan pastikan macro F1
# model melewati heuristik. Ubah nilai ini hanya bersamaan angka barunya.
LAPIS2_AKTIF = False

MODEL_DIR = Path("ml/model/final")
MAX_LENGTH = 256
BOT_THRESHOLD = 0.5
MAX_REVIEWS = 30
SOURCE = "finetuned_indobert"

# Contoh review yang dikutip di `reasons` dipotong supaya alasan tetap terbaca.
EXCERPT_LENGTH = 80


@lru_cache(maxsize=1)
def _pipeline():
    """Muat tokenizer + model sekali, atau None kalau berkasnya tidak ada."""
    if not (MODEL_DIR / "config.json").exists():
        return None

    # torch WAJIB diimpor sebelum transformers. Urutan terbalik membuat proses
    # mati dengan exit 127 (heap corruption) atau menggantung tanpa pesan di
    # mesin dev proyek ini - gejala sekeluarga dengan commit 4c33aff.
    import torch  # noqa: F401
    from transformers import AutoModelForSequenceClassification, AutoTokenizer

    tokenizer = AutoTokenizer.from_pretrained(MODEL_DIR)
    model = AutoModelForSequenceClassification.from_pretrained(MODEL_DIR)
    model.eval()
    return tokenizer, model


def is_available() -> bool:
    """Apakah model siap dipakai - dipakai pemanggil untuk memilih lapis."""
    return LAPIS2_AKTIF and _pipeline() is not None


def predict_bot_probabilities(texts: list[str]) -> list[float]:
    """Peluang tiap teks tergolong bot (kelas 1). Daftar kosong kalau model absen."""
    loaded = _pipeline()
    if loaded is None or not texts:
        return []

    import torch

    tokenizer, model = loaded
    batch = tokenizer(
        texts,
        truncation=True,
        padding=True,
        max_length=MAX_LENGTH,
        return_tensors="pt",
    )
    with torch.no_grad():
        logits = model(**batch).logits
    return torch.softmax(logits, dim=-1)[:, 1].tolist()


def _excerpt(text: str) -> str:
    collapsed = " ".join(text.split())
    if len(collapsed) <= EXCERPT_LENGTH:
        return collapsed
    return collapsed[:EXCERPT_LENGTH] + "..."


def aggregate(probabilities: list[float], texts: list[str]) -> dict[str, Any]:
    """Gabung prediksi per-review jadi satu penilaian per toko.

    Skor = proporsi review yang lolos ambang, diskalakan ke 0-100. Formula
    linear dipilih supaya alasannya bisa dijelaskan ke pengguna apa adanya:
    "3 dari 20 review berpola bot" langsung terbaca sebagai skor 85.
    """
    flagged = [
        (probability, text)
        for probability, text in zip(probabilities, texts)
        if probability >= BOT_THRESHOLD
    ]
    total = len(probabilities)
    score = round(100 * (1 - len(flagged) / total))

    if not flagged:
        reasons = [f"Model tidak menemukan pola review bot pada {total} review"]
        return {"score": score, "source": SOURCE, "reasons": reasons}

    worst = max(flagged)
    reasons = [
        f"{len(flagged)} dari {total} review terdeteksi berpola bot oleh model",
        f'Contoh paling kuat (keyakinan {worst[0]:.0%}): "{_excerpt(worst[1])}"',
    ]
    return {"score": score, "source": SOURCE, "reasons": reasons}


def run_finetuned_classifier(
    store_id: str, reviews: list[dict[str, Any]]
) -> dict[str, Any] | None:
    """Penilaian keaslian satu toko lewat model, atau None kalau tidak bisa.

    None berarti "lapis ini tidak menjawab" - model absen, atau tidak ada teks
    review yang bisa dinilai - dan pemanggil wajib jatuh ke heuristik.
    """
    # Gerbang didahulukan sebelum apa pun: kalau lapis ini mati, torch tidak
    # perlu diimpor sama sekali. Itu juga menghindari urutan impor torch-sebelum
    # -sklearn yang mematikan proses dengan heap corruption (lihat docstring).
    if not LAPIS2_AKTIF:
        return None

    texts = [review["text"] for review in reviews if review.get("text", "").strip()]
    if not texts:
        return None

    probabilities = predict_bot_probabilities(texts[:MAX_REVIEWS])
    if not probabilities:
        return None

    return aggregate(probabilities, texts[:MAX_REVIEWS])
