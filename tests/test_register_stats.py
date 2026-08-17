import pytest

from ml.register_stats import profile_gap, register_profile


def test_counts_records():
    profile = register_profile(["barang bagus", "pengiriman cepat"])
    assert profile.n == 2


def test_median_words():
    profile = register_profile(["satu dua tiga", "satu dua tiga empat lima"])
    assert profile.median_words == 4.0


def test_abbreviation_rate_detects_marketplace_shorthand():
    texts = ["barang bagus bgt, pengiriman cepet", "kualitas produk memuaskan"]
    assert register_profile(texts).abbreviation_rate == 0.5


def test_abbreviation_rate_needs_word_boundary():
    assert register_profile(["segalanya sempurna"]).abbreviation_rate == 0.0


def test_formal_marker_rate():
    texts = ["produk ini sangat memuaskan", "cepet sampe"]
    assert register_profile(texts).formal_marker_rate == 0.5


def test_lowercase_start_rate():
    texts = ["barang oke", "Barang oke", "barang oke"]
    assert register_profile(texts).lowercase_start_rate == pytest.approx(2 / 3)


def test_ignores_leading_whitespace_when_checking_case():
    assert register_profile(["   barang oke"]).lowercase_start_rate == 1.0


def test_empty_corpus_raises():
    with pytest.raises(ValueError, match="kosong"):
        register_profile([])


def test_profile_gap_reports_signed_differences():
    reference = register_profile(["barang bagus bgt", "cepet sampe bgt"])
    candidate = register_profile(["Produk ini sangat memuaskan sekali"])
    gap = profile_gap(reference, candidate)
    assert gap["abbreviation_rate"] < 0
    assert gap["lowercase_start_rate"] < 0
    assert gap["formal_marker_rate"] > 0


def test_profile_gap_is_zero_for_identical_corpora():
    texts = ["barang bagus bgt", "pengiriman cepet"]
    gap = profile_gap(register_profile(texts), register_profile(texts))
    assert all(value == 0 for value in gap.values())


def test_profile_gap_covers_every_measured_axis():
    profile = register_profile(["barang bagus bgt"])
    gap = profile_gap(profile, profile)
    assert set(gap) == {
        "median_words",
        "abbreviation_rate",
        "formal_marker_rate",
        "lowercase_start_rate",
    }


def test_profile_is_immutable():
    profile = register_profile(["barang bagus"])
    with pytest.raises(Exception):
        profile.n = 99
