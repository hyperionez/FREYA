"""Definisi gaya review bot untuk generasi data sintetik (kelas label=1).

Kenapa banyak gaya: kalau semua review bot dihasilkan dari satu prompt, model
cuma belajar menghafal satu pola generator dan metrik jadi menggelembung.
Variasi gaya memaksa model belajar sinyal yang lebih umum.

Kenapa TIDAK ada gaya "generic_short": review bot pendek (15-35 karakter)
tumpang tindih dengan 16.7% review asli -- "barang bagus, seller ramah.."
(asli) praktis identik dengan "barang bagus sekali mantap" (bot). Gaya itu
mengajari model "pendek = bot", yang menggelembungkan skor pada holdout
sintetik lalu ambruk pada data berlabel tangan. Sinyal bot yang layak
dipelajari bersifat struktural, bukan soal panjang.
"""

from __future__ import annotations

BOT_STYLES: tuple[dict[str, str], ...] = (
    {
        "name": "overly_formal",
        "instruction": (
            "Bahasa Indonesia baku dan formal berlebihan, seperti siaran pers. "
            "Tidak ada singkatan, tidak ada typo, struktur kalimat rapi sempurna."
        ),
    },
    {
        "name": "superlative_spam",
        "instruction": (
            "Penuh superlatif dan tanda seru. Kata seperti 'luar biasa', "
            "'sangat memuaskan sekali', 'terbaik sepanjang masa'. Tanpa detail konkret."
        ),
    },
    {
        "name": "template_repetitive",
        "instruction": (
            "Mengikuti template kaku yang sama: sebut kualitas, lalu pengiriman, "
            "lalu penjual, lalu ajakan beli. Urutannya selalu identik."
        ),
    },
    {
        "name": "keyword_stuffed",
        "instruction": (
            "Menjejalkan nama kategori produk dan kata kunci jualan berulang-ulang "
            "secara tidak wajar, seolah dioptimasi untuk pencarian."
        ),
    },
)

_PROMPT_TEMPLATE = """Kamu membuat DATA LATIH SINTETIK untuk riset deteksi review palsu di e-commerce Indonesia.

Tugas: tulis {count} contoh review produk berbahasa Indonesia yang MEMANG SENGAJA dibuat terdengar seperti review bot / review yang dibeli.

Gaya yang harus dipakai: {style_instruction}

Aturan wajib:
- Bahasa Indonesia sehari-hari e-commerce, bukan terjemahan.
- JANGAN sebut nama toko asli, merek asli, nama orang, nomor telepon, atau URL.
- Variasikan kategori produk (elektronik, fashion, makanan, perabot, kosmetik).
- Panjang bervariasi dalam batas gaya di atas.
- Jangan beri penomoran, tanda kutip pembungkus, atau penjelasan apa pun.

Keluarkan HANYA array JSON berisi string, tanpa blok kode. Contoh bentuk:
["review pertama", "review kedua"]"""


def build_prompt(style: dict[str, str], count: int) -> str:
    return _PROMPT_TEMPLATE.format(count=count, style_instruction=style["instruction"])
