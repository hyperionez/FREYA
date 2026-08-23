# Fraud Detector MVP — Deteksi Toko Berisiko di Marketplace

Menilai kredibilitas toko dari sinyal harga, rating, dan **keaslian review**, lalu
menjelaskan *kenapa* sebuah toko dinilai berisiko — bukan sekadar memberi angka.

Contoh keluaran nyata:

```
review_authenticity_score: 20  (heuristic_l1)
  "5 dari 5 review terdeteksi near-duplicate (similarity > 0.9)"
  "Terdeteksi 5+ review masuk dalam rentang 10 menit yang sama"
scoring: 10        label: "Berbahaya"
```

---

## Prasyarat

- **Docker Desktop** (cara yang disarankan), atau
- **Python 3.11+** kalau menjalankan tanpa Docker

---

## Menjalankan dengan Docker

### 1. Siapkan `.env` — WAJIB, jangan dilewati

`.env` tidak ikut di-commit (berisi kunci API). `docker-compose.yml` memuatnya
lewat `env_file`, jadi **tanpa berkas ini `docker compose` langsung gagal** dengan
pesan `env file ... not found`.

```powershell
copy .env.example .env
```

```bash
cp .env.example .env          # macOS / Linux
```

Isi bawaannya sudah cukup untuk menjalankan demo. `GEMINI_API_KEY` hanya
diperlukan kalau kamu membangkitkan ulang data sintetik lewat
`ml/build_dataset.py synth`; untuk menjalankan produk, biarkan apa adanya.

### 2. Nyalakan

```bash
docker compose up --build -d
```

### 3. Pastikan berhasil

```bash
docker compose ps                      # dua layanan harus "Up"
curl http://localhost:8000/health      # -> {"status":"ok"}
```

| Layanan | Alamat |
|---|---|
| Antarmuka (Streamlit) | http://localhost:8501 |
| API (FastAPI) | http://localhost:8000 |

### 4. Menghentikan

```bash
docker compose down
```

Jangan pakai `docker compose down -v` kecuali memang ingin mengulang dari nol:
flag `-v` menghapus volume `hf_cache`, sehingga model embedding harus diunduh
ulang dan pencarian pertama kembali memakan ~60 detik.

---

## Tiga hal yang perlu diketahui saat mencoba

**Pencarian pertama memakan ~60 detik.** Model embedding
(`paraphrase-multilingual-MiniLM-L12-v2`) diunduh dan dimuat ke cache saat
permintaan pertama. Setelah itu konsisten di bawah 0,3 detik. Bukan hang —
tunggu saja.

**Parameter API-nya `query`, bukan `q`.**

```
http://localhost:8000/search?query=iphone 13 second     # benar
http://localhost:8000/search?q=iphone                   # -> 422
```

**Demo berjalan di mode data sintetik.** `docker-compose.yml` menyetel
`DATA_SOURCE=fixture`, yang membaca `tests/fixtures/sample_stores.json`. Data
itu **kami buat sendiri, bukan hasil scraping toko sungguhan**, sehingga:

- nama toko dan tautannya tidak mengarah ke halaman Tokopedia yang nyata;
- kata kunci pencarian **belum memengaruhi hasil** di mode ini — apa pun yang
  diketik, yang muncul lima toko contoh yang sama (`iphone 13 second`).

Modul scraping langsung ada di `app/fetcher.py` dan aktif kalau `DATA_SOURCE`
diubah ke selain `fixture`, tapi mode fixture dipakai sebagai bawaan supaya
demonstrasi dapat direproduksi tanpa bergantung pada situs pihak ketiga.

---

## Menjalankan tanpa Docker

Backend dulu, baru frontend — frontend hanya UI yang memanggil API.

```powershell
python -m venv .venv
.\.venv\Scripts\python.exe -m pip install -r requirements.txt
copy .env.example .env
```

Terminal 1 — backend:

