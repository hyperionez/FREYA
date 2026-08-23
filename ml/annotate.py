"""Annotation tool — labeli review satu per satu jadi ground truth manusia.

    streamlit run ml/annotate.py

Baca  : data/to_label.jsonl   (hasil `python -m ml.build_dataset pack`)
Tulis : data/annotations.jsonl

Kedua path bisa dialihkan lewat argumen, supaya batch kalibrasi dilabeli dengan
tool yang sama - bukan disunting tangan - dan hasilnya tidak mencampuri berkas
anotasi utama:

    streamlit run ml/annotate.py --         --queue data/calibration/batch.jsonl         --out annotations/calibration_michael.jsonl

Setiap label langsung ditulis ke disk begitu tombol ditekan, jadi browser
tertutup atau laptop mati tidak menghilangkan pekerjaan. Menjalankan ulang
akan melanjutkan dari review terakhir yang belum dilabeli.

Kriteria label ada di context/11-annotation-rubric.md — baca dulu sebelum mulai.
Aturan section 5 langkah 2 dan section 4 dijaga alat ini lewat `ml/check_rubric.py`:
label bot pada review berkeluhan ditahan untuk dikonfirmasi, dan kalau tetap
dipilih barisnya ditandai `rubrik_override`. Penjagaan ini ada karena tanpa itu
tiga anotator menghasilkan 86 pelanggaran langkah 2 pada 500 review.
"""

from __future__ import annotations

import argparse
import html
import json
import sys
from datetime import datetime
from pathlib import Path
from typing import Any

import streamlit as st

# `streamlit run ml/annotate.py` menaruh ml/ di sys.path[0], bukan akar repo,
# jadi paket `ml` tidak ketemu tanpa baris ini.
REPO_ROOT = Path(__file__).resolve().parent.parent
sys.path.insert(0, str(REPO_ROOT))

from ml.check_rubric import (  # noqa: E402
    PANJANG_PENDEK,
    RAGU_MAKS,
    RAGU_MIN,
    mengandung_keluhan,
)

DEFAULT_QUEUE = Path("data/to_label.jsonl")
DEFAULT_OUT = Path("data/annotations.jsonl")
RUBRIC_PATH = Path("context/11-annotation-rubric.md")


def _resolve_paths() -> tuple[Path, Path]:
    """Ambil path antrean & keluaran dari argumen, jatuh ke default kalau kosong.

    `parse_known_args` dipakai supaya argumen milik Streamlit sendiri tidak
    membuat tool ini berhenti.
    """
    parser = argparse.ArgumentParser(add_help=False)
    parser.add_argument("--queue", type=Path, default=DEFAULT_QUEUE)
    parser.add_argument("--out", type=Path, default=DEFAULT_OUT)
    args, _ = parser.parse_known_args()
    return args.queue, args.out


TO_LABEL_PATH, ANNOTATIONS_PATH = _resolve_paths()

LABEL_ASLI = 0
LABEL_BOT = 1
LABEL_RAGU = "ragu"

# Rentang target "ragu" datang dari ml/check_rubric.py supaya alat pelabelan dan
# linter pascapelabelan tidak pernah memakai ambang yang berbeda.
RAGU_WARN_AFTER = 30  # rasio baru bermakna setelah sampel cukup

REVIEW_BOX_STYLE = """
<style>
.review-box {
    background: rgba(128, 128, 128, 0.12);
    border-left: 4px solid #4c8bf5;
    border-radius: 6px;
    padding: 1.5rem;
    font-size: 1.25rem;
    line-height: 1.6;
    min-height: 7rem;
    white-space: pre-wrap;
}
</style>
"""


# --------------------------------------------------------------------------
# Penjagaan rubrik
# --------------------------------------------------------------------------


def peringatan_rubrik(text: str, label: int | str) -> list[str]:
    """Aturan rubrik yang dilanggar kalau `label` disimpan untuk `text`.

    Hanya label bot yang bisa melanggar: langkah 2 dan 3 section 5 sama-sama
    bermuara ke asli, dan `ragu` selalu aman karena dibuang saat evaluasi.
    """
    if label != LABEL_BOT:
        return []

    pesan = []
    if mengandung_keluhan(text):
        pesan.append(
            "Section 5 langkah 2: ada keluhan atau kritik, jadi urutan keputusan "
            "berhenti di **Asli** - review bayaran hampir tidak pernah mengeluh."
        )
    if len(" ".join(text.split())) < PANJANG_PENDEK:
        pesan.append(
            "Section 4: pendek bukan bukti bot. Dalam teks sependek ini, "
            "minimal 2 sinyal section 3 sulit dibuktikan - pertimbangkan `ragu`."
        )
    return pesan


