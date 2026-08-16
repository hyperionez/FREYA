# Rubrik Anotasi — Review Bot vs Review Asli

Acuan tunggal saat melabeli `data/to_label.jsonl`. Dibaca **sebelum** label pertama,
dan dibuka lagi setiap kali ragu. Tanpa rubrik, label yang terkumpul tidak konsisten
dan model belajar dari kebisingan.

Terkait: `09-track-b-finetuning-pipeline.md` (alur), `04-fraud-signal-features.md`
(sinyal fraud tingkat toko), `data/README.md` (skema & batasan dataset).

---

## 1. Prinsip yang tidak boleh dilanggar

**Label datang dari penilaian manusia, bukan dari heuristik.** Jangan melabeli
dengan cara membayangkan apa yang akan dijawab `app/review_analysis/embedding.py`
(near-duplicate + time clustering). Kalau label hanya meniru heuristik, evaluasi
"model vs heuristik" jadi sirkular dan angkanya tidak berarti apa-apa.

**Jangan pula meniru gaya data sintetik.** Kelas bot di `train.jsonl` dibangkitkan
LLM dalam empat gaya (`ml/synth_prompts.py`). Kalau saat melabeli kita hanya
mencari empat gaya itu, `test_real.jsonl` berhenti mengukur generalisasi — padahal
justru itu satu-satunya alasan ia ada.

**Satu review dinilai apa adanya.** Anotator hanya melihat teks; tidak ada info
toko, waktu posting, atau review tetangga (lihat §8). Nilai berdasarkan yang
terlihat, jangan mengarang konteks.

---

## 2. Tiga label

| Nilai | Arti | Kapan dipakai |
|---|---|---|
| `0` | **Asli** — plausibel ditulis pembeli sungguhan | Ada jejak pengalaman personal, atau keluhan/kekecewaan, atau detail spesifik produk |
| `1` | **Bot** — plausibel dibuat/dibeli untuk memanipulasi | Memenuhi minimal dua sinyal §3, dan tidak ada sinyal §4 yang membatalkan |
| `"ragu"` | **Tidak dapat ditentukan** | Bukti tidak cukup ke salah satu arah |

`"ragu"` bukan tanda gagal — baris itu dibuang saat evaluasi. **Memaksakan tebakan
pada review ambigu jauh lebih merusak** daripada menandainya ragu, karena ia
menyuntikkan kebisingan ke satu-satunya test set yang mengukur kelayakan model.

Target sehat: `"ragu"` di kisaran 10–20%. Kalau jauh di bawah itu, kemungkinan
besar kita menebak-nebak. Kalau jauh di atas, rubrik ini perlu dipertajam.

---

## 3. Sinyal yang MENDUKUNG label bot

Tidak ada satu pun yang cukup sendirian. **Butuh minimal dua.**

1. **Pujian tanpa rujukan produk.** Memuji panjang lebar tapi tidak menyebut satu
   pun sifat konkret barangnya — bisa ditempel ke produk apa saja tanpa berubah makna.
2. **Struktur template.** Urutan kaku yang terasa diisi ke dalam cetakan:
   kualitas → pengiriman → penjual → ajakan beli, tanpa variasi ritme.
3. **Ajakan bertindak.** "Buruan order", "jangan ragu beli di sini", "dijamin
   tidak menyesal" — pembeli asli menulis untuk pembaca, bukan berjualan.
4. **Penjejalan kata kunci.** Nama kategori/produk diulang tidak wajar, seperti
   dioptimasi untuk pencarian, bukan untuk dibaca.
5. **Formalitas yang tidak pada tempatnya.** Bahasa seperti siaran pers atau
   surat resmi di kolom review marketplace.
6. **Superlatif bertumpuk tanpa isi.** "Sangat memuaskan sekali", "terbaik
   sepanjang masa" beruntun, tanpa satu pun fakta pendukung.

---

## 4. Yang BUKAN bukti (jebakan paling sering)

Poin-poin ini menggoda tapi menyesatkan. Melabeli berdasarkan ini akan merusak dataset.

- **Pendek ≠ bot.** Sudah diukur: rentang panjang review bot pendek menampung
  **16,7% review asli**. `barang bagus, seller ramah..` itu asli. Justru karena
  jebakan ini, gaya `generic_short` dibuang dari data sintetik (lihat `data/README.md`).
- **Positif ≠ bot.** Mayoritas review marketplace memang positif. Kepuasan bukan
  kecurigaan.
