"""Tes untuk logika yang bisa menghanguskan kerja anotasi manual.

Fokus pada `_carry_over_labels`: kalau ini salah, 250+ label tangan hilang
tanpa jejak saat `pack` dijalankan ulang.
"""

from __future__ import annotations

from ml.build_dataset import LABEL_ASLI, LABEL_BOT, LABEL_RAGU, _carry_over_labels


def _row(review_id: str, text: str, label: object = None) -> dict:
    return {
        "review_id": review_id,
        "store_id": None,
        "text": text,
        "posted_at": None,
        "reviewer_rating": None,
        "label": label,
    }


def test_membawa_label_lama_ke_kolam_baru():
    # Arrange
    lama = [_row("t-0001", "barang bagus sekali", LABEL_BOT)]
    baru = [_row("t-0001", "barang bagus sekali"), _row("t-0002", "paket telat")]

    # Act
    hasil, kept, orphaned = _carry_over_labels(baru, lama)

    # Assert
    assert [r["label"] for r in hasil] == [LABEL_BOT, None]
    assert (kept, orphaned) == (1, 0)


def test_mencocokkan_lewat_teks_bukan_review_id():
    """review_id posisional: menaikkan TO_LABEL_SIZE menggeser penomoran."""
    # Arrange
    lama = [_row("t-0001", "respons cepat", LABEL_ASLI)]
    baru = [_row("t-0400", "respons cepat")]

    # Act
    hasil, kept, orphaned = _carry_over_labels(baru, lama)

    # Assert
    assert hasil[0]["label"] == LABEL_ASLI
    assert (kept, orphaned) == (1, 0)


def test_label_ragu_ikut_terbawa():
    # Arrange
    lama = [_row("t-0001", "mantap", LABEL_RAGU)]
    baru = [_row("t-0001", "mantap")]

    # Act
    hasil, kept, _ = _carry_over_labels(baru, lama)

    # Assert
    assert hasil[0]["label"] == LABEL_RAGU
    assert kept == 1


def test_menghitung_label_yang_tidak_ketemu_di_kolam_baru():
    """Label yatim = kerja anotasi yang hangus; pemanggil wajib diberi tahu."""
    # Arrange
    lama = [_row("t-0001", "sudah dilabeli", LABEL_BOT)]
    baru = [_row("t-0001", "review yang sama sekali lain")]

    # Act
    hasil, kept, orphaned = _carry_over_labels(baru, lama)

    # Assert
    assert hasil[0]["label"] is None
    assert (kept, orphaned) == (0, 1)


def test_label_kosong_di_file_lama_tidak_menimpa():
    # Arrange
    lama = [_row("t-0001", "belum dilabeli", None)]
    baru = [_row("t-0001", "belum dilabeli")]

    # Act
    hasil, kept, orphaned = _carry_over_labels(baru, lama)

    # Assert
    assert hasil[0]["label"] is None
    assert (kept, orphaned) == (0, 0)


def test_kolam_lama_kosong_membiarkan_baris_baru_apa_adanya():
    # Arrange
    baru = [_row("t-0001", "review pertama")]

    # Act
    hasil, kept, orphaned = _carry_over_labels(baru, [])

    # Assert
    assert hasil == baru
    assert (kept, orphaned) == (0, 0)
