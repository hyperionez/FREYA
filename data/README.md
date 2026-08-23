# Dataset — deteksi review bot

Dibangun oleh `ml/build_dataset.py`. Jalankan semua perintah **dari root repo**.

## Kelas

| Label | Arti | Sumber |
|---|---|---|
| `0` | review asli (ditulis manusia) | dataset review e-commerce Indonesia publik |
| `1` | review bot / dibeli | dihasilkan LLM dalam 4 gaya berbeda (`ml/synth_prompts.py`) |

Metode ini mengikuti pendekatan Salminen dkk. (Fake Reviews Dataset, OSF) — review
asli sebagai kelas negatif, review yang sengaja dibangkitkan sebagai kelas positif —
diadaptasi ke Bahasa Indonesia karena dataset fake-review berbahasa Indonesia
berlabel belum tersedia publik.

## Berkas

| Berkas | Isi | Di-commit? |
|---|---|---|
| `raw/` | unduhan mentah dari sumber publik | tidak |
| `interim/real.jsonl` | review asli setelah anonimisasi & dedup | tidak |
| `interim/synth.jsonl` | review bot hasil generasi | tidak |
| `train.jsonl` | data latih, seimbang 50/50 | ya |
| `test_synthetic.jsonl` | holdout sintetik — uji *in-distribution* | ya |
| `to_label.jsonl` | kolam review asli untuk dilabeli tangan | ya |
| `test_real.jsonl` | gold set teradjudikasi — uji *out-of-distribution* | ya |

## Skema

`train.jsonl`, `test_synthetic.jsonl`:

```json
{"id": "syn-000001", "text": "...", "label": 1, "source": "llm_synthetic", "style": "superlative_spam"}
```

`to_label.jsonl` dan `test_real.jsonl` memakai nama field yang sama persis dengan
`tests/fixtures/sample_stores.json`, supaya hasilnya langsung cocok dengan pipeline:

```json
{"review_id": "t-0001", "store_id": null, "text": "...", "posted_at": null, "reviewer_rating": null, "label": null}
```

`posted_at` format ISO 8601 (`2026-07-14T10:22:00`), sama seperti yang di-parse
`app/review_analysis/embedding.py`.

## Dua test set, dan kenapa dua

- `test_synthetic.jsonl` mengukur apakah model bisa membedakan review asli dari
  review LLM. Angkanya akan tinggi — ini soal yang mudah.
- `test_real.jsonl` mengukur apakah kemampuan itu **menyeberang** ke review bot
  sungguhan di dunia nyata. Ini yang menentukan model layak dipasang atau tidak.

  Isinya salinan `calibration/gold100.jsonl`: 100 review yang dilabeli tiga
  anotator independen lalu diadjudikasi, 75 asli / 22 bot / 3 ragu. Baris `ragu`
  ikut tersimpan tapi dilewati `dataset_io.load_labeled_records`, jadi 97 baris
  yang benar-benar dinilai. Proporsinya sengaja tidak diseimbangkan supaya
  mencerminkan distribusi dunia nyata.

  Versi sebelumnya — 250 baris tanpa `annotated_by` — dipensiunkan: 241 barisnya
  berlabel identik dengan `test_real.pass1-sentimen.jsonl`, yaitu pass yang
  memakai pertanyaan sentimen dan sudah direset di commit b137fcc. Kesepakatannya
  dengan gold set hanya 60% pada 50 baris yang beririsan.

Selisih antara keduanya adalah temuan jujur yang wajib masuk proposal, bukan
kelemahan yang disembunyikan.

## Batasan yang diketahui

- **Split by store tidak penuh.** Dataset publik tidak menyertakan identitas toko,
  jadi `store_id` hanya terisi untuk review yang dilabeli tangan dari sumber yang
  punya info toko. Di luar itu, split jatuh ke held-out biasa. Sebutkan apa adanya.
- **Kelas bot berasal dari satu keluarga generator.** Empat gaya mengurangi risiko,
  tapi tidak menghilangkannya.
- **Review bot yang sangat pendek sengaja tidak dimodelkan.** Gaya `generic_short`
  (15-35 karakter) dibuang setelah diukur: rentang panjangnya menampung 16.7%
  review asli, sehingga "barang bagus, seller ramah.." (asli) tak terbedakan dari
  "barang bagus sekali mantap" (bot). Menyimpannya akan mengajari model bahwa
  pendek berarti bot — skor holdout sintetik naik semu, lalu ambruk pada data
  berlabel tangan. Konsekuensinya jujur: model ini **tidak** diharapkan menangkap
  review bot satu-frasa, dan kasus itu sebaiknya ditangani aturan terpisah.

## Anonimisasi

`ml/anonymize.py` mengganti nomor telepon, email, URL, mention, dan nama toko
dengan token placeholder sebelum apa pun ditulis ke disk. Diuji di
`tests/test_anonymize.py`.
