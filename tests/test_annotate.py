"""Tes penjagaan rubrik di alat anotasi - logika murni, tanpa menjalankan Streamlit."""

from __future__ import annotations

from ml.annotate import (
    LABEL_ASLI,
    LABEL_BOT,
    LABEL_RAGU,
    peringatan_rubrik,
    perlu_konfirmasi,
)

KELUHAN = "pelayanan buruk, barang rusak, saya kecewa berat dengan toko ini"
NETRAL = "Kualitas barang sangat bagus sekali dan pengiriman sangat cepat sekali " * 2


def test_keluhan_dilabeli_bot_memicu_peringatan():
    pesan = peringatan_rubrik(KELUHAN, LABEL_BOT)

    assert len(pesan) == 1
    assert "langkah 2" in pesan[0].lower()


def test_keluhan_dilabeli_asli_tidak_memicu_apa_pun():
    assert peringatan_rubrik(KELUHAN, LABEL_ASLI) == []


def test_keluhan_dilabeli_ragu_tidak_memicu_apa_pun():
    assert peringatan_rubrik(KELUHAN, LABEL_RAGU) == []


def test_review_pendek_dilabeli_bot_memicu_peringatan_section_4():
    pesan = peringatan_rubrik("mantap joss", LABEL_BOT)

    assert len(pesan) == 1
    assert "section 4" in pesan[0].lower()


def test_review_panjang_tanpa_keluhan_dilabeli_bot_lolos_tanpa_peringatan():
    assert peringatan_rubrik(NETRAL, LABEL_BOT) == []


def test_keluhan_pendek_memicu_dua_peringatan_sekaligus():
    pesan = peringatan_rubrik("barang rusak", LABEL_BOT)

    assert len(pesan) == 2


def test_negasi_tidak_dianggap_keluhan():
    # "tidak cacat" adalah pujian - alat tidak boleh menghalangi label bot di sini.
    # Teks dibuat panjang supaya peringatan section 4 tidak ikut menyala dan
    # mengaburkan apa yang diuji.
    pujian = "Barang rapih tidak cacat sama sekali, sesuai gambar dan deskripsi, mantap sekali ya"
    assert peringatan_rubrik(pujian, LABEL_BOT) == []


def test_perlu_konfirmasi_hanya_saat_ada_peringatan():
    assert perlu_konfirmasi(KELUHAN, LABEL_BOT) is True
    assert perlu_konfirmasi(KELUHAN, LABEL_ASLI) is False
    assert perlu_konfirmasi(NETRAL, LABEL_BOT) is False
