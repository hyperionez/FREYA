# Tech Stack — MVP (Final)

## 1. Backend / Core Logic
- **Bahasa**: Python
- **Framework API**: FastAPI
- **HTTP/scraping client**: **Playwright** — wajib karena marketplace target JS-rendered, bukan static HTML.

## 2. Data Layer
- **Live data**: stateless per-request (Track A) — tidak perlu database besar.
- **Cache**: SQLite (`store_id` → hasil Review Analysis, dengan TTL) — hindari re-scraping/re-analisis toko yang sama berulang.
- **Fixture**: `tests/fixtures/sample_stores.json` — mode sekunder untuk testing/showcase, toggle via `DATA_SOURCE=live|fixture`.

## 3. Scoring Engine (Rule-Based)
- Pure Python, tanpa library ML apapun.
- Bobot/threshold di `config.yaml`, mudah dikalibrasi ulang.

## 4. Modul Review Analysis
| Kebutuhan | Tools | Catatan |
|---|---|---|
| Scraping review | Playwright | 20-30 review/toko |
| Embedding | `sentence-transformers` (`paraphrase-multilingual-MiniLM-L12-v2`) | Lokal, multilingual (Bahasa Indonesia), dipakai dobel: dedup (Lapis 1) + RAG retrieval |
| Near-duplicate detection | Cosine similarity antar embedding | Lapis 1, selalu jalan, tanpa API call |
| Vector store RAG | Chroma (lokal) | 2 collection: review embeddings (ephemeral) + knowledge base pola fraud (persisten) |
| LLM API (opsional, Lapis 2) | Google Gemini API | 1 call per toko, structured JSON output, hanya untuk kasus ambigu |

## 5. Track B — Annotation & Fine-Tuning
| Kebutuhan | Tools | Catatan |
|---|---|---|
| Annotation tool | Streamlit | Tampilkan review + top-k pola RAG untuk bantu annotator |
| Base model | IndoBERT (`indobenchmark/indobert-base-p1`) | Sudah terlatih Bahasa Indonesia |
| Training | HuggingFace `transformers` + `datasets` | Jalan di Google Colab, tidak perlu infra GPU permanen |
| Inference (setelah jadi) | CPU | Model classifier kecil, tidak butuh GPU di production |

## 6. Frontend / Interface MVP
- **Streamlit** — form input + tabel output, cepat untuk demo tanpa perlu frontend engineering.

## 7. Deployment (demo/testing)
- Lokal: `uvicorn` + `streamlit run`.
- Kalau perlu publik: Railway/Render/Fly.io (free tier cukup untuk MVP kecil).

## 8. Yang Sengaja Tidak Dipakai di MVP
- ❌ Kubernetes / container orchestration
- ❌ Message queue (Kafka/RabbitMQ)
- ❌ GPU infra permanen di production (training cukup sesekali di Colab; inference model kecil cukup CPU)
- ❌ Fine-tuning LLM besar (Gemini/GPT) — diganti classifier kecil (IndoBERT) khusus task sempit
- ❌ Microservices — satu service monolitik kecil sudah cukup
- ❌ Auth/user account system

## 9. Struktur Folder Rekomendasi

```
fraud-detector-mvp/
├── app/
│   ├── main.py                  # FastAPI entrypoint
│   ├── fetcher.py                # STEP 1: live scraping (Playwright) / fixture loader
│   ├── features.py                # STEP 2: feature extraction numerik
│   ├── review_analysis/
│   │   ├── embedding.py           # embed review, dedup (Lapis 1)
│   │   ├── rag_retrieval.py       # retrieval pola fraud (Chroma)
│   │   └── llm_analysis.py        # LLM call Lapis 2 (opsional, kasus ambigu)
│   ├── scoring.py                 # STEP 3: rule-based scoring engine
│   ├── labeling.py                # STEP 4: mapping skor -> label + reasons
│   └── config.yaml                # bobot & threshold
├── track_b/
│   ├── annotation_app.py          # Streamlit annotation tool
│   ├── train_classifier.py        # fine-tuning IndoBERT
│   └── data/annotations.jsonl     # dataset hasil anotasi manual
├── frontend/
│   └── streamlit_app.py
├── tests/
│   ├── fixtures/sample_stores.json
│   └── test_scoring.py
└── requirements.txt
```
