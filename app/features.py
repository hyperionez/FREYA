from __future__ import annotations

from statistics import median
from typing import Any

from app.product_matching import filter_relevant_products, group_products_by_variant
from app.review_analysis import get_review_authenticity_score


def extract_features(stores: list[dict[str, Any]], query: str) -> list[dict[str, Any]]:
    relevant_stores = filter_relevant_products(stores, query)
    variant_groups = group_products_by_variant(relevant_stores)
    group_median_by_product_id = _group_median_by_product_id(variant_groups)
    return [_extract_store_features(store, group_median_by_product_id) for store in relevant_stores]


def _group_median_by_product_id(variant_groups: list[list[dict[str, Any]]]) -> dict[str, float | None]:
    result: dict[str, float | None] = {}
    for group in variant_groups:
        prices = [p["price"] for p in group if p.get("price") is not None]
        group_median = median(prices) if len(prices) >= 2 else None
        for product in group:
            result[product["product_id"]] = group_median
    return result


def _extract_store_features(
    store: dict[str, Any], group_median_by_product_id: dict[str, float | None]
) -> dict[str, Any]:
    products = store.get("products", [])
    store_product = products[0] if products else None
    store_price = store_product["price"] if store_product and store_product.get("price") is not None else None

    price_deviation = None
    if store_product is not None and store_price is not None:
        group_median = group_median_by_product_id.get(store_product["product_id"])
        if group_median:
            price_deviation = (store_price - group_median) / group_median

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