```powershell
.\.venv\Scripts\python.exe -m uvicorn app.main:app --port 8000
```

Terminal 2 — frontend:

```powershell
.\.venv\Scripts\python.exe -m streamlit run frontend\streamlit_app.py
```

---

## Menjalankan tes

```bash
python -m pytest tests/ -q          # 202 tes
```

Batasi ke `tests/` — direktori lain di repo memuat berkas tes pihak ketiga yang
bukan bagian dari proyek ini.

---

## Cara kerja penilaian keaslian review

Dua lapis dengan kontrak keluaran identik `{score, source, reasons}`, dipilih di
`app/review_analysis/__init__.py`:

- **Lapis 1 — heuristik** (`embedding.py`): near-duplicate antar review +
  clustering waktu posting. Selalu tersedia, tidak butuh berkas model.
- **Lapis 2 — IndoBERT fine-tuned** (`finetuned.py`): **dimatikan** lewat
  gerbang `LAPIS2_AKTIF = False`.

Lapis 2 dimatikan berdasarkan hasil pengukuran, bukan karena belum selesai. Pada
`data/test_real.jsonl` (97 review teradjudikasi):

| | recall bot | macro F1 |
|---|---|---|
| IndoBERT fine-tuned | 0,0% (0 dari 22) | 0.436 |
| Penebak kelas mayoritas | 0% | 0.436 |
| Heuristik Lapis 1 | 4,5% (1 dari 22) | **0.477** |

Pada `data/test_synthetic.jsonl` model justru mencetak recall bot **99,6%**.
Artinya yang dipelajari adalah *"apakah teks ini ditulis LLM"*, bukan *"apakah
review ini bot"* — kelas bot pada data latih seluruhnya review sintetik hasil
LLM, sementara bot marketplace nyata adalah copy-paste manusia. Alasan lengkap
dan syarat menyalakannya kembali tertulis di komentar konstanta `LAPIS2_AKTIF`.

Berkas model tidak di-commit (`/ml/model` di `.gitignore`, ~500 MB), jadi pada
repo bersih Lapis 2 memang tidak tersedia dan sistem memakai Lapis 1.

Reproduksi angkanya:

```bash
python ml/evaluate.py --test data/test_real.jsonl
python ml/evaluate.py --test data/test_synthetic.jsonl
```

---

## Perkakas data & anotasi

```bash
python -m ml.build_dataset pack                    # siapkan antrean pelabelan
streamlit run ml/annotate.py -- --queue <antrean> --out <keluaran>
python -m ml.check_rubric <berkas anotasi>         # linter rubrik, exit 1 kalau melanggar
python -m ml.calibration score --pool <pass1> --batch <pass2>
```

Rubrik pelabelan: `context/11-annotation-rubric.md`. Alat anotasi menegakkan
aturannya saat pelabelan — label `bot` pada review berkeluhan ditahan untuk
dikonfirmasi, dan yang menembus penjagaan ditandai `rubrik_override`.

---

## Batasan yang diakui

- **Label adalah plausibilitas, bukan kebenaran.** Tidak ada yang tahu label
  sesungguhnya; jangan membacanya sebagai ground truth.
- **Kesepakatan antar-anotator rendah** (κ 0.033–0.061 pada 500 review, tiga
  anotator). Investigasi menunjukkan penyebabnya 86 pelanggaran aturan mekanis
  rubrik, yang kemudian ditutup dengan penjagaan di alat pelabelan.
- **Konsistensi diri κ 0.647** (85% cocok, 100 review, urutan teracak, jeda 41
  menit, protokol identik). Konsisten tidak berarti benar.
- **Tanpa konteks toko dan waktu pada test set.** Sumber data publik tidak
  menyertakan `store_id` maupun `posted_at`, jadi `test_real.jsonl` hanya
  mengevaluasi klasifikasi teks — bukan heuristik Lapis 1 yang bekerja per toko.

Rincian: `data/README.md` dan `context/`.
