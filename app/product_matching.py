from __future__ import annotations

import re
from typing import Any

from app.embedding_model import encode

QUERY_RELEVANCE_THRESHOLD = 0.5
VARIANT_SIMILARITY_THRESHOLD = 0.70

SPEC_TOKEN_PATTERN = re.compile(r"\d+[a-zA-Z]{1,4}")

CONDITION_KEYWORDS = {
    "baru": "new",
    "new": "new",
    "segel": "new",
    "bnib": "new",
    "second": "used",
    "bekas": "used",
    "seken": "used",
    "used": "used",
}
_WORD_PATTERN = re.compile(r"[a-zA-Z]+")


def _extract_spec_tokens(product_name: str) -> set[str]:
    return {token.lower() for token in SPEC_TOKEN_PATTERN.findall(product_name)}


def _extract_condition_tokens(product_name: str) -> set[str]:
    words = _WORD_PATTERN.findall(product_name.lower())
    return {CONDITION_KEYWORDS[w] for w in words if w in CONDITION_KEYWORDS}


def _has_conflicting_variant(name_a: str, name_b: str) -> bool:
    specs_a, specs_b = _extract_spec_tokens(name_a), _extract_spec_tokens(name_b)
    if specs_a and specs_b and specs_a.isdisjoint(specs_b):
        return True
    condition_a, condition_b = _extract_condition_tokens(name_a), _extract_condition_tokens(name_b)
    if condition_a and condition_b and condition_a.isdisjoint(condition_b):
        return True
    return False


def filter_relevant_products(stores: list[dict[str, Any]], query: str) -> list[dict[str, Any]]:
    all_names = [p["product_name"] for s in stores for p in s.get("products", [])]
    if not all_names:
        return stores

    embeddings = encode([query, *all_names])
    query_embedding, product_embeddings = embeddings[0], embeddings[1:]

    filtered_stores = []
    i = 0
    for store in stores:
        relevant = []
        for product in store.get("products", []):
            similarity = float(query_embedding @ product_embeddings[i])
            i += 1
            if similarity >= QUERY_RELEVANCE_THRESHOLD:
                relevant.append(product)
        filtered_stores.append({**store, "products": relevant})
    return filtered_stores


def group_products_by_variant(stores: list[dict[str, Any]]) -> list[list[dict[str, Any]]]:
    products = [p for s in stores for p in s.get("products", [])]
    if not products:
        return []

    names = [p["product_name"] for p in products]
    embeddings = encode(names)

    n = len(products)
    parent = list(range(n))

    def find(i: int) -> int:
        while parent[i] != i:
            parent[i] = parent[parent[i]]
            i = parent[i]
        return i

    def union(i: int, j: int) -> None:
        root_i, root_j = find(i), find(j)
        if root_i != root_j:
            parent[root_i] = root_j

    for i in range(n):
        for j in range(i + 1, n):
            if _has_conflicting_variant(names[i], names[j]):
                continue
            similarity = float(embeddings[i] @ embeddings[j])
            if similarity >= VARIANT_SIMILARITY_THRESHOLD:
                union(i, j)

    groups: dict[int, list[dict[str, Any]]] = {}
    for i, product in enumerate(products):
        groups.setdefault(find(i), []).append(product)
    return list(groups.values())
