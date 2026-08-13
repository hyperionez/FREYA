from fastapi import FastAPI

from app.features import extract_features
from app.fetcher import fetch_stores
from app.labeling import label_stores
from app.scoring import score_stores

app = FastAPI(title="Fraud Detector MVP")


@app.get("/health")
def health():
    return {"status": "ok"}


@app.get("/search")
async def search(query: str):
    # STEP 1-4 (fetch, feature extraction, scoring, labeling) are all wired
    # up — this is the full Track A pipeline (context/02-architecture-ipo.md).
    # Sorted by score descending per the Output contract there.
    stores = await fetch_stores(query)
    stores = extract_features(stores)
    stores = score_stores(stores)
    stores = label_stores(stores)
    stores.sort(key=lambda s: s["scoring"]["score"], reverse=True)
    return {"query": query, "stores": stores}
