from __future__ import annotations

from pathlib import Path
from typing import Any

import yaml

CONFIG_PATH = Path(__file__).resolve().parent / "config.yaml"
_CONFIG: dict[str, Any] = yaml.safe_load(CONFIG_PATH.read_text(encoding="utf-8"))


def score_stores(stores: list[dict[str, Any]]) -> list[dict[str, Any]]:
    return [{**store, "scoring": score_store(store["features"])} for store in stores]


def score_store(features: dict[str, Any]) -> dict[str, Any]:
    contributions = {
        "price_deviation": _score_price_deviation(features.get("price_deviation")),
        "rating_review": _score_rating_review(features.get("rating"), features.get("review_count")),
        "is_official_store": _score_is_official_store(features.get("is_official_store")),
        "response_rate": _score_response_rate(features.get("response_rate")),
        "total_sold": _score_total_sold(features.get("total_sold"), features.get("price_deviation")),
        "review_authenticity": _score_review_authenticity(features.get("review_authenticity_score")),
    }

    _apply_compound_overrides(contributions, features)

    total = _CONFIG["baseline"] + sum(c["contribution"] for c in contributions.values())
    total = max(0, min(100, round(total)))

    return {
        "score": total,
        "contributions": [{"signal": signal, **detail} for signal, detail in contributions.items()],
    }


def _score_price_deviation(deviation: float | None) -> dict[str, Any]:
    if deviation is None:
        return {"contribution": 0, "detail": "Data harga tidak tersedia"}
    for t in _CONFIG["price_deviation"]["thresholds"]:
        if deviation <= t["max_deviation"]:
            return {
                "contribution": t["contribution"],
                "detail": f"Harga {abs(deviation) * 100:.0f}% di bawah median pasar",
            }
    return {"contribution": 0, "detail": "Harga sesuai kisaran pasar"}


def _score_rating_review(rating: float | None, review_count: int | None) -> dict[str, Any]:
    cfg = _CONFIG["rating_review"]
    if review_count is not None and review_count < cfg["min_review_count"]:
        return {
            "contribution": cfg["low_review_count_contribution"],
            "detail": f"Review sangat sedikit ({review_count})",
        }
    if rating is None:
        return {"contribution": 0, "detail": "Data rating tidak tersedia"}
    for t in cfg["rating_thresholds"]:
        if rating >= t["min_rating"]:
            return {"contribution": t["contribution"], "detail": f"Rating toko tinggi ({rating})"}
    if rating < cfg["low_rating"]["max_rating"]:
        return {
            "contribution": cfg["low_rating"]["contribution"],
            "detail": f"Rating toko rendah ({rating})",
        }
    return {"contribution": 0, "detail": f"Rating toko standar ({rating})"}


def _score_is_official_store(is_official: bool | None) -> dict[str, Any]:
    cfg = _CONFIG["is_official_store"]
    if is_official is True:
        return {"contribution": cfg["contribution"], "detail": "Toko berstatus official/verified"}
    if is_official is False:
        return {"contribution": 0, "detail": "Toko bukan official store"}
    return {"contribution": 0, "detail": "Status official toko tidak diketahui"}


def _score_response_rate(response_rate: float | None) -> dict[str, Any]:
    cfg = _CONFIG["response_rate"]
    if response_rate is None:
        return {"contribution": 0, "detail": "Data response rate tidak tersedia"}
    if response_rate < cfg["low_threshold"]:
        return {
            "contribution": cfg["contribution"],
            "detail": f"Response rate rendah ({response_rate * 100:.0f}%)",
        }
    return {"contribution": 0, "detail": f"Response rate wajar ({response_rate * 100:.0f}%)"}


def _score_total_sold(total_sold: int | None, price_deviation: float | None) -> dict[str, Any]:
    cfg = _CONFIG["total_sold"]
    if total_sold is None:
        return {"contribution": 0, "detail": "Data total terjual tidak tersedia"}
    if (
        total_sold < cfg["low_threshold"]
        and price_deviation is not None
        and price_deviation <= cfg["requires_price_deviation_at_most"]
    ):
        return {
            "contribution": cfg["contribution"],
            "detail": f"Transaksi sangat sedikit ({total_sold}) untuk harga jauh di bawah pasar",
        }
    return {"contribution": 0, "detail": f"Total terjual: {total_sold}"}


def _score_review_authenticity(authenticity_score: int | None) -> dict[str, Any]:
    cfg = _CONFIG["review_authenticity"]
    if authenticity_score is None:
        return {"contribution": 0, "detail": "review_authenticity_score tidak tersedia"}
    if authenticity_score < cfg["low_threshold"]:
        return {
            "contribution": cfg["low_contribution"],
            "detail": f"review_authenticity_score sangat rendah ({authenticity_score})",
        }
    if authenticity_score < cfg["mid_threshold"]:
        return {
            "contribution": cfg["mid_contribution"],
            "detail": f"review_authenticity_score rendah ({authenticity_score})",
        }
    if authenticity_score >= cfg["high_threshold"]:
        return {
            "contribution": cfg["high_contribution"],
            "detail": f"review_authenticity_score tinggi ({authenticity_score})",
        }
    return {"contribution": 0, "detail": f"review_authenticity_score standar ({authenticity_score})"}


def _apply_compound_overrides(contributions: dict[str, dict[str, Any]], features: dict[str, Any]) -> None:
    rating = features.get("rating")
    review_count = features.get("review_count")
    authenticity = features.get("review_authenticity_score")
    cfg = _CONFIG["compound_rules"]

    if rating is not None and authenticity is not None:
        rule = cfg["perfect_rating_low_authenticity"]
        if rating >= rule["rating_at_least"] and authenticity < rule["authenticity_below"]:
            contributions["rating_review"] = {
                "contribution": rule["contribution"],
                "detail": (
                    f"Rating sempurna ({rating}) tapi review_authenticity_score rendah "
                    f"({authenticity}) — indikasi review dibeli/bot"
                ),
            }

    if review_count is not None and authenticity is not None:
        rule = cfg["high_review_count_low_authenticity"]
        if review_count >= rule["review_count_at_least"] and authenticity < rule["authenticity_below"]:
            contributions["review_authenticity"] = {
                "contribution": rule["contribution"],
                "detail": (
                    f"{review_count} review tapi review_authenticity_score rendah ({authenticity}) "
                    "— volume besar tidak otomatis kredibel"
                ),
            }
