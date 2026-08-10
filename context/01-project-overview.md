# Project Overview — Online Shop Fraud Detection (MVP)

## 1. Problem Statement
Marketplace online dipenuhi ribuan toko dengan kredibilitas yang tidak transparan bagi pembeli awam. Pembeli sering kesulitan menilai apakah sebuah toko aman untuk bertransaksi hanya dari tampilan halaman produk/toko. Indikator fraud (review palsu/bot, toko baru dengan klaim tidak wajar, harga jauh di bawah pasar) tersebar dan tidak disatukan menjadi satu sinyal yang mudah dibaca user.

## 2. Goal MVP
Membangun sistem **Input → Process → Output** yang:
- Menerima query pencarian produk dari user.
- Melakukan **live scraping** data toko-toko yang menjual produk tersebut di marketplace.
- Memberi label risiko per toko: **Aman / Waspada / Berbahaya**, lengkap dengan alasan singkat (explainability).

Fokus MVP: **membuktikan alur end-to-end bisa jalan dan labelnya masuk akal**, bukan akurasi model yang sempurna sejak hari pertama.

## 3. Prinsip Inti Arsitektur
1. **Keputusan label tetap deterministik (rule-based)** — bukan diserahkan mentah-mentah ke LLM. Ini menjaga sistem auditable, cepat, dan bebas risiko hallucination pada keputusan inti.
2. **AI/LLM masuk sebagai layer sinyal tambahan atau penjelasan**, khusus untuk data tidak terstruktur (teks review) yang memang butuh pemahaman bahasa — bukan untuk data numerik yang sudah bisa dihitung langsung (rating, harga, umur toko).
3. **Tidak ada fine-tuning tanpa data berlabel.** Karena belum ada dataset review berlabel bot/asli, fine-tuning dijalankan sebagai track terpisah yang tidak menghambat rilis MVP inti.

## 4. Scope (In / Out)

**Termasuk scope MVP:**
- 1 marketplace saja dulu.
- Live scraping (Playwright) untuk data toko, produk, dan 20-30 review per toko.
- Rule-based scoring engine untuk sinyal numerik (harga, rating, umur toko, dll).
- Modul Review Analysis Lapis 1 (heuristic embedding) sebagai proxy `review_authenticity_score`.
- Output: daftar toko + label + skor + alasan.
- Fixture data (mode sekunder) untuk unit testing & showcase/demo.

**Di luar scope MVP inti (masuk Track B paralel / fase berikutnya):**
- Model fine-tuned untuk klasifikasi review authenticity (butuh anotasi manual dulu).
- Multi-marketplace agregasi.
- Notifikasi real-time / monitoring toko dari waktu ke waktu.
- Akun user, riwayat pencarian, dashboard admin.

## 5. Dua Track Pengembangan
- **Track A — Core MVP**: pipeline lengkap Step 1-4 dengan Lapis 1 (heuristic) sebagai proxy review authenticity. Ini yang jadi Definition of Done MVP, tidak menunggu Track B.
- **Track B — Review Authenticity Model**: anotasi manual (dibantu RAG) → fine-tuning classifier (IndoBERT) → dipasang menggantikan proxy Lapis 1 setelah siap, tanpa mengubah arsitektur pipeline lain.

Detail lengkap ada di `05-model-approach-mvp.md` dan `09-track-b-finetuning-pipeline.md`.

## 6. Success Metrics (MVP — Track A)
- Sistem berhasil mengembalikan label untuk minimal 90% toko hasil pencarian tanpa error.
- Setiap label disertai alasan yang bisa ditelusuri (bukan black box).
- Divalidasi manual: dari 20 toko sample, label MVP sejalan dengan penilaian manual minimal 70%.

## 7. Constraints & Assumptions
- Live scraping marketplace berisiko diblokir/berubah struktur — perlu fallback fixture untuk testing/demo.
- Belum ada dataset fraud/review berlabel — jadi dasar keputusan rule-based dulu untuk scoring inti, dan track anotasi terpisah untuk review authenticity.
- Tidak menyimpan data pribadi user (nomor HP, alamat) dari sisi penjual — cukup data publik toko.

## 8. Daftar File Dokumentasi
- `02-architecture-ipo.md` — alur Input-Process-Output detail
- `03-data-schema.md` — struktur data toko/produk/review/label
- `04-fraud-signal-features.md` — sinyal & bobot scoring
- `05-model-approach-mvp.md` — rule-based vs AI, Track A vs Track B
- `06-tech-stack-mvp.md` — stack teknis
- `07-roadmap-milestone.md` — rencana pengerjaan bertahap
- `08-review-analysis-module.md` — detail modul review authenticity (Lapis 1 & 2)
- `09-track-b-finetuning-pipeline.md` — anotasi manual, RAG-assisted labeling, fine-tuning IndoBERT
