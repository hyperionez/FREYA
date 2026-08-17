import json

import pytest

from ml.dataset_io import (
    ID2LABEL,
    LABEL2ID,
    RAGU,
    LabelError,
    annotation_summary,
    load_labeled_records,
    load_records,
    normalize_label,
)


def _write_jsonl(path, records):
    with path.open("w", encoding="utf-8") as f:
        for record in records:
            f.write(json.dumps(record, ensure_ascii=False) + "\n")
    return path


def test_label_maps_are_consistent():
    assert LABEL2ID == {"asli": 0, "bot": 1}
    assert ID2LABEL == {0: "asli", 1: "bot"}


def test_normalize_label_accepts_integer_form():
    assert normalize_label(0) == 0
    assert normalize_label(1) == 1


def test_normalize_label_accepts_string_form():
    assert normalize_label("asli") == 0
    assert normalize_label("bot") == 1


def test_normalize_label_ignores_case_and_padding():
    assert normalize_label("  Bot ") == 1
    assert normalize_label("ASLI") == 0


def test_normalize_label_accepts_digit_string():
    assert normalize_label("0") == 0
    assert normalize_label("1") == 1


def test_normalize_label_treats_missing_as_unlabeled():
    assert normalize_label(None) is None
    assert normalize_label("") is None


def test_normalize_label_keeps_ragu_as_its_own_value():
    # ml/annotate.py:31 menulis "ragu" sebagai kelas ketiga; rubrik menargetkan
    # 10-20% ragu. Loader tidak boleh crash, tapi juga tidak boleh diam-diam
    # memasukkannya ke asli atau bot.
    assert normalize_label("ragu") == RAGU
    assert normalize_label(" Ragu ") == RAGU


def test_normalize_label_rejects_unknown_value():
    with pytest.raises(LabelError):
        normalize_label("mungkin")
    with pytest.raises(LabelError):
        normalize_label(2)


def test_load_records_normalizes_integer_dataset(tmp_path):
    path = _write_jsonl(
        tmp_path / "train.jsonl",
        [
            {"id": "real-1", "text": "barang sesuai deskripsi", "label": 0},
            {"id": "syn-1", "text": "mantap sekali luar biasa", "label": 1},
        ],
    )
    records = load_records(path)
    assert [r["label"] for r in records] == [0, 1]


def test_load_records_normalizes_string_dataset(tmp_path):
    path = _write_jsonl(
        tmp_path / "annotations.jsonl",
        [
            {"review_id": "d-1", "text": "jahitannya kurang rapi", "label": "asli"},
            {"review_id": "d-2", "text": "produk terbaik sepanjang masa", "label": "bot"},
        ],
    )
    records = load_records(path)
    assert [r["label"] for r in records] == [0, 1]


def test_load_records_preserves_other_fields(tmp_path):
    path = _write_jsonl(
        tmp_path / "train.jsonl",
        [{"id": "syn-1", "text": "mantap", "label": 1, "style": "superlative_spam"}],
    )
    record = load_records(path)[0]
    assert record["id"] == "syn-1"
    assert record["style"] == "superlative_spam"


def test_load_records_does_not_rewrite_source_file(tmp_path):
    path = _write_jsonl(
        tmp_path / "annotations.jsonl",
        [{"review_id": "d-1", "text": "oke", "label": "bot"}],
    )
    load_records(path)
    raw = json.loads(path.read_text(encoding="utf-8").strip())
    assert raw["label"] == "bot"


def test_load_records_skips_blank_lines(tmp_path):
    path = tmp_path / "train.jsonl"
    path.write_text(
        '{"text": "a", "label": 0}\n\n{"text": "b", "label": 1}\n',
        encoding="utf-8",
    )
    assert len(load_records(path)) == 2