def perlu_konfirmasi(text: str, label: int | str) -> bool:
    """Apakah label ini ditahan dulu untuk dikonfirmasi anotator."""
    return bool(peringatan_rubrik(text, label))


# --------------------------------------------------------------------------
# Baca / tulis
# --------------------------------------------------------------------------


def _read_jsonl(path: Path) -> list[dict[str, Any]]:
    if not path.exists():
        return []
    lines = path.read_text(encoding="utf-8").splitlines()
    return [json.loads(line) for line in lines if line.strip()]


def _append_annotation(record: dict[str, Any]) -> None:
    """Tambah satu baris lalu tutup file segera — kerja anotasi tidak boleh hilang."""
    ANNOTATIONS_PATH.parent.mkdir(parents=True, exist_ok=True)
    with ANNOTATIONS_PATH.open("a", encoding="utf-8") as handle:
        handle.write(json.dumps(record, ensure_ascii=False) + "\n")


def _drop_last_annotation() -> dict[str, Any] | None:
    records = _read_jsonl(ANNOTATIONS_PATH)
    if not records:
        return None
    with ANNOTATIONS_PATH.open("w", encoding="utf-8") as handle:
        for record in records[:-1]:
            handle.write(json.dumps(record, ensure_ascii=False) + "\n")
    return records[-1]


def _pending(queue: list[dict[str, Any]], done: list[dict[str, Any]]) -> list[dict[str, Any]]:
    labeled_ids = {record["review_id"] for record in done}
    return [row for row in queue if row["review_id"] not in labeled_ids]


def _save(row: dict[str, Any], label: int | str, annotator: str, override: bool = False) -> None:
    record = {
        **row,
        "label": label,
        "annotated_by": annotator,
        "annotated_at": datetime.now().isoformat(timespec="seconds"),
    }
    # Jejak audit: label yang menembus penjagaan rubrik ditandai, sejalan dengan
    # `label_before_correction` di gold set. Yang ditembus harus bisa ditinjau.
    if override:
        record["rubrik_override"] = True
    _append_annotation(record)
    st.rerun()


# --------------------------------------------------------------------------
# Tampilan
# --------------------------------------------------------------------------


def _label_counts(done: list[dict[str, Any]]) -> dict[Any, int]:
    counts: dict[Any, int] = {LABEL_ASLI: 0, LABEL_BOT: 0, LABEL_RAGU: 0}
    for record in done:
        label = record.get("label")
        if label in counts:
            counts[label] += 1
    return counts


def _warn_on_ragu_ratio(total: int, ragu: int) -> None:
    if total < RAGU_WARN_AFTER:
        return
    ratio = ragu / total
    if ratio < RAGU_MIN:
        st.warning(
            f"Ragu hanya {ratio:.0%} — mungkin sedang menebak-nebak "
            f"(wajar {RAGU_MIN:.0%}-{RAGU_MAKS:.0%})."
        )
    elif ratio > RAGU_MAKS:
        st.warning(
            f"Ragu {ratio:.0%} — rubrik mungkin perlu dipertajam "
            f"(wajar {RAGU_MIN:.0%}-{RAGU_MAKS:.0%})."
        )


def _render_sidebar(done: list[dict[str, Any]]) -> None:
    with st.sidebar:
        st.header("Rubrik singkat")
        st.markdown(
            "**Urutan keputusan**\n"
            "1. Rusak / bukan review → `ragu`\n"
            "2. Ada keluhan atau kritik → **Asli**\n"
            "3. Ada detail pengalaman spesifik → **Asli**\n"
            "4. ≥2 sinyal bot → **Bot**\n"
            "5. Sisanya → `ragu`\n\n"
            "**Sinyal bot** — pujian tanpa rujukan produk · struktur template · "
            "ajakan beli · penjejalan kata kunci · formalitas janggal · superlatif bertumpuk\n\n"
            "**BUKAN bukti** — pendek · positif · bintang 5 · typo · bahasa gaul · emoji\n\n"
            "⏱️ Maksimal ~15 detik per review. Lebih lama dari itu → `ragu`."
        )
        st.caption(f"Rubrik lengkap: `{RUBRIC_PATH}`")

        if not done:
            return
        st.divider()
        st.header("Distribusi sementara")
        counts = _label_counts(done)
        st.write(
            f"Asli `0` : **{counts[LABEL_ASLI]}**  \n"
            f"Bot `1`  : **{counts[LABEL_BOT]}**  \n"
            f"Ragu     : **{counts[LABEL_RAGU]}**"
        )
        _warn_on_ragu_ratio(len(done), counts[LABEL_RAGU])


