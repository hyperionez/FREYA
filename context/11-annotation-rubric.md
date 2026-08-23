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
toko, waktu posting, atau review tetangga (lihat §9). Nilai berdasarkan yang
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

Rasio `"ragu"` yang wajar ditentukan **bentuk data**, bukan angka tetap. Diukur di
kolam 500 review proyek ini: 41% review lebih pendek dari 60 karakter, dan 34%
pendek **tanpa** keluhan — seluruhnya jatuh ke langkah 5 kalau urutan keputusan
§5 dijalankan apa adanya. Jadi rasio ragu **20–40% itu normal di kolam ini**, dan
yang justru mencurigakan adalah rasio jauh di bawahnya: itu tanda review ambigu
dipaksa dijawab.

> Target lama "10–20%" di dokumen ini salah dan sudah dicabut. Angka itu ditetapkan
> tanpa melihat distribusi panjang review, lalu dipakai memarahi anotator yang
> sebenarnya patuh. Kalau kolam datanya berganti, hitung ulang porsi "pendek tanpa
> keluhan" dan sesuaikan ambangnya di `ml/check_rubric.py`.

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
   (review yang dibeli hampir tidak pernah mengeluh). **`"ragu"` bukan jalan
   tengah di sini** — kalau langkah 1 tidak terpenuhi, keluhan berarti `0`, titik.
   Menjawab `"ragu"` pada review berkeluhan hanya membuang baris yang justru
   paling jelas labelnya.
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

**Konsistensi diri adalah jalur utama, bukan pengganti darurat.** Versi lama
dokumen ini menyatakan "rulebook lomba mengasumsikan dua annotator dan mengukur
kesepakatan lewat kappa" — itu **tidak benar**. Seluruh 320 baris
`AIC_AI_Innovation_Challenge_Rulebook.md` tidak menyebut anotator, kappa, maupun
reliabilitas label satu kali pun. Yang dinilai rulebook (bobot 15%) adalah apakah
keputusan teknis dijelaskan dengan alasan berbasis data dan apakah proses
pengembangannya reflektif. Satu anotator yang mengukur dirinya sendiri dengan
jujur memenuhi itu; tiga anotator dengan kappa 0.04 tidak.

Alurnya (`ml/calibration.py` menjalankan keduanya):

1. `python -m ml.calibration sample --pool <label pass 1> --out <batch>`
2. Labeli batch dengan `ml/annotate.py`.
3. Jeda minimal 30 menit — makin lama makin jujur.
4. Labeli ulang batch yang sama tanpa melihat hasil pertama.
5. `python -m ml.calibration score --pool <pass 1> --batch <pass 2>`

- **≥85% cocok** → rubrik cukup tajam, lanjutkan.
- **70–85%** → tajamkan definisi yang paling sering berubah, baru lanjut.
- **<70%** → tugasnya belum terdefinisi; perbaiki rubrik dulu.

**Syarat yang mudah terlewat: kedua pass harus memakai protokol yang sama.**
Membandingkan pass yang dijaga alat dengan pass lama yang melanggar rubrik akan
mengukur *perubahan protokol*, bukan konsistensi — dan angkanya keluar rendah
walaupun pass kedua justru lebih benar. Pernah terjadi di proyek ini: 57% cocok,
kappa 0.334, padahal seluruh 43 selisihnya bergerak satu arah menjauhi `bot` dan
9 pelanggaran langkah 2 hilang jadi nol. Kalau protokolnya baru berubah, ulangi
kalibrasi dengan **dua pass yang sama-sama dijaga**.

Angka ini **wajib masuk proposal** sebagai lampiran. Konsistensi anotator yang
diakui apa adanya lebih bernilai di mata juri daripada klaim akurasi tanpa dasar.

---

## 8. Penjagaan alat

Sebagian aturan di atas bisa diperiksa mesin, jadi tidak lagi digantungkan pada
disiplin manusia di jam keempat melabeli. Alasannya empiris: tanpa penjagaan,
tiga anotator menghasilkan **86 pelanggaran langkah 2** pada 500 review, dan
kappa berpasangan jatuh di 0.033–0.061.

`ml/annotate.py` — saat melabeli:

- Review dengan penanda keluhan menampilkan petunjuk langkah 2 **sebelum** tombol
  ditekan.
- Label `bot` pada review berkeluhan atau review pendek ditahan untuk
  dikonfirmasi, bukan diblokir. Leksikon keluhannya presisi-tinggi dan pasti
  melewatkan sebagian kasus, jadi penilaian manusia harus tetap bisa menang.
- Label yang menembus penjagaan ditandai `rubrik_override: true` — yang ditembus
  harus bisa ditinjau ulang.

`ml/check_rubric.py` — setelah melabeli:

    python -m ml.check_rubric annotations/berkas.jsonl

Keluar dengan kode 1 kalau ada pelanggaran, jadi bisa dipakai sebagai gerbang
sebelum berkas anotasi diterima. Yang dilaporkan: pelanggaran langkah 2 (keras),
rasio ragu di luar rentang §2, review pendek dilabeli bot (§4), dan keluhan
dilabeli ragu (§5 langkah 2). Tiga yang terakhir bersifat saran tinjau ulang.

Angka pelanggaran dari alat ini adalah **batas bawah**: leksikonnya sengaja tidak
lengkap supaya tidak salah-tuduh.

---

## 9. Batasan yang diakui

- **Tanpa konteks toko dan waktu.** Sumber `PRDECT-ID` tidak menyertakan
  `store_id` maupun `posted_at`, jadi `test_real.jsonl` hanya bisa mengevaluasi
  klasifikasi teks — **bukan** heuristik Lapis 1 yang bekerja per toko.
- **Bot yang ditulis dengan baik tidak akan tertangkap.** Review bayaran yang
  ditulis manusia dengan detail konkret akan dilabeli `0`, dan memang seharusnya
  begitu — anotator tidak punya bukti untuk menyimpulkan sebaliknya.
- **Ini label plausibilitas, bukan kebenaran.** Tidak ada seorang pun yang tahu
  label sesungguhnya. Sebut demikian di proposal; jangan mengklaim ground truth.
