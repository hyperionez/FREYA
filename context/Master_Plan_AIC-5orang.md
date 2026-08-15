# MASTER PLAN — AIC COMPFEST 18 (Tim 5 Orang)
## Fraud Ranker + Otak AI Fine-tuned → satu produk

> Ditulis 15 Agustus 2026. **Deadline submisi: 25 Agustus 2026, 23.55 WIB.** Sisa ~10 hari.
> **Freeze model & kode inti: 21 Agustus.** Sesudahnya hanya video + proposal (30% nilai).
> Basis: proyek "Fraud Ranker" yang sudah ada. Yang di-upgrade: `get_review_authenticity_score()` dari heuristik → IndoBERT fine-tuned.

---

## 1. Ringkasan eksekutif

Kita TIDAK membangun aplikasi baru dan TIDAK menggabung dua aplikasi. Kita mengambil produk yang sudah jalan (scraping → scoring → labeling → docker/fixture) dan **mengganti isi satu fungsi** dengan model yang di-fine-tune, lalu mengubah framing output dari vonis → bukti. Itu menutup gerbang eligibilitas (wajib kustomisasi AI) dan risiko fitnah sekaligus, tanpa merombak arsitektur.

**Tiga hal yang menentukan menang-kalah, berurutan:**
1. **Data anotasi** (tembok kritis) — label dari manusia, bukan heuristik.
2. **Model fine-tuned mengalahkan baseline heuristik** — kalau tidak, jangan dipasang.
3. **Video + proposal selesai tanpa panik** — 30% nilai, dibuat setelah freeze.

---

## 2. Kondisi terkini (audit)

**Sudah ada & jalan:**
- Pipeline `fetcher → features → scoring → labeling`, endpoint `/search`, `/health`.
- Scoring rule-based config-driven (`config.yaml`), compound rules, reasons.
- `product_matching.py` (filter relevansi + grouping varian via embedding) untuk median harga.
- Fixture mode (`DATA_SOURCE=fixture`) → demo reprodusibel tanpa scraping.
- Docker (api + frontend Streamlit), tes untuk scoring & labeling.
- 10 dokumen desain (bahan proposal).

**Belum ada (dan wajib):**
- ❌ Kustomisasi AI apa pun (fine-tune/RAG nol kode). **INI gerbang eligibilitas.**
- ❌ Framing "sinyal bukan vonis" (label masih `Berbahaya` sebagai vonis).
- ❌ Anonimisasi data latih.
- ❌ Deliverables lomba (2 video, proposal PDF, repo public final).

**Perlu diperiksa segera:** apakah git history repo berada dalam periode lomba (17 Jun–25 Agt) dan repo **public**. Kalau selama ini di repo privat, siapkan repo public dengan history yang sah.

---

## 3. BATASAN RULEBOOK (HARD — jangan dilewati)

Setiap orang wajib baca bagian ini. Melanggar = diskualifikasi atau kehilangan poin besar.

**Scope MVP (WAJIB HANYA SAMPAI):**
- Frontend: input tunggal → output AI. ❌ Tanpa dashboard analitik lanjutan, auth kompleks, halaman riwayat.
- Backend: **interaksi sinkron saja**. ❌ Tanpa background job, ❌ pipeline logging otomatis, ❌ DB terdistribusi. Live scraping yang lama = **jadikan jalur sekunder; fixture = jalur demo utama.**
- Model: **core inference, parameter statis saat demo**. ❌ Tanpa auto-tuning, ❌ feedback loop otomatis, ❌ bulk testing scripts di repo penyisihan.

**Kustomisasi AI:** WAJIB fine-tune (jalur utama). RAG/agentic/tool-calling/model pendukung juga sah (dikonfirmasi panitia) → Plan B.

**Orisinalitas & periode:** proyek hanya dikerjakan 17 Jun–25 Agt. Model, arsitektur, fitur, + preprocessing WAJIB dilakukan & dijelaskan selama periode lomba. Dataset boleh publik/sintetik.

