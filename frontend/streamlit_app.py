"""Streamlit frontend (Fase 4 of context/07-roadmap-milestone.md)."""
import streamlit as st

st.set_page_config(page_title="Fraud Detector MVP")
st.title("Online Shop Fraud Detector — MVP")
st.caption("Pipeline belum diimplementasikan — lihat context/07-roadmap-milestone.md untuk status.")

query = st.text_input("Cari produk")
if query:
    st.info("Endpoint /search backend belum mengembalikan hasil nyata (lihat roadmap).")
