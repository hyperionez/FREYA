import os

import requests
import streamlit as st

API_URL = os.getenv("API_URL", "http://127.0.0.1:8000")

LABEL_DISPLAY = {
    "Aman": st.success,
    "Waspada": st.warning,
    "Berbahaya": st.error,
}

st.set_page_config(page_title="Fraud Detector MVP")
st.title("Online Shop Fraud Detector MVP")

query = st.text_input("Cari produk")

if query:
    with st.spinner("Mencari dan menganalisis toko..."):
        try:
            response = requests.get(f"{API_URL}/search", params={"query": query}, timeout=300)
            response.raise_for_status()
        except requests.RequestException as error:
            response = None
            st.error(f"Gagal menghubungi API: {error}")

    if response is not None:
        stores = response.json().get("stores", [])
        if not stores:
            st.info("Tidak ada toko ditemukan untuk query ini.")
        for store in stores:
            assessment = store["assessment"]
            scoring = store["scoring"]
            features = store["features"]
            label = assessment["label"]

            with st.container(border=True):
                st.subheader(store["store_name"])

                display = LABEL_DISPLAY.get(label, st.info)
                display(f"{label} — skor {scoring['score']}/100")

                if features.get("price") is not None:
                    st.write(f"Harga: Rp{features['price']:,}")

                st.markdown("\n".join(f"- {reason}" for reason in assessment["reasons"]))
                st.markdown(f"[Kunjungi toko]({store['store_url']})")
