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
    stores = await fetch_stores(query)
    stores = extract_features(stores, query)
    stores = score_stores(stores)
    stores = label_stores(stores)
    stores.sort(key=lambda s: s["scoring"]["score"], reverse=True)
    return {"query": query, "stores": stores}
