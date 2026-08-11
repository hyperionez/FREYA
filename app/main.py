from fastapi import FastAPI

from app.fetcher import fetch_stores

app = FastAPI(title="Fraud Detector MVP")


@app.get("/health")
def health():
    return {"status": "ok"}


@app.get("/search")
async def search(query: str):
    # STEP 1 (fetch) is wired up; STEP 2-4 (feature extraction, scoring,
    # labeling) aren't implemented yet (Fase 2-3, context/07-roadmap-milestone.md)
    # so this returns raw fetched stores, not the final scored/labeled output.
    stores = await fetch_stores(query)
    return {"query": query, "stores": stores, "note": "scoring/labeling not yet implemented"}
