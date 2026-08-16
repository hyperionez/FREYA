from ml.anonymize import anonymize, normalize_for_dedup


def test_removes_phone_number():
    result = anonymize("barang oke, hubungi 081234567890 ya")
    assert "081234567890" not in result
    assert "[TELEPON]" in result


def test_removes_phone_with_country_code():
    result = anonymize("wa +62 812-3456-7890 untuk grosir")
    assert "812" not in result
    assert "[TELEPON]" in result


def test_removes_email_and_url():
    result = anonymize("cek https://tokopedia.com/abc atau email admin@toko.co.id")
    assert "[URL]" in result
    assert "[EMAIL]" in result
    assert "tokopedia.com" not in result


def test_removes_mention():
    assert anonymize("thanks @seller_jaya") == "thanks [USER]"


def test_replaces_store_name_case_insensitively():
    result = anonymize("beli di Toko Gadget Terpercaya", store_names=("toko gadget terpercaya",))
    assert result == "beli di [TOKO]"


def test_prefers_longest_store_name():
    result = anonymize(
        "beli di Toko Gadget Terpercaya",
        store_names=("Toko Gadget", "Toko Gadget Terpercaya"),
    )
    assert result == "beli di [TOKO]"


def test_collapses_whitespace():
    assert anonymize("  barang    bagus \n sekali ") == "barang bagus sekali"


def test_keeps_ordinary_text_intact():
    text = "pengiriman cepat, packing rapi, sesuai deskripsi"
    assert anonymize(text) == text


def test_normalize_for_dedup_ignores_case_and_punctuation():
    assert normalize_for_dedup("Barang BAGUS!!!") == normalize_for_dedup("barang bagus")


def test_normalize_for_dedup_distinguishes_different_text():
    assert normalize_for_dedup("barang bagus") != normalize_for_dedup("barang jelek")
