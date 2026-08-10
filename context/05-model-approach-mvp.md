# Model Approach — Rule-Based Core, AI sebagai Sinyal Tambahan

## 1. Prinsip Keputusan
Sepanjang project ini, keputusan teknis dipegang konsisten: **komponen yang menentukan label akhir (Aman/Waspada/Berbahaya) harus deterministik dan explainable**. AI (embedding, LLM, model fine-tuned) hanya dipakai di tempat yang benar-benar butuh pemahaman bahasa/pola tidak terstruktur — yaitu analisis teks review — bukan untuk data numerik yang sudah bisa dihitung langsung, dan bukan untuk mengganti scoring engine itu sendiri.

Alasan:
1. **Explainability wajib** — user perlu tahu kenapa toko dilabeli begitu.
2. **Tidak ada dataset fraud berlabel** untuk scoring toko secara keseluruhan → rule-based jadi pilihan yang valid dan cepat divalidasi.
3. **Auditability** — rule-based bisa ditelusuri persis; model/LLM menambah risiko hallucination pada keputusan yang berdampak langsung ke user.

## 2. Dua Track Paralel

```
Track A (Core MVP — blocking)          Track B (Review Model — tidak blocking)
─────────────────────────────          ────────────────────────────────────────
Rule-based scoring engine              Anotasi manual review (dibantu RAG)
        +                                        │
Modul Review Analysis Lapis 1                    ▼
(heuristic embedding, proxy score)     Fine-tuning classifier (IndoBERT)
        │                                        │
        ▼                                        ▼
   [MVP SHIP]  ──────── nanti diganti ────── [Model siap]
```

- **Track A** wajib selesai untuk MVP dianggap "viable" — tidak menunggu Track B.
- **Track B** berjalan paralel, hasilnya "dicolok" menggantikan proxy Lapis 1 begitu model fine-tuned siap dan tervalidasi, tanpa mengubah arsitektur pipeline lain (kontrak `review_authenticity_score` 0-100 tetap sama).

## 3. Kenapa Bukan Fine-Tuning LLM Besar
LLM besar (Gemini/GPT) didesain general-purpose; fine-tuning sendiri oleh user untuk task klasifikasi sempit seperti "review ini bot atau bukan" itu berat & tidak proporsional. Untuk task ini, classifier kecil yang sudah terlatih Bahasa Indonesia (**IndoBERT**) jauh lebih pas: lebih murah dilatih, lebih cepat inference (bisa jalan di CPU), lebih gampang dievaluasi terhadap dataset kecil.

## 4. Kenapa Fine-Tuning Butuh Anotasi Manual Dulu (Bukan Bootstrap)
Sudah diputuskan: anotasi manual dipilih di atas bootstrap dari heuristik, karena label dari heuristik (near-duplicate/timestamp) itu noisy — kalau dipakai langsung untuk training, model bisa belajar dari asumsi yang belum tervalidasi manusia. Anotasi manual lebih lambat tapi hasilnya lebih reliable sebagai ground truth pertama project ini.

## 5. Rule-Based Tetap Ada Sebagai Sanity Check
Bahkan setelah Track B menghasilkan model fine-tuned, rule-based signal lain (harga, umur toko) tetap jadi baseline pembanding. Kalau model bilang "review authentic" tapi sinyal lain ekstrem (misal harga 90% di bawah pasar + toko baru 3 hari), kombinasi itu tetap di-flag sebagai anomali di scoring engine (lihat "Compound Red Flags" di `04-fraud-signal-features.md`) — model tidak dipercaya buta.

## 6. Roadmap Setelah Track B Siap
```
[V0 - MVP: Track A, proxy heuristic]
        │
        ▼
[V1: Track B selesai, model fine-tuned dipasang menggantikan proxy]
        │
        ▼
[V2: Feedback loop dari user (report toko), dataset terus bertambah,
     model di-retrain berkala]
```
