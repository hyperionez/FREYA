from __future__ import annotations

import json
import random
from datetime import datetime, timezone
from pathlib import Path

OUTPUT_PATH = Path(__file__).resolve().parent / "data" / "annotations.jsonl"
EXAMPLES_PER_CLASS = 500
SEED = 42

BOT_CORE_PHRASES = [
    "Barang bagus, pengiriman cepat",
    "Sesuai deskripsi, recommended seller",
    "Produk ori, packing rapi",
    "Puas belanja disini, respon cepat",
    "Kualitas oke, harga bersahabat",
    "Mantap, sudah langganan disini",
    "Top seller, barang sampai dengan selamat",
    "Sangat memuaskan, terpercaya",
    "Pengiriman kilat, barang sesuai pesanan",
    "Toko terbaik, pelayanan ramah",
    "Barang original, kualitas terjamin",
    "Fast respon, packing aman",
    "Belanja disini selalu puas",
    "Sesuai gambar, kualitas mantap",
    "Recommended banget, tidak mengecewakan",
]
BOT_TAILS = [
    "terima kasih ya",
    "makasih seller",
    "top seller",
    "jos gandos",
    "mantap jiwa",
    "5 bintang",
    "lanjut order lagi",
    "",
    "",
]
BOT_EMOJI = ["", "", "", "👍", "🔥", "😍", "✨"]
BOT_PUNCT = ["!", "!!", "!!!", "."]

PRODUCTS = [
    "sepatunya", "tasnya", "bajunya", "hp-nya", "casing-nya", "skincare-nya",
    "kaosnya", "celananya", "jamnya", "headset-nya", "powerbank-nya", "sandalnya",
    "dompetnya", "jaketnya", "kabelnya", "botol minumnya",
]
ASLI_POSITIVE_DETAIL = [
    "warnanya persis kayak di foto, bahannya juga adem",
    "ukurannya pas, tapi agak beda dikit sama size chart",
    "fungsinya oke banget buat dipakai sehari-hari",
    "baterainya awet, dipakai dari pagi sampe malem masih kuat",
    "jahitannya rapi, ga ada benang yang lepas",
    "wanginya ga terlalu menyengat, cocok di kulit sensitif",
    "packingnya tebel banget, bubble wrap sampe 3 lapis",
    "responsif banget pas dites, ga ada lag",
]
ASLI_NEGATIVE_DETAIL = [
    "sayangnya pengiriman agak lama, sekitar seminggu baru sampai",
    "ada sedikit lecet di bagian sudut waktu nyampe",
    "warnanya agak beda tipis dari foto tapi masih oke",
    "kemasannya sempet penyok tapi isinya aman",
    "size-nya kekecilan buat aku, mungkin perlu naik satu ukuran",
    "baunya agak beda dari yang aku ekspektasiin",
    "ada satu bagian yang jahitannya kurang rapi",
]
ASLI_CONTEXT = [
    "beli ini buat kado ulang tahun adek",
    "dipakai buat kerja WFH sehari-hari",
    "ini pembelian kedua aku disini, sebelumnya juga oke",
    "beli karena butuh cepat buat acara minggu depan",
    "awalnya ragu, tapi ternyata worth it juga",
    "dipakai anak aku, dia suka banget",
    "buat dipakai olahraga tiap weekend",
    "",
    "",
]
ASLI_OPENERS = [
    "Overall", "Jujur", "Menurut aku", "Sejauh ini", "Setelah dipakai beberapa hari",
    "Baru sampai hari ini", "Udah dipakai seminggu",
]


def _rng() -> random.Random:
    return random.Random(SEED)


def generate_bot_review(rng: random.Random) -> str:
    phrase = rng.choice(BOT_CORE_PHRASES)
    tail = rng.choice(BOT_TAILS)
    emoji = rng.choice(BOT_EMOJI)
    punct = rng.choice(BOT_PUNCT)
    parts = [phrase]
    if tail:
        parts.append(tail)
    text = ", ".join(parts) + punct
    if emoji:
        text = f"{text} {emoji}"
    return text


def generate_asli_review(rng: random.Random) -> str:
    product = rng.choice(PRODUCTS)
    opener = rng.choice(ASLI_OPENERS)
    sentiment_roll = rng.random()
    if sentiment_roll < 0.55:
        detail = rng.choice(ASLI_POSITIVE_DETAIL)
    elif sentiment_roll < 0.85:
        detail = rng.choice(ASLI_NEGATIVE_DETAIL)
    else:
        detail = f"{rng.choice(ASLI_POSITIVE_DETAIL)}, tapi {rng.choice(ASLI_NEGATIVE_DETAIL)}"
    context = rng.choice(ASLI_CONTEXT)
    sentence = f"{opener}, {product} {detail}."
    if context:
        sentence = f"{sentence} {context.capitalize()}."
    return sentence


def build_dataset() -> list[dict]:
    rng = _rng()
    records = []
    now = datetime.now(timezone.utc).isoformat()

    for i in range(EXAMPLES_PER_CLASS):
        records.append({
            "review_id": f"dummy-bot-{i:04d}",
            "text": generate_bot_review(rng),
            "retrieved_patterns": [],
            "label": "bot",
            "annotated_by": "dummy_generator_v1",
            "annotated_at": now,
        })

    for i in range(EXAMPLES_PER_CLASS):
        records.append({
            "review_id": f"dummy-asli-{i:04d}",
            "text": generate_asli_review(rng),
            "retrieved_patterns": [],
            "label": "asli",
            "annotated_by": "dummy_generator_v1",
            "annotated_at": now,
        })

    rng.shuffle(records)
    return records


def main() -> None:
    records = build_dataset()
    OUTPUT_PATH.parent.mkdir(parents=True, exist_ok=True)
    with OUTPUT_PATH.open("w", encoding="utf-8") as f:
        for record in records:
            f.write(json.dumps(record, ensure_ascii=False) + "\n")
    print(f"Wrote {len(records)} records to {OUTPUT_PATH}")


if __name__ == "__main__":
    main()