**Repo:** GitHub **public**, commit terakhir < 25 Agt 23.55, **Conventional Commits** (`feat:`/`fix:`/`refactor:`). README dengan setup jelas + `docker compose`. Harus jalan lokal (kemungkinan **tanpa GPU** → torch CPU).

**Institusi:** ❌ Dilarang menampilkan latar belakang institusi dalam bentuk apa pun (nama kampus di repo, video, proposal, UI).

**Video Proof of Work:** unlisted, ≤7 menit, double screen (terminal + app) + timestamp, boleh fast-forward + voice over, **DILARANG cut/edit lain**. Semua fitur di video promosi wajib ada di sini. Nama: `COMPFEST 18 AIC: PROOF OF WORK - [Nama Tim] - [Nama Proyek]`.

**Video promosi:** public, ≤5 menit, MP4 ≥720p. Nama: `COMPFEST 18 AIC: [Nama Tim] - [Nama Proyek]`.

**Proposal:** PDF ≤20 halaman (di luar cover, daftar pustaka, lampiran). Wajib: latar belakang, tujuan, metodologi (alur dataset, alur pengembangan model tiap fitur, alur integrasi), kesimpulan.

**Etika (produk):** output = sinyal + bukti + disclaimer, bukan vonis. Data latih & materi publik dianonimkan.

**Pasca-submisi:** standby Discord 9–10 Sep 20.00 (panitia bisa minta live demo).

---

## 4. Peran 5 orang

| Kode | Peran | Kepemilikan utama |
|---|---|---|
| **P1** | Tech Lead / ML | Fine-tune IndoBERT, evaluasi, integrasi ke `get_review_authenticity_score()` |
| **P2** | Data & Scraping | Kumpul review mentah multi-toko, annotation tool, anonimisasi, split-by-store |
| **P3** | Backend & DevOps | Framing bukti di `labeling.py`, docker CPU-only, README, fixture-as-demo, tes |
| **P4** | Frontend & UX | Streamlit: tampilan bukti + disclaimer + highlight reasons + flag "tidak yakin" |
| **P5** | Produk, Proposal & Video | Proposal dari 10 dokumen desain, 2 video, AIC Talks, bab governance |

**Anotasi = sprint bersama.** P2 pemilik tool & kalibrasi, tapi **kelima orang melabeli** hari 2–4 (ini bottleneck kritis). Target per orang ~40–60 label/hari.

---

## 5. Timeline harian (15–25 Agustus)

### FASE 0 — Fondasi & kickoff data | Sab 15 – Min 16
- **P1:** Siapkan `ml/train.py` (kerangka IndoBERT). Tulis kriteria "bot vs asli" (rubrik anotasi) bersama P5. Siapkan Colab/GPU.
- **P2:** Tarik review mentah dari **beberapa toko & kategori** via scraping. Anonimkan (buang nama toko). Bangun annotation tool Streamlit minimal (teks + 3 tombol asli/bot/ragu + progress).
- **P3:** Audit git → pastikan repo public + history dalam periode + Conventional Commits. Verifikasi `docker compose up` jalan dari nol di mesin bersih.
- **P4:** Rancang ulang tampilan hasil: dari label vonis → kartu bukti (sinyal + alasan + disclaimer). Mockup dulu.
- **P5:** Rangka proposal (mapping 10 dokumen → struktur wajib rulebook). Konfirmasi nama tim & nama proyek (≤30 char). Cek jadwal AIC Talks.

**Milestone akhir Fase 0:** annotation tool jalan, rubrik label final, data mentah siap dilabeli, repo public bersih.

