"""Tes agregasi Lapis 2 - murni logika, tanpa memuat model."""

from __future__ import annotations

import pytest

from app.review_analysis import finetuned


def test_skor_penuh_saat_tidak_ada_review_ditandai():
    hasil = finetuned.aggregate([0.1, 0.2, 0.05], ["a", "b", "c"])

    assert hasil["score"] == 100
    assert hasil["source"] == "finetuned_indobert"
    assert "3 review" in hasil["reasons"][0]


def test_skor_turun_proporsional_dengan_review_bot():
    hasil = finetuned.aggregate([0.9, 0.9, 0.1, 0.1], ["a", "b", "c", "d"])

    assert hasil["score"] == 50
    assert "2 dari 4 review" in hasil["reasons"][0]


def test_alasan_mengutip_review_dengan_keyakinan_tertinggi():
    hasil = finetuned.aggregate([0.6, 0.95], ["agak mirip bot", "sangat mirip bot"])

    assert "sangat mirip bot" in hasil["reasons"][1]
    assert "95%" in hasil["reasons"][1]


def test_kutipan_panjang_dipotong():
    panjang = "kata " * 50
    hasil = finetuned.aggregate([0.99], [panjang])

    assert hasil["reasons"][1].count("...") == 1
    assert len(hasil["reasons"][1]) < len(panjang)


def test_mengembalikan_none_saat_tidak_ada_teks_review():
    assert finetuned.run_finetuned_classifier("toko-1", []) is None
    assert finetuned.run_finetuned_classifier("toko-1", [{"text": "   "}]) is None


def test_mengembalikan_none_saat_model_tidak_terpasang(monkeypatch):
    monkeypatch.setattr(finetuned, "predict_bot_probabilities", lambda texts: [])

    assert finetuned.run_finetuned_classifier("toko-1", [{"text": "ada isinya"}]) is None


def test_hanya_menilai_sebanyak_batas_review(monkeypatch):
    dilihat = {}

    def catat(texts):
        dilihat["jumlah"] = len(texts)
        return [0.1] * len(texts)

    monkeypatch.setattr(finetuned, "predict_bot_probabilities", catat)
    reviews = [{"text": f"review ke-{i}"} for i in range(finetuned.MAX_REVIEWS + 10)]

    finetuned.run_finetuned_classifier("toko-1", reviews)

    assert dilihat["jumlah"] == finetuned.MAX_REVIEWS


def test_router_jatuh_ke_heuristik_saat_model_absen(monkeypatch):
    from app import review_analysis

    monkeypatch.setattr(review_analysis, "run_finetuned_classifier", lambda s, r: None)
    hasil = review_analysis.get_review_authenticity_score("toko-1", [])

    assert hasil["source"] == "heuristic_l1"


def test_router_memakai_model_saat_tersedia(monkeypatch):
    from app import review_analysis

    jawaban = {"score": 40, "source": "finetuned_indobert", "reasons": ["x"]}
    monkeypatch.setattr(review_analysis, "run_finetuned_classifier", lambda s, r: jawaban)

    assert review_analysis.get_review_authenticity_score("toko-1", [{"text": "a"}]) is jawaban