def _render_review(row: dict[str, Any]) -> None:
    st.markdown(REVIEW_BOX_STYLE, unsafe_allow_html=True)
    # escape: teks review bisa memuat karakter markdown yang merusak tampilan
    st.markdown(f'<div class="review-box">{html.escape(row["text"])}</div>', unsafe_allow_html=True)
    st.caption(f"`{row['review_id']}` · {len(row['text'])} karakter")


def _render_finished(done: list[dict[str, Any]]) -> None:
    st.success(f"Selesai — {len(done)} review terlabeli di `{ANNOTATIONS_PATH}`.")
    counts = _label_counts(done)
    usable = counts[LABEL_ASLI] + counts[LABEL_BOT]
    st.write(
        f"Asli **{counts[LABEL_ASLI]}** · Bot **{counts[LABEL_BOT]}** · "
        f"Ragu **{counts[LABEL_RAGU]}** (dibuang saat evaluasi)"
    )
    st.info(f"{usable} baris terpakai sebagai test set berlabel manusia.")
    st.download_button(
        "Unduh annotations.jsonl",
        data=ANNOTATIONS_PATH.read_text(encoding="utf-8"),
        file_name="annotations.jsonl",
        mime="application/x-ndjson",
    )


def _render_konfirmasi(row: dict[str, Any]) -> None:
    """Tahan label bot yang melanggar rubrik sampai anotator menegaskan pilihannya.

    Sengaja bukan blokir keras: leksikon keluhan di `check_rubric` dibuat
    presisi-tinggi dan pasti melewatkan sebagian kasus, jadi penilaian manusia
    harus tetap bisa menang - asal jejaknya tercatat.
    """
    for pesan in peringatan_rubrik(row["text"], LABEL_BOT):
        st.warning(pesan)
    st.caption(
        "Lanjutkan hanya kalau kamu yakin rubriknya keliru di baris ini. "
        "Pilihanmu dicatat sebagai `rubrik_override` supaya bisa ditinjau ulang."
    )

    batal, tetap = st.columns(2)
    if batal.button("↩️ Batal, pilih ulang", type="primary", use_container_width=True):
        st.session_state.pop("konfirmasi", None)
        st.rerun()
    if tetap.button("🤖 Tetap Bot", use_container_width=True):
        st.session_state.pop("konfirmasi", None)
        _save(row, LABEL_BOT, st.session_state["annotator"], override=True)


def _ask_annotator() -> None:
    st.title("Anotasi Review")
    st.write("Masukkan nama anotator — tercatat di tiap baris supaya kesepakatan bisa dihitung.")
    name = st.text_input("Nama anotator", placeholder="misal: michael")
    if st.button("Mulai", type="primary", disabled=not name.strip()):
        st.session_state["annotator"] = name.strip()
        st.rerun()


# --------------------------------------------------------------------------
# Main
# --------------------------------------------------------------------------


def main() -> None:
    st.set_page_config(page_title="Anotasi Review", page_icon="🏷️", layout="centered")

    queue = _read_jsonl(TO_LABEL_PATH)
    if not queue:
        st.error(
            f"`{TO_LABEL_PATH}` kosong atau belum ada. "
            "Jalankan dulu: `python -m ml.build_dataset pack`"
        )
        return

    done = _read_jsonl(ANNOTATIONS_PATH)
    _render_sidebar(done)

    if not st.session_state.get("annotator"):
        _ask_annotator()
        return

    remaining = _pending(queue, done)
    st.progress(len(done) / len(queue), text=f"{len(done)} / {len(queue)} terlabeli")

    if not remaining:
        _render_finished(done)
        return

    row = remaining[0]
    _render_review(row)

    # Petunjuk didahulukan sebelum tombol ditekan: memandu lebih murah daripada
    # menegur, dan langkah 2 adalah aturan yang paling sering terlewat.
    if mengandung_keluhan(row["text"]):
        st.info("Terdeteksi penanda keluhan — section 5 langkah 2 mengarah ke **Asli**.")

    if st.session_state.get("konfirmasi") == row["review_id"]:
        _render_konfirmasi(row)
        return

    asli, bot, ragu = st.columns(3)
    if asli.button("✅ Asli", use_container_width=True):
        _save(row, LABEL_ASLI, st.session_state["annotator"])
    if bot.button("🤖 Bot", use_container_width=True):
        if perlu_konfirmasi(row["text"], LABEL_BOT):
            st.session_state["konfirmasi"] = row["review_id"]
            st.rerun()
        else:
            _save(row, LABEL_BOT, st.session_state["annotator"])
    if ragu.button("🤔 Ragu", use_container_width=True):
        _save(row, LABEL_RAGU, st.session_state["annotator"])

    if done and st.button("↩️ Batalkan label terakhir"):
        undone = _drop_last_annotation()
        if undone:
            st.toast(f"Dibatalkan: {undone['review_id']}")
        st.rerun()


if __name__ == "__main__":
    main()
