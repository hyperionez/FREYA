"""Tes linter rubrik anotasi - aturan yang bisa dicek mekanis dari teks + label."""

from __future__ import annotations

from ml.check_rubric import (
    RAGU_MAKS,
    RAGU_MIN,
    check_records,
    mengandung_keluhan,
)


def _rec(text, label, by="michael", review_id="t-0001"):
    return {"review_id": review_id, "text": text, "label": label, "annotated_by": by}


# --- deteksi keluhan (dasar dari aturan section 5 langkah 2) ---


def test_keluhan_eksplisit_terdeteksi():
    assert mengandung_keluhan("barang jelek, saya sangat kecewa berat")


def test_pujian_biasa_bukan_keluhan():
    assert not mengandung_keluhan("Barang original mantapp, seller ramah")


def test_penanda_yang_dinegasikan_bukan_keluhan():
    # "tidak cacat" adalah pujian; pencocokan kata polos salah menandainya keluhan.
    assert not mengandung_keluhan("rapih tidak cacat, sesuai gambar")
    assert not mengandung_keluhan("ga rusak sama sekali")


# --- section 5 langkah 2: ada keluhan -> wajib asli ---


def test_keluhan_dilabeli_bot_adalah_pelanggaran():
    laporan = check_records([_rec("pelayanan buruk, saya kecewa", 1)])

    assert len(laporan["pelanggaran"]) == 1
    assert laporan["pelanggaran"][0]["review_id"] == "t-0001"


def test_keluhan_dilabeli_asli_bukan_pelanggaran():
    laporan = check_records([_rec("pelayanan buruk, saya kecewa", 0)])

    assert laporan["pelanggaran"] == []


def test_keluhan_dilabeli_ragu_bukan_pelanggaran():
    # "ragu" dibuang saat evaluasi, jadi tidak menyuntikkan label salah ke test set.
    laporan = check_records([_rec("pelayanan buruk, saya kecewa", "ragu")])

    assert laporan["pelanggaran"] == []


def test_baris_belum_dilabeli_dilewati():
    laporan = check_records([_rec("pelayanan buruk, saya kecewa", None)])

    assert laporan["pelanggaran"] == []


# --- rasio ragu (target rubrik section 2: 10-20%) ---


def test_ragu_terlalu_sedikit_ditandai():
    records = [_rec("teks biasa", 0, review_id=f"t-{i}") for i in range(100)]
    laporan = check_records(records)

    assert laporan["ragu"]["rasio"] == 0.0
    assert laporan["ragu"]["dalam_target"] is False


def test_ragu_dalam_rentang_target_tidak_ditandai():
    records = [_rec("teks biasa", 0, review_id=f"t-{i}") for i in range(85)]
    records += [_rec("teks biasa", "ragu", review_id=f"r-{i}") for i in range(15)]
    laporan = check_records(records)

    assert RAGU_MIN <= laporan["ragu"]["rasio"] <= RAGU_MAKS
    assert laporan["ragu"]["dalam_target"] is True


# --- section 4: pendek bukan bukti bot (advisory, bukan pelanggaran) ---


def test_review_pendek_dilabeli_bot_jadi_catatan_bukan_pelanggaran():
    laporan = check_records([_rec("mantap joss", 1)])

    assert laporan["pelanggaran"] == []
    assert len(laporan["catatan_pendek"]) == 1


def test_review_panjang_dilabeli_bot_tidak_jadi_catatan():
    panjang = "Kualitas barang sangat bagus sekali dan pengiriman sangat cepat sekali " * 3
    laporan = check_records([_rec(panjang, 1)])

    assert laporan["catatan_pendek"] == []


# --- pengelompokan per anotator (satu berkas bisa memuat lebih dari satu orang) ---


def test_laporan_dipecah_per_anotator():
    records = [
        _rec("pelayanan buruk, saya kecewa", 1, by="michael", review_id="t-1"),
        _rec("pelayanan buruk, saya kecewa", 0, by="JR", review_id="t-2"),
    ]
    laporan = check_records(records)

    assert laporan["per_anotator"]["michael"]["pelanggaran"] == 1
    assert laporan["per_anotator"]["JR"]["pelanggaran"] == 0
