"""Definisi gaya review bot untuk generasi data sintetik (kelas label=1).

## Kenapa versi ini berbeda dari yang pertama

Versi pertama menghasilkan kelas bot yang bisa dipisahkan dari review asli
**tanpa melihat isinya sama sekali** (diukur `ml/register_stats.py`):

    korpus                     median kata  singkatan  formal  huruf kecil di awal
    review asli (publik)              11.0      48.5%   48.0%               53.9%
    review bot berlabel tangan         9.5      28.5%   47.7%               52.3%
    review bot sintetik (lama)        17.0       5.3%   71.1%                2.9%

Kapitalisasi saja sudah memisahkan hampir sempurna: 2.9% lawan ~54%. Gaya
`overly_formal` yang lama bahkan secara harfiah memerintahkan "tidak ada
singkatan, tidak ada typo, struktur kalimat rapi sempurna" - artinya kita
melatih pendeteksi tulisan baku, bukan pendeteksi review yang dibeli.

Akibatnya terukur: 15 kata penanda "bot" terkuat yang dipelajari model ternyata
`sangat`, `ini`, `yang`, `dan` - kata tata bahasa, bukan tanda kecurangan.
Model mendapat 99.7% di validasi dan **0.8% recall bot** di data berlabel tangan.

## Dua perubahan

1. **`REGISTER_RULES`** dipasang di setiap prompt: ragam santai marketplace,
   singkatan, huruf kecil, kalimat pendek. Kelas bot harus berbeda dari review
   asli karena *maksud dan strukturnya*, bukan karena *cara mengetiknya*.

2. **Setiap gaya dipetakan ke satu sinyal di rubrik anotasi**
   (`context/11-annotation-rubric.md` bagian 3). Anotator manusia menandai bot
   memakai sinyal-sinyal itu; kalau data latih dibangun dari sinyal yang sama,
   yang dipelajari model sejalan dengan yang dinilai gold set.

## Soal gaya pendek

Versi pertama sengaja membuang gaya pendek dengan alasan review bot pendek
tumpang tindih dengan 16.7% review asli. Penalarannya masuk akal, tapi
premisnya terbantah data berlabel tangan: review bot sungguhan justru
**lebih pendek** dari review asli (median 9.5 lawan 11.5 kata). Membuang
rentang pendek berarti membuang wilayah tempat bot sungguhan hidup, dan
itulah yang membuat model gagal menyeberang.

Panjang tetap tidak boleh jadi satu-satunya pembeda - karena itu target kata
tiap gaya di bawah ini mengelilingi median review asli, bukan menjauhinya.
"""

from __future__ import annotations

REGISTER_RULES = """- Tulis seperti orang Indonesia mengetik cepat di HP, bukan seperti artikel.
- Mayoritas diawali HURUF KECIL. Tanda baca boleh berantakan atau tidak ada.
- Pakai singkatan sehari-hari: yg, dgn, bgt, sdh, tdk, gak, utk, aja, jd, tp, kalo, pake.
- Boleh ada typo, huruf diulang (mantapp, bagusss), dan titik berlebih (..).
- Kalimat pendek dan terpotong. Hindari kata sambung baku seperti 'sehingga',
  'merupakan', 'tersebut'.
- JANGAN menulis paragraf rapi berstruktur subjek-predikat lengkap."""

BOT_STYLES: tuple[dict, ...] = (
    {
        "name": "generic_praise",
        "rubric": "3.1 pujian tanpa rujukan produk",
        "words": (4, 10),
        "instruction": (
            "Pujian umum yang bisa ditempel ke produk apa pun tanpa berubah makna. "
            "Tidak menyebut satu pun sifat konkret barangnya - tidak ada ukuran, "
            "warna, rasa, bahan, atau cara pakai."
        ),
    },
    {
        "name": "template_repetitive",
        "rubric": "3.2 struktur template",
        "words": (10, 18),
        "instruction": (
            "Urutan kaku yang selalu sama: kualitas barang, lalu pengiriman, lalu "
            "penjual. Tiap bagian satu frasa pendek, ritmenya seragam, tanpa variasi."
        ),
    },
    {
        "name": "call_to_action",
        "rubric": "3.3 ajakan bertindak",
        "words": (6, 14),
        "instruction": (
            "Berjualan ke pembaca, bukan bercerita: 'buruan order', 'jangan ragu "
            "beli disini', 'dijamin gak nyesel', 'langsung checkout aja'."
        ),
    },
    {
        "name": "keyword_stuffed",
        "rubric": "3.4 penjejalan kata kunci",
        "words": (8, 16),
        "instruction": (
            "Mengulang nama kategori produk berkali-kali secara tidak wajar, seolah "
            "dioptimasi mesin pencari. Contoh bentuk: 'sepatu pria sepatu olahraga "
            "sepatu murah bagus bgt'."
        ),
    },
    {
        "name": "misplaced_formal",
        "rubric": "3.5 formalitas yang tidak pada tempatnya",
        "words": (10, 18),
        "instruction": (
            "Nada kelewat sopan dan kaku untuk kolom review - seperti membalas surat "
            "resmi. TETAP pakai ragam mengetik di HP: huruf kecil dan singkatan tetap "
            "muncul, yang janggal adalah nadanya, bukan ejaannya."
        ),
    },
    {
        "name": "superlative_stack",
        "rubric": "3.6 superlatif bertumpuk tanpa isi",
        "words": (5, 12),
        "instruction": (
            "Superlatif ditumpuk beruntun tanpa satu pun fakta pendukung: 'terbaik "
            "sepanjang masa', 'paling juara sedunia', 'mantap luar biasa banget'."
        ),
    },
)

_PROMPT_TEMPLATE = """Kamu membuat DATA LATIH SINTETIK untuk riset deteksi review palsu di e-commerce Indonesia.

Tugas: tulis {count} contoh review produk berbahasa Indonesia yang MEMANG SENGAJA dibuat terdengar seperti review bot / review yang dibeli.

Ciri bot yang harus muncul: {style_instruction}

Panjang tiap review: {low}-{high} kata. Jangan lebih panjang dari itu.

CARA MENGETIK (ini wajib, jangan diabaikan):
{register_rules}

Aturan lain:
- JANGAN sebut nama toko asli, merek asli, nama orang, nomor telepon, atau URL.
- Variasikan kategori produk (elektronik, fashion, makanan, perabot, kosmetik).
- Jangan beri penomoran, tanda kutip pembungkus, atau penjelasan apa pun.

Keluarkan HANYA array JSON berisi string, tanpa blok kode. Contoh bentuk:
["review pertama", "review kedua"]"""


def build_prompt(style: dict, count: int) -> str:
    if count <= 0:
        raise ValueError(f"count harus positif, dapat {count}")
    low, high = style["words"]
    return _PROMPT_TEMPLATE.format(
        count=count,
        style_instruction=style["instruction"],
        register_rules=REGISTER_RULES,
        low=low,
        high=high,
    )
