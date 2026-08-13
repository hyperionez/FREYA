# Roadmap & Milestone — MVP

Track A (Core MVP) dan Track B (Review Authenticity Model) berjalan **paralel**, bukan berurutan. Track A yang menentukan Definition of Done MVP.

## Track A — Core MVP

### Fase 0 — Persiapan (1-2 hari)
- [ ] Tentukan 1 marketplace target, cek struktur halaman untuk scraping (Playwright).
- [x] Siapkan environment: Python, FastAPI, Playwright.
- [ ] Kumpulkan 15-20 contoh toko (campuran kredibel & mencurigakan) untuk kalibrasi manual nanti.

### Fase 1 — Live Scraping (2-3 hari)
- [ ] Implementasi `fetcher.py`: Playwright scraping toko, produk, dan 20-30 review/toko. **Partial (2026-08-11):** store discovery (search → produk → toko) dan sebagian field toko (`rating`, `review_count`*, `total_sold`) sudah jalan; `location`, `is_official_store`, `response_rate`, `response_time_minutes`, produk, dan review masih kosong — selector belum ketemu/dikonfirmasi (lihat `context/10-tokopedia-scraping-notes.md`). *`review_count` masih pakai angka rating (552) sebagai placeholder, bukan angka ulasan (278) — perlu diperbaiki.
- [x] Implementasi mode fixture (`DATA_SOURCE=fixture`) sebagai fallback testing. Diverifikasi jalan end-to-end (venv lokal + Docker) lewat `/search`.
- [x] Tangani rate limiting, delay antar request, dan kegagalan scraping (fail gracefully). Delay + skip-on-error diimplementasi di `fetcher.py`, berlaku juga untuk bagian live scraping yang belum lengkap di atas.

### Fase 2 — Feature Extraction & Review Analysis Lapis 1 (3-4 hari)
- [x] Implementasi `features.py` untuk fitur numerik. `price_deviation` dihitung terhadap median harga lintas toko untuk query yang sama; `rating`, `review_count`, `is_official_store`, `response_rate`, `total_sold` pass-through dari data mentah. Diverifikasi lewat `/search` dengan fixture data.
- [x] Implementasi `review_analysis/embedding.py`: embed review (`sentence-transformers`, `paraphrase-multilingual-MiniLM-L12-v2`) + near-duplicate detection (cosine similarity > 0.9) + time-clustering (≥5 review dalam 10 menit). Kontrak `{score, source, reasons}` (source selalu `heuristic_l1` untuk saat ini). Diverifikasi: toko `GadgetMurahKilat` di fixture (review nyaris identik dalam rentang 10 menit) otomatis terdeteksi dan turun ke skor 20.
- [ ] **[Mulai Track B secara paralel]**: mulai kumpulkan sample review dari hasil scraping untuk keperluan anotasi.
- Catatan: Lapis 2 (LLM/Gemini + RAG untuk kasus ambigu) belum diimplementasikan — di luar scope Fase 2, hasil ambigu tetap pakai skor Lapis 1 untuk saat ini.

### Fase 3 — Scoring & Labeling (2-3 hari)
- [x] Implementasi `scoring.py` sesuai bobot di `04-fraud-signal-features.md`. Bobot/threshold dipindah ke `config.yaml` (recalibratable tanpa ubah kode). Mencakup 6 sinyal individual + 2 compound rule (§4) yang override kontribusi individual saat trigger. Diverifikasi lewat `/search` dengan fixture data — compound rule "rating sempurna tapi review bot" berhasil menjatuhkan skor `GadgetMurahKilat` ke 0.
- [x] Implementasi `labeling.py`: mapping skor -> label + reasons. Threshold Aman ≥75 / Waspada 40-74 / Berbahaya <40 (§5). Reasons diambil dari kontribusi scoring dengan |kontribusi| ≥ 10, diurutkan dari paling signifikan; fallback reason kalau tidak ada yang signifikan supaya label tidak pernah tanpa alasan. `/search` sekarang menjalankan STEP 1-4 penuh dan sort hasil per skor tertinggi. Diverifikasi lewat fixture: 2 toko Aman (85), 1 Waspada (68), 2 Berbahaya (7, 0).
- [ ] Unit test untuk tiap rule scoring.

### Fase 4 — Interface & Integrasi (2-3 hari)
- [ ] Endpoint FastAPI (`/search?query=...`) menjalankan pipeline lengkap.
- [ ] UI Streamlit untuk input query & tampilkan hasil.

### Fase 5 — Validasi & Kalibrasi (2-3 hari)
- [ ] Jalankan sistem terhadap 20 toko sample dari Fase 0.
- [ ] Bandingkan label sistem vs penilaian manual, target minimal 70% sejalan.
- [ ] Kalibrasi ulang bobot/threshold.

### Fase 6 — Demo & Dokumentasi (1 hari)
- [ ] Siapkan demo end-to-end (live scraping + fallback fixture).
- [ ] Catat known limitations.
- [ ] Susun status Track B untuk laporan.

## Track B — Review Authenticity Model (Paralel, Mulai dari Fase 2)

### Fase B1 — Persiapan Knowledge Base RAG
- [ ] Kumpulkan/tulis dokumentasi pola review palsu yang dikenal (puluhan entri).
- [ ] Setup Chroma, index knowledge base pakai `sentence-transformers`.

### Fase B2 — Anotasi Manual
- [ ] Bangun `annotation_app.py` (Streamlit): tampilkan review + top-k pola RAG relevan, tombol Bot/Asli/Ragu.
- [ ] Anotasi sample review dari hasil scraping Track A (target jumlah disesuaikan kapasitas waktu).

### Fase B3 — Fine-Tuning
- [ ] Siapkan dataset dari hasil anotasi (`data/annotations.jsonl`).
- [ ] Fine-tune IndoBERT di Google Colab.
- [ ] Evaluasi model (precision/recall terhadap validation set).

### Fase B4 — Integrasi
- [ ] Ganti proxy Lapis 1 dengan model fine-tuned di `review_analysis/` (via kontrak `review_authenticity_score` yang sudah konsisten).
- [ ] Bandingkan hasil label sebelum/sesudah model diganti — pastikan tidak ada regresi signifikan.

## Definition of Done

**MVP (Track A) selesai kalau:**
1. User bisa input nama produk dan mendapat daftar toko berlabel via live scraping dalam waktu wajar.
2. Setiap label disertai alasan yang masuk akal.
3. Divalidasi manual terhadap sample toko, mencapai target kesepakatan minimal 70%.
4. Kode modular, siap "menerima" model Track B tanpa refactor besar.

**Track B dianggap siap dipasang kalau:**
1. Dataset anotasi mencapai jumlah yang disepakati cukup representatif.
2. Model fine-tuned menunjukkan performa lebih baik dari proxy heuristik Lapis 1 pada validation set.
3. Integrasi ke pipeline tidak menyebabkan regresi pada hasil labeling toko yang sudah divalidasi di Fase 5.