### FASE 1 — Sprint anotasi + prep pipeline | Min 16 – Sel 18
- **Semua:** kalibrasi — 2 orang label 100 review sama → cek kesepakatan (kappa) → tajamkan definisi → anotasi serius.
- **P1:** finalisasi `ml/train.py` + `ml/evaluate.py` (metrik per kelas, dibanding proxy heuristik). Uji pipeline dgn data dummy kecil.
- **P2:** kelola alur data, jaga keseimbangan asli/bot, siapkan **split by store** (bukan acak) + sisakan 1 kategori untuk uji.
- **P3:** implementasi framing bukti di `labeling.py` (ganti "Berbahaya" → tingkat sinyal + disclaimer). Jaga kontrak tetap.
- **P4:** bangun UI hasil versi bukti + flag "tidak yakin".
- **P5:** tulis bab Latar Belakang + Metodologi (alur dataset) proposal.

**Milestone akhir Fase 1 (Sel 18):** ~400–500 label terkumpul.

> **🚦 GO/NO-GO — Selasa 18 Agustus:**
> - Label ≥ ~400 & kesepakatan sehat → lanjut fine-tune.
> - Label < ~200 dengan susah payah → **aktifkan Plan B RAG** (§8). Jangan tunggu 20 Agt.

### FASE 2 — Fine-tune + integrasi | Sel 18 – Kam 20
- **P1:** fine-tune IndoBERT (GPU). Evaluasi di test set held-out per-toko. **Bandingkan vs proxy heuristik.** Iterasi 2–3 putaran. Integrasi model → `run_finetuned_classifier()`; fallback heuristik tetap ada.
- **P2:** lanjut anotasi menuju 800–1500 (data lebih banyak = model lebih baik). Kurasi test set bersih.
- **P3:** konversi/muat model untuk **CPU inference** di backend; pastikan image torch-CPU; `docker compose up` tetap jalan tanpa GPU.
- **P4:** sambungkan UI ke output baru (skor + reasons dari model + disclaimer). Poles.
- **P5:** bab Alur Pengembangan Model + Alur Integrasi. Mulai skrip/plan video.

**Milestone akhir Fase 2 (Kam 20):** model fine-tuned terpasang, **terbukti mengalahkan heuristik**, app jalan end-to-end via docker CPU. Kalau model TIDAK mengalahkan heuristik → pakai heuristik + jujurkan di proposal (jangan paksa model buruk).

### FASE 3 — Poles & kunci | Kam 20 – Jum 21
- **Semua:** uji `docker compose up` di ≥2 mesin bersih berbeda. Fixture = jalur demo utama, scraping = sekunder (tunjukkan bisa, tapi jangan andalkan saat rekaman).
- **P1/P3:** bekukan bobot & kode inti. Tabel final heuristik vs fine-tuned.
- **P4:** finalisasi UI (disclaimer jelas, no institusi).
- **P5:** README final, proposal 80%.

> **❄️ FREEZE — Jumat 21 Agustus. Setelah ini: TIDAK ada perubahan model/kode inti.**

### FASE 4 — Video + proposal | Sab 22 – Sen 24
- **P5 (pimpin) + P1:** **Video Proof of Work** (≤7 mnt, double screen, timestamp, **no cut**, fast-forward+VO boleh). Tunjukkan seluruh alur + teknologi AI. Upload YouTube **unlisted**, nama sesuai format.
- **P5 + P4:** **Video promosi** (≤5 mnt, 720p, MP4). Cerita masalah → solusi. Contoh anonim/sintetik (jangan pamer toko asli dicap). Upload **public**, nama sesuai format.
- **P1/P2/P3:** finalisasi proposal (metodologi, decision-based-on-data, akui keterbatasan), lengkapi lampiran (tabel evaluasi, kesepakatan anotator).
- **P3:** commit final rapi (Conventional Commits), repo public terkunci.

**Milestone akhir Fase 4 (Sen 24):** semua berkas siap, video ter-upload, proposal PDF final.

### FASE 5 — Buffer & submit | Sen 24 – Sel 25
- **Semua:** cek ulang tiap berkas terhadap checklist §7. Re-render bila perlu, proofread.
- **Submit PAGI 25 Agt** via situs COMPFEST — jangan 23.50.

