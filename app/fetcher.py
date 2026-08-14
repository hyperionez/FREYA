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

RATING_SOLD_SELECTOR = (
    "#zeus-root > div > div:nth-child(2) > div.css-1s3ezns > div.css-11kmdxw "
    "> div > div > div.css-k3ckr2.e1wfhb0y1 > div > div > p"
)
RATING_SOLD_PATTERN = re.compile(
    r"(?P<rating>[\d.]+)\s*\((?P<rating_count>[\d.,]+)\)\s*•\s*(?P<total_sold>[\d.,]+)\s*terjual"
)


async def fetch_stores(query: str) -> list[dict[str, Any]]:
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
        "location": None,
        "is_official_store": None,
        "rating": rating,
        "review_count": rating_count,
        "total_sold": total_sold,
        "response_rate": None,
        "response_time_minutes": None,
        "store_url": store_url,
        "products": [],
        "reviews": [],
    }


async def _polite_delay() -> None:
    await asyncio.sleep(random.uniform(MIN_DELAY_SECONDS, MAX_DELAY_SECONDS))
