"""FastAPI entrypoint (STEP 0/4 of context/02-architecture-ipo.md).

The /search pipeline (fetcher -> features -> scoring -> labeling) lands here
as Fase 1-4 of context/07-roadmap-milestone.md are implemented.
"""
from fastapi import FastAPI

app = FastAPI(title="Fraud Detector MVP")


@app.get("/health")
def health():
    return {"status": "ok"}


@app.get("/search")
def search(query: str):
    # TODO(Fase 1-4): live scraping -> feature extraction -> scoring -> labeling
    return {"query": query, "results": [], "note": "pipeline not yet implemented"}