---

## 6. Critical path & prinsip

- **Jalur kritis:** anotasi (Fase 1) → fine-tune (Fase 2). Semua sumber daya ke sini jika tertinggal.
- **Protect the 30%:** video + proposal tidak boleh dikorbankan demi mengejar akurasi. Freeze 21 Agt tidak dapat diganggu gugat.
- **Jangan overbuild:** tidak menambah fitur baru (login, riwayat, dashboard, WA integration, queue). Tiap ide "lebih keren" yang menambah permukaan = menurunkan nilai MVP.
- **Model kalah heuristik? Pakai heuristik.** Kejujuran > angka palsu. Tetap sah selama ada komponen kustomisasi (fine-tune tetap ada di repo + dijelaskan; atau RAG Plan B).

---

## 7. Deliverables checklist → rubrik

- [ ] Repo GitHub public, README + `docker compose`, Conventional Commits, torch-CPU → *Implementasi 25%, MVP 15%*
- [ ] Model fine-tuned terintegrasi + tabel before/after vs heuristik → *Implementasi 25%, Proposal 15%*
- [ ] Split by-store + uji held-out kategori → *Proposal 15%*
- [ ] Framing bukti + disclaimer + anonimisasi → *Governance 3.5%, MVP 15%*
- [ ] Flag "tidak yakin" + akui keterbatasan → *MVP 15%*
- [ ] Video Proof of Work (unlisted, no-cut, format nama) → *penilaian teknis*
- [ ] Video promosi (public, 720p, format nama) → *Video 15%*
- [ ] Proposal PDF ≤20 hal (metodologi lengkap) → *Proposal 15%*
- [ ] Tanpa jejak institusi di semua materi
- [ ] Hadir + presensi AIC Talks → *Bonus 1.5%*

---

## 8. Contingency — Plan B (RAG)

Pemicu: GO/NO-GO 18 Agt gagal (data < ~200). RAG sudah dikonfirmasi sah oleh panitia.
- Bangun basis pola fraud (Chroma) yang dikurasi manual (bukan scraping) → retrieve top-k → foundation model menilai keaslian review sebagai konteks (grounded, bukan zero-shot).
- **Catatan CPU/reprodusibilitas:** LLM inference butuh API eksternal (key + internet) atau self-host (berat). Pastikan `docker compose` tetap bisa didemokan; siapkan mode fixture untuk penjurian offline.
- Basis pola ini tetap berguna di jalur fine-tune (mempercepat & menyeragamkan anotasi), jadi membangunnya tidak sia-sia.

---

## 9. Definition of Done

Produk dianggap selesai bila: `docker compose up` di mesin bersih tanpa GPU → user masukkan input → sistem keluarkan penilaian toko dengan **bukti + disclaimer**, di mana skor keaslian review berasal dari **model fine-tuned yang terbukti > heuristik** (atau RAG Plan B), semua deliverable ter-upload sesuai format, repo public bersih, dan tidak satu pun batasan §3 dilanggar.

---

## Lampiran — Guardrail satu layar (tempel di grup)

1. Label anotasi DARI MANUSIA, bukan heuristik. (anti-sirkular)
2. Anonim di data latih & materi publik; nama boleh di output live.
3. Output = sinyal + bukti + disclaimer, BUKAN vonis.
4. Fixture = demo utama. Scraping = sekunder.
5. Sinkron saja. Tanpa queue/background job/DB terdistribusi/auth/riwayat.
6. Parameter statis saat demo. Tanpa auto-retrain/feedback loop di repo.
7. Freeze 21 Agt. Sesudahnya cuma video + proposal.
8. Conventional Commits. Repo public. torch-CPU.
9. Tanpa jejak institusi di mana pun.
10. Model kalah heuristik → pakai heuristik, jujurkan.
