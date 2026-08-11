# Data Schema — MVP

## 1. Entity: Store (Toko)

```json
{
  "store_id": "string",
  "store_name": "string",
  "marketplace": "string (contoh: 'tokopedia')",
  "location": "string",
  "is_official_store": "boolean",
  "rating": "float (0-5)",
  "review_count": "integer",
  "total_sold": "integer",
  "response_rate": "float (0-1)",
  "response_time_minutes": "integer | null",
  "store_url": "string"
}
```

## 2. Entity: Product (Produk hasil pencarian)

```json
{
  "product_id": "string",
  "store_id": "string",
  "product_name": "string",
  "price": "integer",
  "product_rating": "float (0-5)",
  "product_review_count": "integer",
  "product_url": "string"
}
```

## 3. Entity: Review (baru — untuk Modul Review Analysis)

```json
{
  "review_id": "string",
  "store_id": "string",
  "text": "string",
  "posted_at": "datetime (ISO 8601)",
  "reviewer_rating": "integer (1-5) | null"
}
```
- Diambil 20-30 review per toko saat live scraping.
- `text` adalah input utama untuk embedding (dedup) dan, kalau perlu, analisis LLM.

## 4. Entity: Review Analysis Result (output Modul Review Analysis)

```json
{
  "store_id": "string",
  "review_authenticity_score": "integer (0-100)",
  "source": "enum ['heuristic_l1', 'llm_l2', 'finetuned_model']",
  "reasons": [
    "string (contoh: '6 dari 25 review terdeteksi near-duplicate dengan similarity > 0.9')"
  ],
  "analyzed_at": "datetime (ISO 8601)"
}
```
- `source` menandai apakah skor berasal dari heuristik Lapis 1, LLM Lapis 2, atau model fine-tuned Track B — berguna untuk debugging & evaluasi kualitas per sumber.

## 5. Entity: Fraud Assessment (Hasil Labeling Akhir)

```json
{
  "store_id": "string",
  "score": "integer (0-100)",
  "label": "enum ['Aman', 'Waspada', 'Berbahaya']",
  "reasons": [
    "string (contoh: 'Harga 55% di bawah median pasar')",
    "string (contoh: 'Belum ada ulasan')",
    "string (contoh: '24% review terindikasi bot')"
  ],
  "evaluated_at": "datetime (ISO 8601)"
}
```

## 6. Contoh Response API End-to-End

```json
{
  "query": "iphone 13 second",
  "results": [
    {
      "store_name": "Toko Gadget Terpercaya",
      "product_name": "iPhone 13 128GB Second Original",
      "price": 6500000,
      "label": "Aman",
      "score": 82,
      "reasons": [
        "Rating toko 4.9 dari 3.200 ulasan",
        "Harga sesuai kisaran pasar (median: 6.7jt)",
        "Toko berstatus official/verified",
        "Review authenticity score 91/100 — pola review wajar"
      ],
      "store_url": "https://..."
    },
    {
      "store_name": "iphonemurahbanget99",
      "product_name": "iPhone 13 Second Mulus",
      "price": 2100000,
      "label": "Berbahaya",
      "score": 18,
      "reasons": [
        "Harga 68% di bawah median pasar",
        "Belum ada ulasan",
        "Tidak ada status verifikasi toko"
      ],
      "store_url": "https://..."
    }
  ]
}
```

## 7. Entity Khusus Track B: Annotation Record

```json
{
  "review_id": "string",
  "text": "string",
  "retrieved_patterns": ["string (top-k pola fraud dari RAG, ditampilkan ke annotator)"],
  "label": "enum ['bot', 'asli', 'ragu']",
  "annotated_by": "string",
  "annotated_at": "datetime (ISO 8601)"
}
```
- Hasil anotasi ini yang jadi dataset training untuk fine-tuning classifier (lihat `09-track-b-finetuning-pipeline.md`).

## 8. Catatan Implementasi
- Store, Product, Review, Review Analysis Result cukup jadi struktur in-memory per-request (tidak wajib database permanen) untuk Track A.
- Cache hasil `Review Analysis Result` per `store_id` disimpan di SQLite dengan TTL — menghindari re-analisis toko yang sama berulang.
- Field yang datanya tidak tersedia dari sumber → isi `null`, jangan dipaksa 0.