def test_load_records_keeps_unlabeled_rows(tmp_path):
    path = _write_jsonl(
        tmp_path / "to_label.jsonl",
        [
            {"review_id": "t-1", "text": "sudah dilabeli", "label": 0},
            {"review_id": "t-2", "text": "belum dilabeli", "label": None},
        ],
    )
    assert len(load_records(path)) == 2


def test_load_labeled_records_drops_unlabeled_rows(tmp_path):
    path = _write_jsonl(
        tmp_path / "to_label.jsonl",
        [
            {"review_id": "t-1", "text": "sudah dilabeli", "label": 0},
            {"review_id": "t-2", "text": "belum dilabeli", "label": None},
        ],
    )
    records = load_labeled_records(path)
    assert len(records) == 1
    assert records[0]["review_id"] == "t-1"


def test_load_labeled_records_rejects_empty_text(tmp_path):
    path = _write_jsonl(
        tmp_path / "train.jsonl",
        [{"id": "real-1", "text": "   ", "label": 0}],
    )
    with pytest.raises(ValueError, match="text"):
        load_labeled_records(path)


def test_load_labeled_records_reports_file_and_line_on_bad_label(tmp_path):
    path = _write_jsonl(
        tmp_path / "train.jsonl",
        [
            {"id": "real-1", "text": "aman", "label": 0},
            {"id": "real-2", "text": "aneh", "label": "mungkin"},
        ],
    )
    with pytest.raises(LabelError) as excinfo:
        load_labeled_records(path)
    assert "train.jsonl" in str(excinfo.value)
    assert "2" in str(excinfo.value)


def test_load_labeled_records_raises_when_file_missing(tmp_path):
    with pytest.raises(FileNotFoundError):
        load_labeled_records(tmp_path / "tidak_ada.jsonl")


def test_label_distribution_counts_both_classes(tmp_path):
    from ml.dataset_io import label_distribution

    path = _write_jsonl(
        tmp_path / "train.jsonl",
        [
            {"text": "a", "label": 0},
            {"text": "b", "label": 1},
            {"text": "c", "label": 1},
        ],
    )
    assert label_distribution(load_labeled_records(path)) == {"asli": 1, "bot": 2}


def test_load_labeled_records_excludes_ragu(tmp_path):
    # Training biner tidak bisa memakai "ragu" (context/09: di-exclude atau
    # ditangani terpisah), tapi barisnya tetap harus terbaca tanpa error.
    path = _write_jsonl(
        tmp_path / "to_label.jsonl",
        [
            {"review_id": "t-1", "text": "bahan jelek.. panas", "label": 0},
            {"review_id": "t-2", "text": "barang bagus, seller ramah..", "label": "ragu"},
            {"review_id": "t-3", "text": "buruan order dijamin puas", "label": 1},
        ],
    )
    records = load_labeled_records(path)
    assert [r["review_id"] for r in records] == ["t-1", "t-3"]
    assert len(load_records(path)) == 3


def test_annotation_summary_reports_all_four_buckets(tmp_path):
    path = _write_jsonl(
        tmp_path / "to_label.jsonl",
        [
            {"text": "a", "label": 0},
            {"text": "b", "label": 1},
            {"text": "c", "label": 1},
            {"text": "d", "label": "ragu"},
            {"text": "e", "label": None},
        ],
    )
    assert annotation_summary(path) == {
        "asli": 1,
        "bot": 2,
        "ragu": 1,
        "belum": 1,
        "total": 5,
    }


def test_annotation_summary_ragu_ratio_is_derivable(tmp_path):
    # Rubrik menargetkan ragu 10-20% dari yang sudah dilabeli; angkanya harus
    # bisa dihitung dari ringkasan ini tanpa membuka berkas lagi.
    path = _write_jsonl(
        tmp_path / "to_label.jsonl",
        [{"text": f"r{i}", "label": "ragu" if i < 2 else 0} for i in range(10)],
    )
    summary = annotation_summary(path)
    sudah = summary["asli"] + summary["bot"] + summary["ragu"]
    assert summary["ragu"] / sudah == pytest.approx(0.2)
