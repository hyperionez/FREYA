"""STEP 1 — live scraping (Playwright) / fixture loader (Fase 1, context/07-roadmap-milestone.md).

Data source toggled via the DATA_SOURCE env var: "fixture" (default) or "live".
The live path only implements what's actually been verified against Tokopedia —
see context/10-tokopedia-scraping-notes.md for what's confirmed vs. still open
(response_rate, is_official_store's real meaning, the review list, product
listing). Unconfirmed fields are left None/empty rather than guessed.
"""
from __future__ import annotations

import asyncio
import json
import os
import random
import re
from pathlib import Path
from typing import Any

from playwright.async_api import Page, TimeoutError as PlaywrightTimeoutError, async_playwright

TOKOPEDIA_SEARCH_URL = "https://www.tokopedia.com/search?st=product&q={query}"
FIXTURE_PATH = Path(__file__).resolve().parent.parent / "tests" / "fixtures" / "sample_stores.json"

MIN_DELAY_SECONDS = 1.5
MAX_DELAY_SECONDS = 3.5
MAX_PRODUCTS_TO_SCAN = 20
NAV_TIMEOUT_MS = 15_000

# Combined "5.0 (552) • 199 terjual" text node on a store's Beranda tab.
# Literal selector copied from a live DevTools inspection (context/10-tokopedia-
# scraping-notes.md) — nth-child based, so it's fragile against Tokopedia layout
# changes, but it's what was actually confirmed to work, not a guess.
RATING_SOLD_SELECTOR = (
    "#zeus-root > div > div:nth-child(2) > div.css-1s3ezns > div.css-11kmdxw "
    "> div > div > div.css-k3ckr2.e1wfhb0y1 > div > div > p"
)
RATING_SOLD_PATTERN = re.compile(
    r"(?P<rating>[\d.]+)\s*\((?P<rating_count>[\d.,]+)\)\s*•\s*(?P<total_sold>[\d.,]+)\s*terjual"
)


async def fetch_stores(query: str) -> list[dict[str, Any]]:
    """STEP 1 entry point. Returns raw Store dicts (context/03-data-schema.md),
    each with nested "products" and "reviews" — same shape as the fixture file."""
    data_source = os.getenv("DATA_SOURCE", "fixture")
    if data_source == "fixture":
        return _load_fixture()
    return await _fetch_live(query)


def _load_fixture() -> list[dict[str, Any]]:
    if not FIXTURE_PATH.exists():
        return []
    data = json.loads(FIXTURE_PATH.read_text(encoding="utf-8"))
    return data.get("stores", [])


async def _fetch_live(query: str) -> list[dict[str, Any]]:
    stores: list[dict[str, Any]] = []
    seen_store_urls: set[str] = set()

    async with async_playwright() as pw:
        browser = await pw.chromium.launch(headless=True)
        page = await browser.new_page()
        page.set_default_timeout(NAV_TIMEOUT_MS)

        try:
            store_urls = await _collect_store_urls(page, query, seen_store_urls)
        except Exception:
            
            store_urls = []

        for store_url in store_urls:
            try:
                store = await _scrape_store(page, store_url)
                if store:
                    stores.append(store)
            except Exception:
                continue
            await _polite_delay()

        await browser.close()

    return stores


async def _collect_store_urls(page: Page, query: str, seen: set[str]) -> list[str]:
    """Search -> product results -> follow each product to its store page,
    de-duplicating by store URL.

    context/10-tokopedia-scraping-notes.md documents a `btnSRPShopTab` data-testid
    that switches search results to store results directly, which is probably a
    faster path than this one — not used here yet because its own result-link
    selectors were never verified. This function only uses the confirmed path.
    """
    await page.goto(TOKOPEDIA_SEARCH_URL.format(query=query.replace(" ", "%20")))
    await _polite_delay()


    product_links = page.get_by_role("link", name=re.compile(r"^product-image"))
    count = min(await product_links.count(), MAX_PRODUCTS_TO_SCAN)
    product_hrefs = []
    for i in range(count):
        href = await product_links.nth(i).get_attribute("href")
        if href:
            product_hrefs.append(href)

    store_urls: list[str] = []
    for href in product_hrefs:
        try:
            await page.goto(href)

            heading = page.get_by_role("heading").first
            if await heading.count() == 0:
                continue
            async with page.expect_navigation(timeout=NAV_TIMEOUT_MS):
                await heading.click()
            store_url = page.url
            if store_url not in seen:
                seen.add(store_url)
                store_urls.append(store_url)
        except Exception:
            continue
        await _polite_delay()

    return store_urls


async def _scrape_store(page: Page, store_url: str) -> dict[str, Any] | None:
    """KNOWN GAPS (context/10-tokopedia-scraping-notes.md) — left as None/empty
    rather than guessed at:
      - location: no selector found yet.
      - is_official_store: the green checkmark badge next to the store name is
        the likely candidate, but its exact meaning (official store vs. some
        other seller-tier badge) was never confirmed — not implemented rather
        than risk a wrong TRUE/FALSE.
      - response_rate / response_time_minutes: not located anywhere on the
        Beranda tab or the Info Toko dialog.
      - store_age_days: intentionally not scraped — dropped from the schema
        entirely (context/04-fraud-signal-features.md, 2026-08-11 decision;
        Tokopedia doesn't expose it anywhere).
      - products / reviews: STEP 1 review-list scraping (20-30 reviews/store,
        context/02-architecture-ipo.md) isn't implemented yet — the `Ulasan`
        tab structure hasn't been captured.
    """
    await page.goto(store_url)

    store_id = store_url.rstrip("/").rsplit("/", 1)[-1]

    name_el = page.get_by_role("heading").first
    store_name = (await name_el.text_content() or "").strip() if await name_el.count() > 0 else ""

    rating: float | None = None
    rating_count: int | None = None
    total_sold: int | None = None
    rating_sold_el = page.locator(RATING_SOLD_SELECTOR).first
    if await rating_sold_el.count() > 0:
        text = await rating_sold_el.text_content() or ""
        m = RATING_SOLD_PATTERN.search(text)
        if m:
            rating = float(m.group("rating"))
            rating_count = int(m.group("rating_count").replace(".", "").replace(",", ""))
            total_sold = int(m.group("total_sold").replace(".", "").replace(",", ""))

    return {
        "store_id": store_id,
        "store_name": store_name,
        "marketplace": "tokopedia",
        "location": None,  # TODO: selector not found yet
        "is_official_store": None,  # TODO: badge meaning unconfirmed, see docstring
        "rating": rating,

        "review_count": rating_count,
        "total_sold": total_sold,
        "response_rate": None,  # TODO: not found yet
        "response_time_minutes": None,  # TODO: not found yet
        "store_url": store_url,
        "products": [],  # TODO: not implemented yet
        "reviews": [],  # TODO: not implemented yet — Ulasan tab structure unknown
    }


async def _polite_delay() -> None:
    """Rate limiting between requests, per context/07-roadmap-milestone.md Fase 1."""
    await asyncio.sleep(random.uniform(MIN_DELAY_SECONDS, MAX_DELAY_SECONDS))
