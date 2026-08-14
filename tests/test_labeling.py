from app.labeling import label_store, label_stores


def _scoring(score, contributions=None):
    return {"score": score, "contributions": contributions or []}


def test_score_at_aman_threshold_is_aman():
    result = label_store(_scoring(75))
    assert result["label"] == "Aman"


def test_score_above_aman_threshold_is_aman():
    result = label_store(_scoring(100))
    assert result["label"] == "Aman"


def test_score_just_below_aman_threshold_is_waspada():
    result = label_store(_scoring(74))
    assert result["label"] == "Waspada"


def test_score_at_waspada_threshold_is_waspada():
    result = label_store(_scoring(40))
    assert result["label"] == "Waspada"


def test_score_just_below_waspada_threshold_is_berbahaya():
    result = label_store(_scoring(39))
    assert result["label"] == "Berbahaya"


def test_score_at_zero_is_berbahaya():
    result = label_store(_scoring(0))
    assert result["label"] == "Berbahaya"


def test_significant_contributions_become_reasons():
    contributions = [
        {"signal": "price_deviation", "contribution": -20, "detail": "harga jauh di bawah pasar"},
        {"signal": "is_official_store", "contribution": 10, "detail": "toko official"},
    ]
    result = label_store(_scoring(40, contributions))
    assert result["reasons"] == ["harga jauh di bawah pasar", "toko official"]


def test_insignificant_contributions_are_excluded():
    contributions = [
        {"signal": "response_rate", "contribution": -5, "detail": "response rate rendah"},
        {"signal": "total_sold", "contribution": 0, "detail": "total terjual wajar"},
    ]
    result = label_store(_scoring(50, contributions))
    assert result["reasons"] == ["Tidak ada sinyal signifikan terdeteksi — skor mendekati baseline netral"]


def test_reasons_sorted_by_magnitude_descending():
    contributions = [
        {"signal": "is_official_store", "contribution": 10, "detail": "toko official"},
        {"signal": "price_deviation", "contribution": -20, "detail": "harga jauh di bawah pasar"},
        {"signal": "review_authenticity", "contribution": -15, "detail": "review mencurigakan"},
    ]
    result = label_store(_scoring(30, contributions))
    assert result["reasons"] == [
        "harga jauh di bawah pasar",
        "review mencurigakan",
        "toko official",
    ]


def test_label_stores_adds_assessment_per_store():
    stores = [
        {"store_id": "s1", "scoring": _scoring(90)},
        {"store_id": "s2", "scoring": _scoring(20)},
    ]
    result = label_stores(stores)
    assert result[0]["assessment"]["label"] == "Aman"
    assert result[1]["assessment"]["label"] == "Berbahaya"


def test_label_stores_preserves_other_store_fields():
    stores = [{"store_id": "s1", "store_name": "Toko A", "scoring": _scoring(90)}]
    result = label_stores(stores)
    assert result[0]["store_name"] == "Toko A"
