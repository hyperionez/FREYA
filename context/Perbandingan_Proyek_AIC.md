# Perbandingan Dua Pendekatan — AIC COMPFEST 18

> Dokumen asesmen untuk dianalisis AI. Ditulis 14 Agustus 2026. Deadline submisi: **25 Agustus 2026, 23.55 WIB** (11 hari).
> Membandingkan dua proyek di domain yang sama (kepercayaan/fraud toko online):
> **Proyek A** = "Fraud Ranker" (sudah dibangun) · **Proyek B** = "Trust Analyzer" (baru rencana).

---

## 0. Cara pakai dokumen ini (untuk AI yang membacanya)

Tujuanmu bukan memenangkan argumen untuk salah satu sisi. Tujuanmu:
1. Menilai proyek yang sedang kamu bantu (kemungkinan Proyek A) secara jujur terhadap aturan lomba.
2. Mengidentifikasi risiko yang bisa menjatuhkan di penjurian, terutama gerbang eligibilitas.
3. Mengusulkan perbaikan konkret yang muat dalam 11 hari.

Aturan main penilaian ada di §1. Baca itu dulu sebelum menilai apa pun.

---

## 1. Konteks lomba & aturan kunci

**Tema:** AI for the Backbone of the Economy (Smart Manufacturing / Logistics / Commerce). Kedua proyek masuk **Smart Commerce**.

**Aturan paling menentukan (Ketentuan Khusus & Deliverables rulebook):**
> "Diperbolehkan menggunakan model API dan pre-trained model. Model **WAJIB di fine-tune** sesuai dengan inovasi fitur per tim."

**Klarifikasi panitia (perlu diverifikasi keasliannya dari kanal resmi — email/website/Discord):**
Syarat inti adalah **adanya kustomisasi**, bukan zero-shot API call biasa. Selain fine-tuning murni (LoRA/QLoRA), boleh dipenuhi lewat:
- Retrieval-Augmented Generation (RAG)
- Agentic Workflow / AI Agents
- Tool Calling / Function Calling
- Training model pendukung yang terintegrasi dengan Foundation Model

> **Implikasi:** Pintu lebih lebar, TAPI palang tetap ada. Off-the-shelf model dipakai zero-shot + aturan buatan tangan **TIDAK** memenuhi — bukan fine-tune, bukan RAG, bukan agent, bukan model terlatih.

**Batasan MVP (rulebook, "WAJIB HANYA SAMPAI"):**
- Frontend: input tunggal → tampilkan output AI. Tanpa dashboard analitik, auth kompleks, riwayat.
- Backend: **interaksi sinkron** saja. Tanpa background jobs, tanpa pipeline logging otomatis, tanpa DB terdistribusi. Harus jalan via `docker compose` sesuai README.
- Model AI: **core inference, parameter statis saat demo**. Tanpa auto-tuning, bulk testing scripts, atau feedback loop otomatis di repo penyisihan.

**Kriteria penilaian (total 105%):**
Orisinalitas & Dampak 20% · Implementasi & Arsitektur 25% · Kesiapan MVP 15% · Video Promosi 15% · Kualitas Proposal 15% · Relevansi Tema 10% · Bonus Governance 3.5% · Bonus AIC Talks 1.5%.

**Reprodusibilitas:** panitia harus bisa menjalankan kode lokal (kemungkinan tanpa GPU). Panitia berhak minta live demo / klarifikasi.

---

## 2. Ringkasan dua proyek

### Proyek A — "Fraud Ranker" (sudah dibangun)
- **Alur:** user input query produk → **live scraping** marketplace (Playwright/Tokopedia) → ekstraksi fitur toko → **scoring rule-based** → label **Aman / Waspada / Berbahaya** per toko + alasan.
- **AI di dalamnya:** hanya di modul review — embedding pakai-jadi (`sentence-transformers`) untuk deteksi near-duplicate (cosine) + clustering waktu posting → satu fitur `review_authenticity_score`.
- **Arsitektur:** modular, scoring digerakkan `config.yaml`, kontrak antar-modul rapi, ada fixture mode untuk demo reprodusibel, ada unit test, dokumentasi desain lengkap (10 file).

### Proyek B — "Trust Analyzer" (rencana)
- **Alur:** user tempel teks (review / deskripsi / chat penjual) → **IndoBERT fine-tuned** klasifikasi per-kalimat → sorot kalimat red-flag + alasan + flag "tidak yakin".
- **AI di dalamnya:** fine-tuning sebagai inti, wajib dan sentral.
- **Posisi produk:** output = **sinyal untuk diperiksa, BUKAN vonis**. Manusia yang memutuskan.
- **Status:** belum ada kode; mulai dari nol pada 14 Agustus.

---

## 3. TEMUAN KRITIS Proyek A — kustomisasi AI ada di bagian yang ditunda

Berdasarkan inspeksi kode (bukan dokumen):

