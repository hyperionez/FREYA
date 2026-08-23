from __future__ import annotations

from functools import lru_cache

EMBEDDING_MODEL_NAME = "paraphrase-multilingual-MiniLM-L12-v2"


@lru_cache(maxsize=1)
def _model():
    """Muat model embedding sekali, dengan urutan impor yang aman.

    sklearn WAJIB diimpor sebelum sentence-transformers menarik torch. Urutan
    sebaliknya mematikan proses tanpa traceback - exit 127 atau heap corruption
    0xC0000374 - karena sklearn menarik pandas lalu zoneinfo setelah torch
    memuat DLL-nya. Gejala yang sama sudah didokumentasikan di ml/evaluate.py
    dan ml/calibration.py, tapi jalur produk belum pernah dijaga: memanggil
    get_review_authenticity_score() dengan review sungguhan mematikan proses
    di mesin dev proyek ini.

    Diverifikasi 23 Agustus 2026: tanpa baris sklearn di bawah prosesnya mati,
    dengan baris itu penilaian selesai normal. Jangan dirapikan oleh isort.
    """
    import sklearn.metrics  # noqa: F401  - WAJIB lebih dulu, lihat docstring

    from sentence_transformers import SentenceTransformer

    return SentenceTransformer(EMBEDDING_MODEL_NAME)


def encode(texts: list[str]):
    return _model().encode(texts, normalize_embeddings=True)
