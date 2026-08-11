# Architecture — Input → Process → Output

## 1. Alur Tingkat Tinggi

```
[User Input: nama produk]
        │
        ▼
[STEP 1: Live Scraping] ── Playwright: toko, produk, 20-30 review/toko
        │
        ▼
[STEP 2: Feature Extraction]
        │
        ├── Fitur numerik langsung (rating, harga, total terjual, dll)
        │
        └── Modul Review Analysis (lihat 08-review-analysis-module.md)
                 │
                 ▼
            review_authenticity_score
        │
        ▼
[STEP 3: Scoring Engine] ── rule-based, weighted, semua fitur digabung
        │
        ▼
[STEP 4: Labeling] ── mapping skor → Aman / Waspada / Berbahaya + alasan
        │
        ▼
[Output: daftar toko + label + alasan]
```

## 2. Detail Tiap Tahap

### STEP 0 — Input
- User mengetik nama produk. Validasi input dasar (bukan string kosong, filter karakter injeksi).

### STEP 1 — Live Scraping (Playwright)
- Halaman marketplace target di-render pakai headless browser (Playwright) karena konten JS-rendered.
- Ambil per toko: nama, usia toko, lokasi, rating, jumlah ulasan, total terjual, status official, response rate, harga produk yang dicari, dan **20-30 review teks per toko**.
- Terapkan rate limiting & delay antar request (menghindari anti-bot marketplace).
- **Fallback**: kalau mode `DATA_SOURCE=fixture` diaktifkan, data diambil dari `tests/fixtures/sample_stores.json` alih-alih live scraping — dipakai untuk testing/showcase, bukan operasional default.

### STEP 2 — Feature Extraction
Dua jalur paralel:
1. **Fitur numerik** — dihitung langsung dari data mentah (`price_deviation`, `rating_score`, `total_sold`, dll). Tidak melibatkan AI sama sekali.
2. **Fitur dari teks review** — diproses lewat Modul Review Analysis (embedding + heuristik, opsional LLM) menghasilkan satu fitur baru: `review_authenticity_score`.

Detail fitur numerik ada di `04-fraud-signal-features.md`. Detail modul review ada di `08-review-analysis-module.md`.

### STEP 3 — Scoring Engine
- Weighted rule-based scoring (0-100), modul terpisah (`scoring.py`).
- Semua fitur — numerik maupun `review_authenticity_score` — diperlakukan sama sebagai input ke formula scoring. Scoring engine ini **tidak tahu dan tidak peduli** apakah suatu fitur dihasilkan dari perhitungan matematis biasa atau dari model AI — ini yang membuat Track B nanti bisa "dicolok" tanpa mengubah scoring engine.

### STEP 4 — Labeling
- Threshold awal: Skor ≥ 75 → **Aman**, 40-74 → **Waspada**, < 40 → **Berbahaya** (dikalibrasi ulang setelah uji manual).
- Setiap label wajib disertai alasan konkret dari kontribusi fitur signifikan.

### Output
List toko terurut skor: `nama_toko`, `label`, `skor`, `alasan[]`, `link_toko`.

## 3. Prinsip Desain
- **Modular**: fetch, extract (numerik & review), score, label adalah modul terpisah.
- **Explainable by default**: label tanpa alasan tidak boleh lolos ke output.
- **AI sebagai sinyal, bukan keputusan**: LLM/model klasifikasi hanya menghasilkan angka fitur (`review_authenticity_score`), keputusan akhir tetap di scoring engine rule-based.
- **Fail gracefully**: toko gagal di-scrape → skip, beri label "Data tidak lengkap", jangan gagalkan seluruh request.
- **Interface stabil antar Track A/B**: `review_authenticity_score` punya kontrak (rentang 0-100) yang sama baik dihasilkan dari heuristik (Track A) maupun model fine-tuned (Track B) — penggantian sumber tidak mengubah modul lain.
