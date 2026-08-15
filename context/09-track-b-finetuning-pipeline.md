# Track B — Annotation & Fine-Tuning Pipeline

Track ini berjalan **paralel** dengan Track A (Core MVP), tidak menghambat rilis MVP inti. Tujuannya: menghasilkan model classifier kecil (IndoBERT fine-tuned) yang menggantikan proxy heuristik Lapis 1 di Modul Review Analysis, setelah tervalidasi lebih baik.

## 1. Kenapa Anotasi Manual (Bukan Bootstrap Otomatis)
Label dari heuristik (near-duplicate/time clustering) bersifat noisy — kalau langsung dipakai untuk training, model berisiko belajar dari asumsi yang belum tervalidasi manusia. Anotasi manual lebih lambat tapi jadi ground truth pertama yang reliable untuk project ini.

## 2. Alur Lengkap

```
[Sample review dari live scraping Track A]
        │
        ▼
[Annotation Tool — Streamlit]
   Untuk tiap review, tampilkan:
   - Teks review
   - Top-k pola fraud relevan dari RAG (Chroma, knowledge base sama seperti Lapis 2)
   - Tombol pilihan: Bot / Asli / Ragu
        │
        ▼
[Dataset: data/annotations.jsonl]
   {review_id, text, retrieved_patterns, label, annotated_by, annotated_at}
        │
        ▼
[Fine-tuning: IndoBERT + HuggingFace transformers, jalan di Google Colab]
        │
        ▼
[Evaluasi: precision/recall terhadap validation set terpisah]
        │
        ▼
   Performa lebih baik dari proxy Lapis 1?
        │
        ├── YA → pasang menggantikan proxy di review_analysis/ (source: finetuned_model)
        └── TIDAK → kumpulkan lebih banyak anotasi, iterasi ulang
```

## 3. Kenapa RAG Membantu di Tahap Anotasi
Menampilkan pola fraud yang relevan (retrieved dari knowledge base yang sama dipakai Lapis 2) ke annotator punya dua manfaat:
- **Konsistensi**: annotator yang berbeda cenderung menilai lebih seragam kalau ada acuan pola yang sama.
- **Kecepatan**: annotator tidak perlu menghafal semua pola fraud, tinggal bandingkan dengan yang ditampilkan sistem.

RAG di sini **membantu manusia mengambil keputusan**, bukan menggantikan keputusan manusia — beda peran dengan RAG di Lapis 2 (yang membantu LLM).

## 4. Fine-Tuning — Detail Teknis

**Kenapa IndoBERT, bukan LLM besar:**
- Task-nya sempit (klasifikasi biner/tiga kelas: bot/asli/ragu), tidak butuh model general-purpose besar.
- IndoBERT sudah pre-trained di korpus Bahasa Indonesia — fine-tuning butuh data jauh lebih sedikit dibanding training dari nol.
- Inference ringan (CPU cukup), cocok untuk MVP yang tidak punya infra GPU permanen.

**Setup training (garis besar):**
```python
from transformers import AutoTokenizer, AutoModelForSequenceClassification, Trainer, TrainingArguments

model_name = "indobenchmark/indobert-base-p1"
tokenizer = AutoTokenizer.from_pretrained(model_name)
model = AutoModelForSequenceClassification.from_pretrained(model_name, num_labels=2)  # bot / asli

# dataset dari data/annotations.jsonl (label "ragu" di-exclude atau ditangani terpisah)
# training_args, Trainer.fit(), evaluasi dengan held-out validation set
```

**Evaluasi wajib sebelum dipasang ke pipeline:**
- Precision & recall terhadap validation set yang TIDAK dipakai untuk training.
- Bandingkan langsung dengan skor proxy Lapis 1 pada sample toko yang sama dari Fase 5 (Track A) — model baru harus terbukti lebih baik, bukan asumsi otomatis lebih baik karena "pakai AI".

## 5. Integrasi ke Pipeline (Setelah Model Siap)
Karena kontrak `review_authenticity_score` sudah didesain konsisten sejak awal (lihat `08-review-analysis-module.md` bagian 5), integrasi hanya mengganti isi fungsi `get_review_authenticity_score()`:

```python
def get_review_authenticity_score(store_id, reviews) -> ReviewAnalysisResult:
    if finetuned_model_available():
        return run_finetuned_classifier(reviews)   # source: finetuned_model
    return run_heuristic_l1(reviews)                # source: heuristic_l1 (fallback)
```

Tidak ada perubahan di `features.py`, `scoring.py`, atau `labeling.py` — sesuai prinsip modular yang dipegang sejak arsitektur awal.

## 6. Retraining Berkala (Setelah V1)
Setelah model terpasang dan sistem mulai punya fitur feedback dari user (roadmap V2 di `05-model-approach-mvp.md`), dataset anotasi bisa terus bertambah dari feedback tersebut, dan model di-retrain berkala untuk meningkatkan akurasi seiring waktu.

**Di luar scope submisi kompetisi (2026-08-15):** `context/Master_Plan_AIC-5orang.md` §3 mewajibkan parameter model **statis saat demo** — tanpa auto-retrain atau feedback loop otomatis di repo penyisihan, dan model **dibekukan** per 21 Agustus. Bagian ini murni ide pasca-kompetisi (V2+); tidak diimplementasikan untuk submisi.
