import pytest

from ml.annotations_sync import clear_labels, merge_annotations


def _pool_row(review_id, text, label=None, **extra):
    return {
        "review_id": review_id,
        "store_id": None,
        "text": text,
        "posted_at": None,
        "reviewer_rating": None,
        "label": label,
        **extra,
    }


def _annotation(review_id, text, label, by="michael", at="2026-08-17T14:03:11"):
    return {
        "review_id": review_id,
        "text": text,
        "label": label,
        "annotated_by": by,
        "annotated_at": at,
    }


def test_applies_label_to_matching_review():
    pool = [_pool_row("t-1", "bahan jelek.. panas")]
    merged, report = merge_annotations(pool, [_annotation("t-1", "bahan jelek.. panas", 0)])
    assert merged[0]["label"] == 0
    assert report.applied == 1


def test_carries_annotator_metadata_for_audit_trail():
    pool = [_pool_row("t-1", "buruan order dijamin puas")]
    annotations = [_annotation("t-1", "buruan order dijamin puas", 1, by="michael")]
    merged, _ = merge_annotations(pool, annotations)
    assert merged[0]["annotated_by"] == "michael"
    assert merged[0]["annotated_at"] == "2026-08-17T14:03:11"


def test_carries_ragu_label_through():
    pool = [_pool_row("t-1", "mantap paten joss")]
    merged, report = merge_annotations(pool, [_annotation("t-1", "mantap paten joss", "ragu")])
    assert merged[0]["label"] == "ragu"
    assert report.applied == 1


def test_leaves_unannotated_rows_untouched():
    pool = [_pool_row("t-1", "sudah"), _pool_row("t-2", "belum")]
    merged, report = merge_annotations(pool, [_annotation("t-1", "sudah", 0)])
    assert merged[1]["label"] is None
    assert "annotated_by" not in merged[1]
    assert report.untouched == 1


def test_last_annotation_wins_for_repeated_review():
    # annotations.jsonl bersifat append-only (ml/annotate.py:69), jadi melabeli
    # ulang review yang sama menambah baris kedua, bukan menimpa.
    pool = [_pool_row("t-1", "barang ok")]
    annotations = [
        _annotation("t-1", "barang ok", 1, at="2026-08-17T10:00:00"),
        _annotation("t-1", "barang ok", "ragu", at="2026-08-17T15:00:00"),
    ]
    merged, report = merge_annotations(pool, annotations)
    assert merged[0]["label"] == "ragu"
    assert merged[0]["annotated_at"] == "2026-08-17T15:00:00"
    assert report.applied == 1


def test_falls_back_to_text_when_review_id_shifted():
    # ml/build_dataset.py:341 mencatat review_id bersifat posisional dan bergeser
    # kalau `pack` dijalankan ulang; teks yang dinormalisasi tetap cocok.
    pool = [_pool_row("t-77", "Barang BAGUS!!!")]
    merged, report = merge_annotations(pool, [_annotation("t-1", "barang bagus", 1)])
    assert merged[0]["label"] == 1
    assert report.matched_by_text == 1


def test_reports_orphaned_annotations():
    pool = [_pool_row("t-1", "ada di kolam")]
    annotations = [
        _annotation("t-1", "ada di kolam", 0),
        _annotation("t-9", "sudah tidak ada di kolam", 1),
    ]
    _, report = merge_annotations(pool, annotations)
    assert report.orphaned == 1


def test_does_not_mutate_input_rows():
    pool = [_pool_row("t-1", "barang ok")]
    merge_annotations(pool, [_annotation("t-1", "barang ok", 1)])
    assert pool[0]["label"] is None


def test_rejects_annotation_without_review_id():
    pool = [_pool_row("t-1", "barang ok")]
    with pytest.raises(ValueError, match="review_id"):
        merge_annotations(pool, [{"text": "barang ok", "label": 1}])


def test_rejects_unknown_label_value():
    pool = [_pool_row("t-1", "barang ok")]
    with pytest.raises(ValueError):
        merge_annotations(pool, [_annotation("t-1", "barang ok", "mungkin")])


def test_clear_labels_blanks_label_and_audit_fields():
    pool = [
        _pool_row("t-1", "a", label=1, annotated_by="michael", annotated_at="2026-08-16T09:00:00"),
        _pool_row("t-2", "b", label="ragu", annotated_by="michael"),
    ]
    cleared, count = clear_labels(pool)
    assert count == 2
    assert all(row["label"] is None for row in cleared)
    assert all("annotated_by" not in row for row in cleared)
    assert all("annotated_at" not in row for row in cleared)


def test_clear_labels_keeps_review_fields():
    pool = [_pool_row("t-1", "bahan jelek", label=0)]
    cleared, _ = clear_labels(pool)
    assert cleared[0]["review_id"] == "t-1"
    assert cleared[0]["text"] == "bahan jelek"
    assert "store_id" in cleared[0]


def test_clear_labels_counts_only_labeled_rows():
    pool = [_pool_row("t-1", "a", label=0), _pool_row("t-2", "b")]
    _, count = clear_labels(pool)
    assert count == 1


def test_clear_labels_does_not_mutate_input():
    pool = [_pool_row("t-1", "a", label=1)]
    clear_labels(pool)
    assert pool[0]["label"] == 1