- **Bintang 5 ≠ bot.** Distribusi rating asli condong ke atas secara alami.
- **Typo, singkatan, huruf besar acak ≠ asli.** Generator modern meniru ini dengan
  mudah. Ketidakrapian bukan sertifikat keaslian.
- **Bahasa gaul/alay ≠ asli.** Sama seperti di atas.
- **Emoji ≠ penanda apa pun.** Dipakai kedua kelas.
- **Mirip review lain ≠ bot** pada level satu review. Kemiripan antar-review adalah
  sinyal tingkat *toko* dan sudah ditangani heuristik Lapis 1. Anotator menilai
  satu review, bukan kelompok.

---

## 5. Urutan keputusan

Jalankan berurutan, berhenti di langkah pertama yang terpenuhi.

1. Teks rusak, kosong, bukan review, atau bukan Bahasa Indonesia → **`"ragu"`**.
2. Ada keluhan, kekecewaan, kritik, atau penyebutan masalah konkret → **`0`**
   (review yang dibeli hampir tidak pernah mengeluh).
3. Ada detail pengalaman personal yang spesifik dan sulit ditempel ke produk lain
   (ukuran, warna meleset, lama pemakaian, perbandingan, kondisi saat tiba) → **`0`**.
4. Terpenuhi **≥2** sinyal §3 → **`1`**.
5. Sisanya → **`"ragu"`**.

Batas waktu: **maksimal ~15 detik per review**. Kalau lebih lama, jawabannya
`"ragu"`. Kecepatan lebih penting daripada kesempurnaan — 250 label yang wajar
lebih berharga daripada 60 label yang sempurna.

---

## 6. Contoh terkalibrasi

Diambil dari data nyata proyek ini.

| Teks | Label | Alasan |
|---|---|---|
| `gak bisa di pakai??` | `0` | Keluhan → langkah 2 |
| `Sangat presisi dan pas` | `0` | Detail sifat fisik barang |
| `barang bagus, seller ramah..` | `"ragu"` | Generik, tapi pendek bukan bukti (§4) |
| `mantap paten joss` | `"ragu"` | Tidak ada isi ke arah mana pun |
| `Alhamdulillah berfungsi dengan baik. Packaging aman. Respon cepat dan ramah. Seller dan kurir amanah` | `0` | Ada rujukan konkret (fungsi, kemasan), ritme alami |
| `Kualitas barang sangat bagus dan berfungsi dengan sangat baik sesuai deskripsi produk. Pengiriman sangat cepat sekali dan kurirnya juga sangat ramah. Penjual sangat responsif dan amanah banget. Pokoknya jangan ragu untuk beli di sini guys recommended banget deh.` | `1` | Template (§3.2) + ajakan bertindak (§3.3) + superlatif bertumpuk (§3.6) |

---

## 7. Kalibrasi

Rulebook lomba mengasumsikan dua annotator dan mengukur kesepakatan lewat kappa.
**Kalau dikerjakan sendirian**, ganti dengan konsistensi diri:

1. Labeli 50 review pertama.
2. Kerjakan hal lain minimal 30 menit.
3. Labeli ulang 50 review yang sama tanpa melihat hasil pertama.
4. Hitung berapa persen yang cocok.

- **≥85% cocok** → rubrik cukup tajam, lanjutkan.
- **70–85%** → tajamkan definisi yang paling sering berubah, baru lanjut.
- **<70%** → tugasnya belum terdefinisi; perbaiki rubrik dulu. Melanjutkan hanya
  memproduksi kebisingan.

Angka ini **wajib masuk proposal** sebagai lampiran. Konsistensi anotator yang
diakui apa adanya lebih bernilai di mata juri daripada klaim akurasi tanpa dasar.

---

## 8. Batasan yang diakui

- **Tanpa konteks toko dan waktu.** Sumber `PRDECT-ID` tidak menyertakan
  `store_id` maupun `posted_at`, jadi `test_real.jsonl` hanya bisa mengevaluasi
  klasifikasi teks — **bukan** heuristik Lapis 1 yang bekerja per toko.
- **Bot yang ditulis dengan baik tidak akan tertangkap.** Review bayaran yang
  ditulis manusia dengan detail konkret akan dilabeli `0`, dan memang seharusnya
  begitu — anotator tidak punya bukti untuk menyimpulkan sebaliknya.
- **Ini label plausibilitas, bukan kebenaran.** Tidak ada seorang pun yang tahu
  label sesungguhnya. Sebut demikian di proposal; jangan mengklaim ground truth.
