# Fraud Signal Features & Scoring Rules (MVP)

Prinsip: tiap sinyal dikonversi jadi kontribusi skor (positif = menambah kepercayaan, negatif = mengurangi). Total skor dibatasi 0-100.

## 1. Daftar Sinyal & Bobot Awal

| Sinyal | Deskripsi | Bobot | Arah | Sumber |
|---|---|---|---|---|
| `price_deviation` | Selisih harga toko vs median harga produk sejenis | 20 | Semakin jauh di bawah median → skor turun tajam | Rule-based (matematis) |
| `store_age` | Umur toko sejak dibuat | 15 | Toko < 30 hari → turun; > 1 tahun → naik | Rule-based |
| `rating` | Rating toko (0-5) | 15 | Linear: rating tinggi → naik | Rule-based |
| `review_count` | Jumlah ulasan toko | 10 | Review sangat sedikit (<10) → turun | Rule-based |
| `is_official_store` | Status toko resmi/verified | 10 | Official → bonus skor | Rule-based |
| `response_rate` | Tingkat respons chat penjual | 5 | Response rate rendah (<50%) → turun | Rule-based |
| `total_sold` | Jumlah transaksi sukses | 5 | Sangat sedikit transaksi tapi klaim harga murah → turun | Rule-based |
| `review_authenticity_score` | Skor keaslian review (bot vs asli) | 20 | Skor rendah (banyak indikasi bot) → turun tajam | Modul Review Analysis — lihat `08-review-analysis-module.md` |

> Bobot di atas adalah starting point, dikalibrasi ulang setelah uji manual terhadap sample toko nyata.

## 2. Contoh Rule Konkret — Sinyal Numerik (Pseudocode)

```python
def score_price_deviation(store_price, market_median):
    deviation = (store_price - market_median) / market_median
    if deviation <= -0.5:
        return -20
    elif deviation <= -0.3:
        return -12
    elif deviation <= -0.15:
        return -5
    return 0

def score_store_age(age_days):
    if age_days < 7:
        return -15
    elif age_days < 30:
        return -8
    elif age_days > 365:
        return +10
    return 0

def score_rating_review(rating, review_count):
    if review_count < 10:
        return -10
    if rating >= 4.5:
        return +15
    if rating >= 4.0:
        return +8
    if rating < 3.0:
        return -20
    return 0
```

## 3. Rule untuk `review_authenticity_score`

```python
def score_review_authenticity(authenticity_score):
    # authenticity_score: 0-100, dari Modul Review Analysis
    if authenticity_score < 30:
        return -20   # sangat indikatif bot
    elif authenticity_score < 60:
        return -8
    elif authenticity_score >= 85:
        return +10
    return 0
```

Skor akhir = `50 (baseline netral) + sum(semua kontribusi sinyal)`, di-clamp ke rentang 0-100.

## 4. Kombinasi Sinyal yang Perlu Diwaspadai (Compound Red Flags)
- **Toko baru + harga jauh di bawah pasar** → langsung set label maksimal "Berbahaya" meski sinyal lain netral.
- **Rating sempurna (5.0) tapi review_authenticity_score rendah** → highly suspicious, dua sinyal saling menguatkan indikasi review dibeli/bot.
- **review_count tinggi tapi review_authenticity_score rendah** → volume review besar tidak otomatis kredibel kalau banyak yang bot.

## 5. Alasan (Reasons) yang Ditampilkan ke User
Setiap kontribusi skor signifikan (|kontribusi| ≥ 10) diterjemahkan jadi kalimat, contoh:
- `"Harga jauh di bawah rata-rata pasar (indikasi produk palsu/scam)"`
- `"24% dari review terindikasi pola bot (duplikasi tinggi & waktu posting berkelompok)"`
