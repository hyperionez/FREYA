"""STEP 2 — feature extraction (Fase 2, context/07-roadmap-milestone.md).

Two parallel paths per context/02-architecture-ipo.md §2: numeric features
computed straight from raw Store/Product data (no AI), and
review_authenticity_score from the Review Analysis module (AI-assisted,
because its input — free-text reviews — is unstructured). Both land in the
same per-store "features" dict, which STEP 3 (scoring.py, not implemented
yet) will consume uniformly.
"""
from __future__ import annotations

from statistics import median
from typing import Any

from app.review_analysis.embedding import get_review_authenticity_score


def extract_features(stores: list[dict[str, Any]]) -> list[dict[str, Any]]:
    """STEP 2 entry point. Returns each store with an added "features" dict."""
    market_median_price = _market_median_price(stores)
    return [_extract_store_features(store, market_median_price) for store in stores]


def _market_median_price(stores: list[dict[str, Any]]) -> float | None:
    prices = [
        product["price"]
        for store in stores
        for product in store.get("products", [])
        if product.get("price") is not None
    ]
    return median(prices) if prices else None


def _extract_store_features(store: dict[str, Any], market_median_price: float | None) -> dict[str, Any]:
    products = store.get("products", [])
    store_price = products[0]["price"] if products and products[0].get("price") is not None else None

    price_deviation = None
    if store_price is not None and market_median_price:
        price_deviation = (store_price - market_median_price) / market_median_price

    review_analysis = get_review_authenticity_score(store["store_id"], store.get("reviews", []))

    features = {
        "price": store_price,
        "price_deviation": price_deviation,
        "rating": store.get("rating"),
        "review_count": store.get("review_count"),
        "is_official_store": store.get("is_official_store"),
        "response_rate": store.get("response_rate"),
        "total_sold": store.get("total_sold"),
        "review_authenticity_score": review_analysis["score"],
        "review_authenticity_source": review_analysis["source"],
        "review_authenticity_reasons": review_analysis["reasons"],
    }

    return {**store, "features": features}
