import pytest

from ml.calibration import (
    AgreementReport,
    CalibrationError,
    agreement,
    sample_batch,
)


def _row(review_id, text, label=None, **extra):
    return {
        "review_id": review_id,
        "store_id": None,
        "text": text,
        "posted_at": None,
        "reviewer_rating": None,
        "label": label,
        **extra,
    }


def _pool(n, label_cycle=(0, 1)):
    return [
        _row(f"t-{i:04d}", f"review nomor {i}", label_cycle[i % len(label_cycle)])
        for i in range(1, n + 1)
    ]


# --------------------------------------------------------------------------
# sample_batch
# --------------------------------------------------------------------------


def test_sample_batch_returns_requested_size():
    batch = sample_batch(_pool(50), size=10, seed=1)

    assert len(batch) == 10


def test_sample_batch_blanks_the_first_labels():
    batch = sample_batch(_pool(50), size=10, seed=1)

    assert all(row["label"] is None for row in batch)


def test_sample_batch_strips_annotator_trail():
    pool = [_row("t-0001", "teks", 1, annotated_by="michael", annotated_at="2026-08-18")]

    batch = sample_batch(pool, size=1, seed=1)

    assert "annotated_by" not in batch[0]
    assert "annotated_at" not in batch[0]


def test_sample_batch_keeps_review_id_and_text():
    batch = sample_batch(_pool(20), size=20, seed=1)

    assert {row["review_id"] for row in batch} == {f"t-{i:04d}" for i in range(1, 21)}
    assert all(row["text"] for row in batch)


def test_sample_batch_shuffles_so_order_carries_no_hint():
    pool = _pool(60)

    batch = sample_batch(pool, size=60, seed=1)

    assert [row["review_id"] for row in batch] != [row["review_id"] for row in pool]


def test_sample_batch_is_deterministic_for_a_seed():
    pool = _pool(50)

    first = sample_batch(pool, size=10, seed=7)
    second = sample_batch(pool, size=10, seed=7)

    assert [row["review_id"] for row in first] == [row["review_id"] for row in second]


def test_sample_batch_ignores_rows_the_first_pass_left_unlabeled():
    pool = _pool(5) + [_row(f"u-{i}", "belum dilabeli", None) for i in range(20)]

    batch = sample_batch(pool, size=5, seed=1)

    assert {row["review_id"] for row in batch} == {f"t-{i:04d}" for i in range(1, 6)}


def test_sample_batch_rejects_size_larger_than_labeled_pool():
    with pytest.raises(CalibrationError, match="hanya 5"):
        sample_batch(_pool(5), size=10, seed=1)


def test_sample_batch_rejects_non_positive_size():
    with pytest.raises(CalibrationError):
        sample_batch(_pool(5), size=0, seed=1)


def test_sample_batch_does_not_mutate_the_pool():
    pool = _pool(10)

    sample_batch(pool, size=5, seed=1)

    assert all(row["label"] is not None for row in pool)


# --------------------------------------------------------------------------
# agreement
# --------------------------------------------------------------------------


def test_agreement_perfect_match():
    first = _pool(10)
    second = [_row(row["review_id"], row["text"], row["label"]) for row in first]

    report = agreement(first, second)

    assert report.compared == 10
    assert report.percent_match == 1.0
    assert report.kappa == 1.0
    assert report.disagreements == []


def test_agreement_counts_only_the_reviews_relabeled():
    first = _pool(100)
    second = [_row(row["review_id"], row["text"], row["label"]) for row in first[:10]]

    report = agreement(first, second)

    assert report.compared == 10


def test_agreement_percent_match_counts_exact_label_equality():
    first = [_row("a", "x", 0), _row("b", "y", 1), _row("c", "z", 0), _row("d", "w", 1)]
    second = [_row("a", "x", 0), _row("b", "y", 0), _row("c", "z", 0), _row("d", "w", 1)]

    report = agreement(first, second)

    assert report.percent_match == 0.75


def test_agreement_treats_ragu_as_its_own_class():
    first = [_row("a", "x", "ragu"), _row("b", "y", "ragu")]
    second = [_row("a", "x", "ragu"), _row("b", "y", 1)]

    report = agreement(first, second)

    assert report.percent_match == 0.5
    assert report.matrix[("ragu", "bot")] == 1


def test_agreement_normalises_label_spelling():
    first = [_row("a", "x", "Bot"), _row("b", "y", "ASLI")]
    second = [_row("a", "x", 1), _row("b", "y", 0)]

    report = agreement(first, second)

    assert report.percent_match == 1.0


def test_agreement_kappa_is_zero_when_match_is_pure_chance():
    # Kedua pass melabeli 50/50 dan sepakat persis separuh - itu definisi kebetulan.
    first = [_row("a", "1", 0), _row("b", "2", 0), _row("c", "3", 1), _row("d", "4", 1)]
    second = [_row("a", "1", 0), _row("b", "2", 1), _row("c", "3", 0), _row("d", "4", 1)]

    report = agreement(first, second)

    assert report.kappa == pytest.approx(0.0)


def test_agreement_kappa_is_negative_when_worse_than_chance():
    first = [_row("a", "1", 0), _row("b", "2", 0), _row("c", "3", 1), _row("d", "4", 1)]
    second = [_row("a", "1", 1), _row("b", "2", 1), _row("c", "3", 0), _row("d", "4", 0)]

    report = agreement(first, second)

    assert report.kappa < 0


def test_agreement_lists_disagreements_with_both_labels_and_text():
    first = [_row("a", "teks yang jadi rebutan", 0)]
    second = [_row("a", "teks yang jadi rebutan", 1)]

    report = agreement(first, second)

    assert report.disagreements == [
        {
            "review_id": "a",
            "text": "teks yang jadi rebutan",
            "first": "asli",
            "second": "bot",
        }
    ]


def test_agreement_rejects_unlabeled_rows_in_the_second_pass():
    first = _pool(3)
    second = [_row("t-0001", "review nomor 1", None)]

    with pytest.raises(CalibrationError, match="belum dilabeli"):
        agreement(first, second)


def test_agreement_rejects_review_id_absent_from_the_first_pass():
    first = _pool(3)
    second = [_row("hantu-1", "tidak ada di kolam", 1)]

    with pytest.raises(CalibrationError, match="hantu-1"):
        agreement(first, second)


def test_agreement_rejects_an_empty_second_pass():
    with pytest.raises(CalibrationError, match="kosong"):
        agreement(_pool(3), [])


def test_agreement_verdict_follows_the_rubric_thresholds():
    assert AgreementReport(compared=100, percent_match=0.90, kappa=0.8).verdict == "lanjut"
    assert AgreementReport(compared=100, percent_match=0.85, kappa=0.7).verdict == "lanjut"
    assert AgreementReport(compared=100, percent_match=0.78, kappa=0.5).verdict == "tajamkan"
    assert AgreementReport(compared=100, percent_match=0.70, kappa=0.4).verdict == "tajamkan"
    assert AgreementReport(compared=100, percent_match=0.69, kappa=0.3).verdict == "berhenti"