| Komponen | Status di kode aktual |
|---|---|
| Rule-based scoring | ✅ Dibangun, jalan |
| Heuristic embedding (cosine dedup + time clustering) | ✅ Dibangun, jalan (embedding **off-the-shelf**, tanpa training) |
| Fine-tuning IndoBERT (disebut "Track B") | ❌ Dokumen saja, **nol kode** |
| RAG (Chroma) | ❌ Ada di `requirements`, **tidak pernah diimpor/dipakai** |
| LLM layer (Gemini) | ❌ Dokumen saja, **nol kode** |

**Konsekuensi:** produk yang benar-benar siap submit = aturan buatan tangan + embedding pakai-jadi. **Tidak ada satu pun kustomisasi AI.** Terhadap aturan asli "wajib fine-tune", ini **belum memenuhi**. Fine-tuning dan RAG-nya secara eksplisit ditandai "tidak menghambat MVP inti" (non-blocking) — padahal di lomba ini, itu justru **gerbang eligibilitas**. Prioritasnya terbalik.

**Ironi arsitektur:** filosofi tim ("keputusan label deterministik rule-based, bukan LLM") adalah rekayasa yang benar (auditable, bebas halusinasi) — tapi di kompetisi AI yang mewajibkan kustomisasi model jadi pusat, meminimalkan AI justru melemahkan Implementasi Teknologi (25%).

### Jalan keluar untuk Proyek A (pilih satu, sebelum 25 Agt)
1. **Selesaikan fine-tuning** (anotasi review → fine-tune IndoBERT → validasi → pasang menggantikan proxy heuristik). Penuhi aturan asli, paling kuat. Berat dalam 11 hari, mungkin kalau diprioritaskan sekarang.
2. **Aktifkan RAG + LLM sebagai bagian inti pipeline** (bukan "opsional"). Lebih ringan; penuhi klarifikasi (jika klarifikasi terverifikasi asli).

**Yang tidak boleh:** submit versi rule-based + embedding pakai-jadi apa adanya, berharap dihitung sebagai kustomisasi. Tidak akan.

---

## 4. Perbandingan per kriteria

| Kriteria | Bobot | Proyek A (Fraud Ranker) | Proyek B (Trust Analyzer) |
|---|---|---|---|
| Orisinalitas & Dampak | 20% | Ambisius (scan toko live); tapi "fraud detection marketplace" ide relatif umum | Framing "sinyal bukan vonis" lebih segar & defensible; dampak sedikit lebih sempit |
| **Implementasi & Arsitektur** | 25% | **Arsitektur lebih matang** (config-driven, kontrak, tes) — TAPI inti rule-based, kustomisasi AI belum ada = risiko eligibilitas | Fine-tune di pusat (patuh aturan), tapi **arsitektur belum terbukti** |
| Kesiapan MVP | 15% | **MVP ADA & jalan** (fixture) — tapi rawan *overbuilt* (crawl banyak toko vs aturan input-tunggal sinkron) | Scope pas sempurna — **tapi belum berwujud** |
| Video Promosi | 15% | Ceiling tinggi jika scraping jalan live; canggung jika melabeli toko asli "Berbahaya" | "Kalimat merah + baseline meleset" aman, varians rendah |
| **Kualitas Proposal** | 15% | **10 dokumen desain jujur sudah ada** — bahan proposal kuat. Lemah di "bobot ditebak manual" | Cerita before/after + cross-source kuat **jika dieksekusi** — belum ada jejak |
| Relevansi Tema | 10% | Smart Commerce, pas. Rule-based core bisa dituduh "AI tempelan" | Smart Commerce, AI jelas jadi inti |
| Governance (bonus) | 3.5% | Belum menyinggung risiko menuduh toko asli | "Sinyal bukan vonis" + buang nama sudah baked-in |

### Dua pertanyaan berbeda
- **(A) Mana yang lebih pas aturan + etika + scope?** → Proyek B lebih bersih.
- **(B) Mana yang realistis skornya lebih tinggi 25 Agustus?** → **Kemungkinan Proyek A — ASALKAN gerbang fine-tune/RAG dibereskan.** Alasannya: arsitektur lebih matang, dokumentasi reflektif sudah ada, MVP sudah jalan. Keunggulan Proyek B baru terwujud jika dieksekusi hampir sempurna dalam 11 hari DAN tembok data teratasi.

---

## 5. Risiko sekunder Proyek A

1. **Live scraping rapuh — bermasalah ganda.** Selector tidak stabil (diakui di catatan tim sendiri). (a) Panitia harus bisa `docker compose up` dan melihat jalan; browser headless yang menavigasi search→PDP→toko dengan delay makan menit & gampang patah. (b) Video Proof of Work dilarang di-cut — jika scraping patah saat rekaman, tak bisa ditambal. Mitigasi fixture bagus untuk tes, tapi berarti yang dilihat panitia data buatan.
2. **Menuduh toko nyata bernama asli "Berbahaya" = risiko fitnah/etika.** Memberi cap berbahaya pada usaha nyata berdasarkan heuristik tebakan. Rawan hukum & etika; belum dijawab dokumen. Ini juga membuka pertanyaan juri yang sulit.
3. **Bobot scoring ditebak manual.** Validasi "70% sejalan penilaian manual atas 20 toko" lemah. Rubrik Proposal (15%) mencari keputusan berbasis data → titik lemah.
4. **Scope borderline overbuilt.** Crawl banyak toko dengan delay per langkah menegangkan batas "interaksi sinkron" MVP.

