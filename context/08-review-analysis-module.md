# Modul Review Analysis — Detail Lapis 1 & Lapis 2

Modul ini satu-satunya bagian pipeline yang benar-benar butuh AI, karena inputnya teks tidak terstruktur (review). Outputnya SATU fitur: `review_authenticity_score` (0-100), yang masuk ke scoring engine rule-based seperti fitur lain.

## 1. Alur Lengkap

```
[20-30 review/toko dari live scraping]
        │
        ▼
[Embedding: sentence-transformers, multilingual, lokal]
        │
        ▼
[Lapis 1: Heuristic Pre-filter] ── selalu jalan, gratis, cepat
   - Near-duplicate detection (cosine similarity antar embedding review)
   - Clustering waktu posting (banyak review masuk waktu berdekatan)
        │
        ▼
   Hasil sudah jelas (sangat mencurigakan / sangat bersih)?
        │
        ├── YA → langsung hasilkan review_authenticity_score, SELESAI (source: heuristic_l1)
        │
        └── TIDAK (ambigu) →
                    ▼
        [Lapis 2: LLM Analysis — 1 API call per toko]
           - Kirim 20-30 review + hasil Lapis 1 sebagai konteks
           - RAG: retrieve top-k pola fraud relevan dari knowledge base (Chroma)
             untuk grounding penilaian LLM
           - Prompt terstruktur, output JSON: {score, reasoning}
                    ▼
           review_authenticity_score (source: llm_l2)
```

> Catatan status MVP: Track A hanya mengimplementasikan Lapis 1 sebagai proxy. Lapis 2 (LLM) bersifat opsional/tahap lanjutan sebelum Track B (model fine-tuned) menggantikan proxy ini sepenuhnya — lihat `05-model-approach-mvp.md` untuk urutan prioritas.

## 2. Lapis 1 — Heuristic Pre-filter (Detail)

**Near-duplicate detection:**
```python
def detect_near_duplicates(review_embeddings, threshold=0.9):
    duplicate_pairs = []
    for i in range(len(review_embeddings)):
        for j in range(i + 1, len(review_embeddings)):
            sim = cosine_similarity(review_embeddings[i], review_embeddings[j])
            if sim > threshold:
                duplicate_pairs.append((i, j, sim))
    return duplicate_pairs
```

**Clustering waktu posting:**
```python
def detect_time_clustering(timestamps, window_minutes=10, min_count=5):
    # kalau >= min_count review masuk dalam window_minutes yang sama -> flag
    ...
```

**Kombinasi jadi skor:**
```python
def compute_heuristic_score(duplicate_ratio, time_cluster_flag):
    score = 100
    score -= duplicate_ratio * 60          # makin banyak duplikat, makin turun
    if time_cluster_flag:
        score -= 20
    return max(0, min(100, score))
```

**Kapan dianggap "jelas" (tidak perlu Lapis 2):**
- `duplicate_ratio` sangat tinggi (>50%) ATAU sangat rendah (<5%) DAN tidak ada time clustering mencurigakan → hasil dianggap cukup pasti, langsung dipakai.
- Selain itu (nilai di rentang tengah / sinyal bertentangan) → lanjut ke Lapis 2.

## 3. Lapis 2 — LLM Analysis (Detail)

**Kenapa dipanggil selektif, bukan selalu:** menghemat cost & latency — LLM API hanya untuk kasus yang heuristik saja tidak cukup meyakinkan.

**Struktur prompt (garis besar, bukan implementasi final):**
- System instruction: definisikan task secara sempit (nilai keaslian sekumpulan review, bukan tugas terbuka).
- Context dari RAG: top-k pola fraud relevan yang ter-retrieve dari knowledge base.
- Data: 20-30 review + ringkasan hasil Lapis 1 (duplicate_ratio, time_cluster_flag).
- Instruksi output: **wajib JSON terstruktur** (`{"score": int, "reasoning": [string]}`), bukan teks bebas — supaya hasilnya predictable dan bisa langsung dipakai sistem.

**Kontrak output:**
```json
{
  "score": 42,
  "reasoning": [
    "Beberapa review menggunakan frasa generik yang identik meski produk berbeda",
    "Tidak ditemukan detail spesifik terhadap varian/warna produk di sebagian besar review"
  ]
}
```

## 4. RAG Knowledge Base — Isi & Sumber
- Berisi puluhan entri pola review palsu yang dikenal (ditulis/dikurasi manual, bukan hasil scraping) — contoh kategori: frasa generik berulang, review tanpa detail produk spesifik, pola waktu posting tidak wajar, rating ekstrem tanpa elaborasi.
- Disimpan di Chroma, di-retrieve pakai embedding yang sama dengan yang dipakai untuk dedup (`sentence-transformers`).
- Knowledge base ini **sama** yang dipakai untuk membantu anotator manual di Track B (lihat `09-track-b-finetuning-pipeline.md`) — satu sumber kebenaran, dipakai dua konteks (inference live & assist anotasi).

## 5. Interface ke Scoring Engine
```python
def get_review_authenticity_score(store_id, reviews) -> ReviewAnalysisResult:
    # internal: pilih Lapis 1 saja, atau Lapis 1 + Lapis 2, atau nanti model fine-tuned (Track B)
    # kontrak return SELALU: {score: int (0-100), source: str, reasons: list[str]}
    ...
```
Kontrak ini yang membuat Track B bisa menggantikan implementasi internal tanpa mengubah pemanggil di `features.py`.
