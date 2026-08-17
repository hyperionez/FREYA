"""Ukur "register" tulisan: seberapa mirip sebuah korpus dengan review marketplace asli.

Kenapa ini ada. Kelas bot sintetik yang lama bisa dipisahkan dari review asli
tanpa melihat isinya sama sekali - cukup dari cara menulisnya:

    korpus                     median kata  singkatan  formal  huruf kecil di awal
    review asli (publik)              11.0      48.5%   48.0%               53.9%
    review bot berlabel tangan         9.5      28.5%   47.7%               52.3%
    review bot sintetik (lama)        17.0       5.3%   71.1%                2.9%

Model yang dilatih di atas data itu belajar "Bahasa Indonesia formal dan rapi =
bot", bukan "review yang dibeli = bot". Hasilnya 99.7% di validasi dan 0.8%
recall bot di data berlabel tangan.

Modul ini membuat kesenjangan tersebut bisa diukur SEBELUM kuota generator
dibakar untuk membuat ulang 1500 review.
"""

from __future__ import annotations

import re
import statistics
from dataclasses import asdict, dataclass
from typing import Iterable

# Singkatan khas marketplace Indonesia. Bukan daftar lengkap - cukup jadi
# indikator apakah penulisnya memakai ragam santai atau ragam baku.
ABBREVIATIONS = (
    "yg", "dgn", "dg", "bgt", "sdh", "udh", "udah", "tdk", "gak", "ga", "nggak",
    "utk", "dr", "sy", "aja", "bs", "jd", "jg", "krn", "karna", "klo", "kalo",
    "tp", "blm", "hrs", "sm", "dpt", "trs", "pake", "gk", "bnyk", "bgs", "msh",
    "lg", "skrg", "kyk", "cepet", "sampe", "banget",
)

# Penanda ragam baku/formal. Generator LLM memakainya jauh lebih sering
# daripada pembeli sungguhan.
FORMAL_MARKERS = (
    "sangat", "yang", "dan", "ini", "tersebut", "sehingga", "merupakan",
    "adalah", "dengan", "untuk", "sekali", "memuaskan", "kualitas",
)

_ABBREVIATION_RE = re.compile(r"\b(?:%s)\b" % "|".join(ABBREVIATIONS), re.IGNORECASE)
_FORMAL_RE = re.compile(r"\b(?:%s)\b" % "|".join(FORMAL_MARKERS), re.IGNORECASE)

GAP_FIELDS = (
    "median_words",
    "abbreviation_rate",
    "formal_marker_rate",
    "lowercase_start_rate",
)


@dataclass(frozen=True)
class RegisterProfile:
    """Profil register satu korpus. Frozen supaya tidak terubah tak sengaja."""

    n: int
    median_words: float
    abbreviation_rate: float
    formal_marker_rate: float
    lowercase_start_rate: float

    def as_row(self, name: str) -> str:
        return (
            f"{name:<32}{self.n:>7}{self.median_words:>13.1f}"
            f"{self.abbreviation_rate:>11.1%}{self.formal_marker_rate:>9.1%}"
            f"{self.lowercase_start_rate:>10.1%}"
        )


HEADER = (
    f"{'korpus':<32}{'n':>7}{'median kata':>13}{'singkatan':>11}{'formal':>9}{'kecil':>10}"
)


def _starts_lowercase(text: str) -> bool:
    stripped = text.lstrip()
    return bool(stripped) and stripped[0].islower()


def register_profile(texts: Iterable[str]) -> RegisterProfile:
    """Hitung profil register sebuah korpus teks."""
    texts = [t for t in texts if t and t.strip()]
    if not texts:
        raise ValueError("korpus kosong: tidak ada teks untuk diukur")

    n = len(texts)
    return RegisterProfile(
        n=n,
        median_words=float(statistics.median(len(t.split()) for t in texts)),
        abbreviation_rate=sum(1 for t in texts if _ABBREVIATION_RE.search(t)) / n,
        formal_marker_rate=sum(1 for t in texts if _FORMAL_RE.search(t)) / n,
        lowercase_start_rate=sum(1 for t in texts if _starts_lowercase(t)) / n,
    )


def profile_gap(reference: RegisterProfile, candidate: RegisterProfile) -> dict[str, float]:
    """Selisih candidate terhadap reference. Nol berarti register sudah cocok.

    Positif = candidate lebih tinggi dari acuan. Untuk `formal_marker_rate`,
    positif berarti candidate terlalu baku; untuk `abbreviation_rate` dan
    `lowercase_start_rate`, negatif berarti candidate terlalu rapi.
    """
    ref, cand = asdict(reference), asdict(candidate)
    return {field: cand[field] - ref[field] for field in GAP_FIELDS}
