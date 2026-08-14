from app.scoring import score_store


def test_no_data_scores_baseline():
    result = score_store({})
    assert result["score"] == 50


def test_price_deviation_severe_drop():
    result = score_store({"price_deviation": -0.6})
    contribution = _contribution(result, "price_deviation")
    assert contribution == -20


def test_price_deviation_moderate_drop():
    result = score_store({"price_deviation": -0.4})
    assert _contribution(result, "price_deviation") == -12


def test_price_deviation_mild_drop():
    result = score_store({"price_deviation": -0.2})
    assert _contribution(result, "price_deviation") == -5


def test_price_deviation_within_market_range():
    result = score_store({"price_deviation": -0.05})
    assert _contribution(result, "price_deviation") == 0


def test_price_deviation_missing_is_neutral():
    result = score_store({"price_deviation": None})
    assert _contribution(result, "price_deviation") == 0


def test_low_review_count_penalized_regardless_of_rating():
    result = score_store({"rating": 5.0, "review_count": 3})
    assert _contribution(result, "rating_review") == -10


def test_excellent_rating_with_enough_reviews():
    result = score_store({"rating": 4.7, "review_count": 50})
    assert _contribution(result, "rating_review") == 15


def test_good_rating_with_enough_reviews():
    result = score_store({"rating": 4.2, "review_count": 50})
    assert _contribution(result, "rating_review") == 8


def test_poor_rating_with_enough_reviews():
    result = score_store({"rating": 2.5, "review_count": 50})
    assert _contribution(result, "rating_review") == -20


def test_middling_rating_is_neutral():
    result = score_store({"rating": 3.5, "review_count": 50})
    assert _contribution(result, "rating_review") == 0


def test_official_store_bonus():
    result = score_store({"is_official_store": True})
    assert _contribution(result, "is_official_store") == 10


def test_non_official_store_no_penalty():
    result = score_store({"is_official_store": False})
    assert _contribution(result, "is_official_store") == 0


def test_unknown_official_status_no_penalty():
    result = score_store({"is_official_store": None})
    assert _contribution(result, "is_official_store") == 0


def test_low_response_rate_penalized():
    result = score_store({"response_rate": 0.2})
    assert _contribution(result, "response_rate") == -5


def test_healthy_response_rate_no_penalty():
    result = score_store({"response_rate": 0.9})
    assert _contribution(result, "response_rate") == 0


def test_low_total_sold_with_deep_discount_penalized():
    result = score_store({"total_sold": 3, "price_deviation": -0.4})
    assert _contribution(result, "total_sold") == -5


def test_low_total_sold_without_discount_no_penalty():
    result = score_store({"total_sold": 3, "price_deviation": -0.05})
    assert _contribution(result, "total_sold") == 0


def test_healthy_total_sold_no_penalty_even_with_discount():
    result = score_store({"total_sold": 500, "price_deviation": -0.6})
    assert _contribution(result, "total_sold") == 0


def test_review_authenticity_very_low():
    result = score_store({"review_authenticity_score": 10})
    assert _contribution(result, "review_authenticity") == -20


def test_review_authenticity_low():
    result = score_store({"review_authenticity_score": 45})
    assert _contribution(result, "review_authenticity") == -8


def test_review_authenticity_high():
    result = score_store({"review_authenticity_score": 90})
    assert _contribution(result, "review_authenticity") == 10


def test_review_authenticity_middling_is_neutral():
    result = score_store({"review_authenticity_score": 70})
    assert _contribution(result, "review_authenticity") == 0


def test_perfect_rating_with_bot_reviews_overrides_to_negative():
    result = score_store({"rating": 5.0, "review_count": 10, "review_authenticity_score": 20})
    assert _contribution(result, "rating_review") == -15
    assert result["score"] == 15


def test_perfect_rating_with_clean_reviews_keeps_bonus():
    result = score_store({"rating": 5.0, "review_count": 10, "review_authenticity_score": 90})
    assert _contribution(result, "rating_review") == 15


def test_high_review_count_with_bot_reviews_overrides_to_deeper_negative():
    result = score_store({"review_count": 5000, "review_authenticity_score": 40})
    assert _contribution(result, "review_authenticity") == -15


def test_worst_case_signals_clamp_at_zero():
    result = score_store(
        {
            "price_deviation": -0.9,
            "rating": 2.0,
            "review_count": 1000,
            "is_official_store": False,
            "response_rate": 0.1,
            "total_sold": 3,
            "review_authenticity_score": 5,
        }
    )
    assert result["score"] == 0


def test_best_case_signals_stay_within_range():
    result = score_store(
        {
            "rating": 4.9,
            "review_count": 500,
            "is_official_store": True,
            "response_rate": 0.99,
            "review_authenticity_score": 95,
        }
    )
    assert 0 <= result["score"] <= 100
    assert result["score"] == 85


def _contribution(result, signal):
    for entry in result["contributions"]:
        if entry["signal"] == signal:
            return entry["contribution"]
    raise AssertionError(f"no contribution found for signal {signal!r}")