---

## 6. Kekuatan & kelemahan (ringkas, dua sisi)

**Proyek A kuat:** arsitektur matang, dokumentasi jujur (tambang emas proposal), MVP sudah jalan, fixture mode, tes.
**Proyek A lemah:** kustomisasi AI belum ada (gerbang eligibilitas), scraping rapuh, risiko fitnah toko asli, bobot ditebak.

**Proyek B kuat:** fine-tune sentral (patuh), etika "sinyal bukan vonis", scope pas, demo dramatis, data tidak sirkular jika sumbernya nyata.
**Proyek B lemah:** belum dibangun sama sekali di 14 Agt; kualitas bergantung pengumpulan data nyata yang belum terbukti; mengejar tim yang start lebih dulu.

---

## 7. Tiga jalur keputusan

### Jalur 1 — GABUNG (nilai tertinggi jika memungkinkan)
Rulebook izinkan tim 3–5 orang, boleh beda institusi. Domain kedua proyek nyaris identik → bersaing sesama = merugikan berdua jika satu meja juri.
Gabungan = arsitektur matang + dokumentasi jujur (dari A) + fine-tune sentral + etika sinyal-bukan-vonis + eval cross-source (dari B). **Kelemahan terbesar A (kustomisasi AI belum ada) = kekuatan terbesar B. Kelemahan terbesar B (belum dibangun) = tertutup kerja berminggu-minggu A.**

### Jalur 2 — BERSAING & DIFERENSIASI (jika tak bisa gabung)
Proyek B jangan bertarung di tanah A (scanner marketplace live — wilayah A, dan rapuh). Menang di tanah yang A tak bisa ikuti cepat: fine-tune yang benar-benar jalan, "sinyal bukan vonis", tabel cross-source (model belajar penipuan, bukan platform). Jadilah versi yang patuh aturan & etis — di situ A sedang lemah.

### Jalur 3 — PERBAIKI DI TEMPAT (jika A jalan sendiri)
Fokus tunggal: **balik prioritas** — jadikan fine-tune ATAU RAG sebagai blocking, bukan "nanti". Plus: tambahkan disclaimer "sinyal bukan vonis" + buang nama toko dari label, untuk menutup risiko fitnah & mengisi Governance.

---

## 8. Rekomendasi konkret + action items (11 hari)

**Prioritas #1 untuk Proyek A (eligibilitas):** dalam 3 hari ke depan, putuskan jalur fine-tune vs RAG dan MULAI membangunnya sebagai blocking. Jangan sampai 25 Agt tiba dengan hanya rule-based + embedding pakai-jadi.

**Timeline saran (jika A memilih fine-tune review-authenticity):**
- 14–16 Agt: anotasi sample review (bot/asli) — target beberapa ratus, multi-sumber, buang nama toko.
- 17–19 Agt: fine-tune IndoBERT, evaluasi vs proxy heuristik (precision/recall, held-out).
- 20 Agt: pasang model menggantikan proxy; uji `docker compose` di mesin bersih (CPU-only).
- **21 Agt: FREEZE.** 22–24: Video Proof of Work (no cut) + Video promosi + proposal. 25: submit pagi.

**Perbaikan cepat lintas-jalur (murah, dampak tinggi):**
- Ubah output label dari vonis → **sinyal untuk diperiksa** + disclaimer. Tutup risiko fitnah, isi Governance.
- **Buang nama toko/penjual** dari data latih & tampilan label.
- Simpan **live scraping sebagai jalur sekunder**; pastikan fixture bisa mendemonstrasikan seluruh alur andai scraping patah saat penjurian.
- Di proposal, jujurkan keterbatasan (bobot ditebak, scraping rapuh) → rubrik menghargai refleksi.

---

## 9. Yang bisa saling dipinjam

**B pinjam dari A:** pola `config.yaml` untuk scoring, fixture mode untuk demo reprodusibel, kontrak antar-modul, disiplin mendokumentasikan keputusan & gap.
**A pinjam dari B:** fine-tune sentral (menutup gerbang aturan), framing "sinyal bukan vonis" (menutup risiko fitnah + isi Governance), eval cross-source (bukti model belajar penipuan bukan platform).

---

*Catatan verifikasi: klarifikasi panitia di §1 harus dipastikan asli dari kanal resmi sebelum arsitektur diubah bergantung padanya. Jika tidak terverifikasi, hanya jalur fine-tuning murni yang aman memenuhi aturan.*
