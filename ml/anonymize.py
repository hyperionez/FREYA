"""Anonimisasi teks review sebelum masuk data latih.

Guardrail: data latih & materi publik wajib anonim (nama boleh muncul di
output live, bukan di dataset yang di-commit).
"""

from __future__ import annotations

import re

_URL_PATTERN = re.compile(r"https?://\S+|www\.\S+", re.IGNORECASE)
_EMAIL_PATTERN = re.compile(r"\b[\w.+-]+@[\w-]+\.[\w.-]+\b")
_MENTION_PATTERN = re.compile(r"@[\w.]+")
# 08xxxxxxxxxx / +62xxxxxxxxxx, minimal 9 digit setelah prefix
_PHONE_PATTERN = re.compile(r"(?:\+?62|0)[\s.-]?8[\d\s.-]{7,13}\d")
_WHITESPACE_PATTERN = re.compile(r"\s+")

URL_TOKEN = "[URL]"
EMAIL_TOKEN = "[EMAIL]"
MENTION_TOKEN = "[USER]"
PHONE_TOKEN = "[TELEPON]"
STORE_TOKEN = "[TOKO]"


def anonymize(text: str, store_names: tuple[str, ...] = ()) -> str:
    """Ganti PII dan nama toko dengan token placeholder.

    Urutan penting: URL dulu (bisa mengandung @ dan angka), baru sisanya.
    """
    cleaned = _URL_PATTERN.sub(URL_TOKEN, text)
    cleaned = _EMAIL_PATTERN.sub(EMAIL_TOKEN, cleaned)
    cleaned = _PHONE_PATTERN.sub(PHONE_TOKEN, cleaned)
    cleaned = _MENTION_PATTERN.sub(MENTION_TOKEN, cleaned)
    cleaned = _replace_store_names(cleaned, store_names)
    return _WHITESPACE_PATTERN.sub(" ", cleaned).strip()


def _replace_store_names(text: str, store_names: tuple[str, ...]) -> str:
    if not store_names:
        return text
    # Nama terpanjang dulu supaya "Toko Gadget Terpercaya" tidak keburu
    # tergantikan sebagian oleh "Toko Gadget".
    for name in sorted(store_names, key=len, reverse=True):
        if not name.strip():
            continue
        text = re.sub(re.escape(name), STORE_TOKEN, text, flags=re.IGNORECASE)
    return text


def normalize_for_dedup(text: str) -> str:
    """Bentuk kanonik untuk deteksi duplikat exact (bukan near-duplicate)."""
    lowered = text.casefold()
    stripped = re.sub(r"[^\w\s]", "", lowered)
    return _WHITESPACE_PATTERN.sub(" ", stripped).strip()
