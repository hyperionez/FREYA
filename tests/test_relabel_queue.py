import pytest

from ml.relabel_queue import (
    NEGATIVE,
    POSITIVE,
    RelabelError,
    blank_labels,
    seed_annotations,
    select_for_relabel,
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


def _ids(rows):
    return [row["review_id"] for row in rows]


# --------------------------------------------------------------------------
# select_for_relabel
# --------------------------------------------------------------------------


def test_negative_labeled_asli_is_kept():
    # Rubrik bagian 5 langkah 2: ada keluhan atau kritik -> Asli, tanpa syarat.
    pool = [_row("a", "barang rusak", 0)]

    plan = select_for_relabel(pool, {"barang rusak": NEGATIVE})

    assert _ids(plan.keep) == ["a"]
    assert plan.redo == []


def test_negative_labeled_ragu_is_kept():
    pool = [_row("a", "barang rusak", "ragu")]

    plan = select_for_relabel(pool, {"barang rusak": NEGATIVE})

    assert _ids(plan.keep) == ["a"]


def test_negative_labeled_bot_goes_back_in_the_queue():
    pool = [_row("a", "barang rusak", 1)]

    plan = select_for_relabel(pool, {"barang rusak": NEGATIVE})

    assert _ids(plan.redo) == ["a"]
    assert plan.keep == []


@pytest.mark.parametrize("label", [0, 1, "ragu"])
def test_every_positive_review_goes_back_in_the_queue(label):
    # Rubrik bagian 4: positif bukan bukti - apa pun labelnya, keputusannya
    # diambil lewat pertanyaan yang salah.
    pool = [_row("a", "mantap sekali", label)]

    plan = select_for_relabel(pool, {"mantap sekali": POSITIVE})

    assert _ids(plan.redo) == ["a"]


def test_review_absent_from_the_sentiment_source_goes_back_in_the_queue():
    pool = [_row("a", "teks tak dikenal", 0)]

    plan = select_for_relabel(pool, {})

    assert _ids(plan.redo) == ["a"]


def test_unlabeled_review_goes_back_in_the_queue():
    pool = [_row("a", "barang rusak", None)]

    plan = select_for_relabel(pool, {"barang rusak": NEGATIVE})

    assert _ids(plan.redo) == ["a"]


def test_label_spelling_is_normalised_before_deciding():
    pool = [_row("a", "barang rusak", "ASLI"), _row("b", "barang rusak lagi", "Bot")]
    sentiment = {"barang rusak": NEGATIVE, "barang rusak lagi": NEGATIVE}

    plan = select_for_relabel(pool, sentiment)

    assert _ids(plan.keep) == ["a"]
    assert _ids(plan.redo) == ["b"]


def test_pool_order_is_preserved_in_both_lists():
    pool = [
        _row("a", "rusak", 0),
        _row("b", "bagus", 1),
        _row("c", "jelek", 0),
        _row("d", "keren", 1),
    ]
    sentiment = {"rusak": NEGATIVE, "bagus": POSITIVE, "jelek": NEGATIVE, "keren": POSITIVE}

    plan = select_for_relabel(pool, sentiment)

    assert _ids(plan.keep) == ["a", "c"]
    assert _ids(plan.redo) == ["b", "d"]


def test_sentiment_lookup_tolerates_whitespace_and_case():
    pool = [_row("a", "  Barang   RUSAK  ", 0)]

    plan = select_for_relabel(pool, {"barang rusak": NEGATIVE})

    assert _ids(plan.keep) == ["a"]


def test_unknown_sentiment_value_is_rejected_loudly():
    pool = [_row("a", "rusak", 0)]

    with pytest.raises(RelabelError, match="Netral"):
        select_for_relabel(pool, {"rusak": "Netral"})


# --------------------------------------------------------------------------
# blank_labels
# --------------------------------------------------------------------------


def test_blank_labels_clears_only_the_listed_reviews():
    pool = [_row("a", "x", 0), _row("b", "y", 1)]

    blanked = blank_labels(pool, {"b"})

    assert blanked[0]["label"] == 0
    assert blanked[1]["label"] is None


def test_blank_labels_strips_the_annotator_trail_it_clears():
    pool = [_row("a", "x", 1, annotated_by="michael", annotated_at="2026-08-18T09:00:00")]

    blanked = blank_labels(pool, {"a"})

    assert "annotated_by" not in blanked[0]
    assert "annotated_at" not in blanked[0]


def test_blank_labels_leaves_the_trail_of_rows_it_keeps():
    pool = [_row("a", "x", 0, annotated_by="michael")]

    blanked = blank_labels(pool, {"zzz"})

    assert blanked[0]["annotated_by"] == "michael"


def test_blank_labels_does_not_mutate_the_pool():
    pool = [_row("a", "x", 1)]

    blank_labels(pool, {"a"})

    assert pool[0]["label"] == 1


def test_blank_labels_keeps_row_count_and_order():
    pool = [_row("a", "x", 0), _row("b", "y", 1), _row("c", "z", 1)]

    blanked = blank_labels(pool, {"b"})

    assert _ids(blanked) == ["a", "b", "c"]


# --------------------------------------------------------------------------
# seed_annotations
# --------------------------------------------------------------------------


def test_seed_annotations_writes_one_record_per_kept_review():
    kept = [_row("a", "x", 0), _row("b", "y", "ragu")]

    records = seed_annotations(kept, annotator="michael", at="2026-08-18T09:00:00")

    assert _ids(records) == ["a", "b"]
    assert records[0]["label"] == 0
    assert records[1]["label"] == "ragu"


def test_seed_annotations_carries_text_and_audit_fields():
    kept = [_row("a", "teks review", 0)]

    records = seed_annotations(kept, annotator="michael", at="2026-08-18T09:00:00")

    assert records[0]["text"] == "teks review"
    assert records[0]["annotated_by"] == "michael"
    assert records[0]["annotated_at"] == "2026-08-18T09:00:00"


def test_seed_annotations_normalises_the_label():
    kept = [_row("a", "x", "Asli")]

    records = seed_annotations(kept, annotator="michael", at="2026-08-18T09:00:00")

    assert records[0]["label"] == 0


def test_seed_annotations_rejects_an_unlabeled_row():
    with pytest.raises(RelabelError, match="belum dilabeli"):
        seed_annotations([_row("a", "x", None)], annotator="michael", at="2026-08-18T09:00:00")


def test_seed_annotations_rejects_a_blank_annotator():
    with pytest.raises(RelabelError, match="anotator"):
        seed_annotations([_row("a", "x", 0)], annotator="  ", at="2026-08-18T09:00:00")
