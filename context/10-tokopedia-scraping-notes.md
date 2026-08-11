# Tokopedia Scraping Notes (Fase 0)

Captured 2026-08-10 via `playwright codegen https://www.tokopedia.com` (manual session, browser automation to Tokopedia is off-limits for Claude — see `CLAUDE.md`). Raw recording: `.scratch/tokopedia_codegen.py` (gitignored, not committed — regenerate if needed).

## Confirmed URL patterns
- Search results: `https://www.tokopedia.com/search?st=product&q=<url-encoded query>`
- Store page: `https://www.tokopedia.com/<store-slug>` — flat slug, e.g. `https://www.tokopedia.com/hobimac`. Not nested under `/search` or `/store`.

## Navigation flow to reach a store (for `fetcher.py`)
1. `goto` search URL for the query.
2. Click a product result link (role `link`, accessible name pattern: `"product-image " + <product title>` — **not stable**, changes per product; use as a locator pattern, not a hardcoded string).
3. On the Product Detail Page (PDP), the store name renders as a `heading` — click it to navigate to the store's own page (`tokopedia.com/<slug>`).
4. On the store page, a `Produk` link/tab shows the store's full product listing. A `Beranda` (home/overview) tab is implied but not directly exercised in this session — **that's where store stats (age, rating, review_count, official badge, response_rate) most likely live**, still needs a follow-up pass to find selectors for those specific text/badge elements.

## Alternate path: search results has its own Shop tab
The search results page (`/search?...`) has two tabs, found as stable `data-testid`s:
- `btnSRPProductTab` — product results (default)
- `btnSRPShopTab` — **store results directly**, i.e. searching stores by name instead of drilling in via a product. Worth evaluating as a faster/more direct path to a store list than product → PDP → store, if `fetcher.py` needs to enumerate many stores per query.

## Stable selectors found (data-testid based — prefer these over text-role selectors)
| testid | Where | Purpose |
|---|---|---|
| `btnSRPProductTab` | Search results | Switch to product results |
| `btnSRPShopTab` | Search results | Switch to store results |
| `btnPDPSeeMore` | Product page | Expand product description |
| `pdpVariantContainer` | Product page | Product variant picker (container) |
| `btnVariantChipActive` | Product page | Active variant chip within the picker |

Text-role selectors (`get_by_role("link", name="...")`, `get_by_role("heading", name="...")`) worked in this session but are **not safe to hardcode** — the accessible name includes the product/store's own title, which is different every time. Use these only as a locator *pattern* (e.g. "the first `link` role inside the results grid"), not a literal string match.

## Store `Beranda` tab — confirmed layout (live screenshot, `tokopedia.com/hobimac`, 2026-08-10)

Header card, top of the store page:
- Store logo + a green checkmark badge next to the store name — likely `is_official_store` indicator, not yet confirmed by clicking it.
- Store name (`Hobi Mac`) + location (`Kab. Sleman`).
- Buttons: `Follow`, `Chat Penjual`, and two icon-only buttons (one of these opens the `Info Toko` dialog, `data-testid="btnShopDetail"` — see below).
- Right-aligned: `★ 5.0 (552) • 199 terjual`, with a `Rating & Ulasan` link underneath that opens a rating-breakdown modal (star histogram + `% pembeli merasa puas`).
- Tabs below the card: `Beranda` / `Produk` / `Ulasan`.
- Below the tabs: a `Produk Terlaris` (best-selling products) grid — not store metadata, just a product listing.

Selector for the rating/review count text node:
```
#zeus-root > div > div:nth-child(2) > div.css-1s3ezns > div.css-11kmdxw > div > div > div.css-k3ckr2.e1wfhb0y1 > div > div > p
```
This is the `5.0 (552) • 199 terjual` combined text — parsing it in code needs a regex/split, it's not separate fields in the DOM (rating value, rating count, and sold count are all in one `<p>`).

**`review_count` vs rating count are NOT the same number.** The rating-breakdown modal shows `552 rating • 278 ulasan` — 552 people left a star rating, but only 278 left a written review (ulasan). `context/03-data-schema.md`'s `review_count` field needs a decision on which of these two numbers it means, since scraping 20-30 *review texts* (`context/02-architecture-ipo.md`) implies the 278 (ulasan) count is the relevant one, not 552.

## ⚠️ `store_age_days` is NOT available in the `Info Toko` dialog

Checked directly: the `Info Toko` dialog (opened via `btnShopDetail`) contains **only store description and store notes ("catatan toko") — no join date, no "bergabung sejak," no store age anywhere.**

Dialog content container selector:
```
body > div:nth-child(44) > div.css-1mcbo0u.e1nc1fa20 > article > div > div.css-1rwcaap > div
```

This is a real gap against the spec, not just a missing selector: `context/03-data-schema.md`'s `Store` entity has `store_age_days`, and `context/04-fraud-signal-features.md` weights it at **15 points** in the scoring formula (`score_store_age()`, new store < 30 days → penalty, > 1 year → bonus) — a meaningful chunk of the total. If Tokopedia's current UI genuinely doesn't expose this anywhere, the team needs to decide: drop the signal, find another proxy (e.g. earliest product listing date as an estimate, if that's discoverable), or redistribute its 15-point weight across the other signals. Flagging this now rather than silently deciding for the team — this is a spec/scoring decision, not a scraping detail.

Also still unconfirmed: **`response_rate`** and **`response_time_minutes`** — not seen in the header card or the `Info Toko` dialog so far. Possibly on the `Chat Penjual` flow itself (some marketplaces only reveal response rate when you open a chat), or genuinely not exposed either. Needs a check.

## Still needed before `fetcher.py` (Fase 1) can be written
- [x] `rating` (value) + rating count — combined in one `<p>`, selector above.
- [x] `total_sold` — same `<p>`, `199 terjual`.
- [ ] `is_official_store` — the green checkmark badge is the likely candidate, needs a hover/click to confirm what it actually indicates (could just be "Power Merchant" or similar tier, not literally "official").
- [ ] `response_rate` / `response_time_minutes` — not found yet, may not be exposed on this UI at all.
- [x] ~~`store_age_days`~~ — **confirmed NOT available in Info Toko.** Needs a product-decision on how to handle (see above), not just more scraping.
- [ ] Selectors for the review list itself (20-30 reviews/store per `context/02-architecture-ipo.md`) — the `Ulasan` tab/link hasn't been drilled into yet, only the rating-breakdown modal.

Next step: check the green badge (what does it say on hover/click?) and the `Ulasan` tab (review list structure — text, reviewer name/rating, posted_at). `response_rate` may need checking inside the `Chat Penjual` flow.
