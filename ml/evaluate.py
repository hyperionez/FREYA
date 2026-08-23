"""Evaluasi model fine-tuned terhadap baseline heuristik.

Dijalankan setelah `ml/train.py`:

    python ml/evaluate.py                             # kedua test set
    python ml/evaluate.py --test data/test_real.jsonl # satu test set saja

Dua test set dievaluasi karena mengukur dua hal berbeda (lihat `data/README.md`):

- `test_synthetic.jsonl` — apakah model bisa memisahkan review asli dari review
  buatan LLM. Soal mudah, angkanya akan tinggi.
- `test_real.jsonl` — 250 review berlabel tangan. Apakah kemampuan itu menyeberang
  ke data dunia nyata. **Inilah angka penentu GO/NO-GO**, bukan yang sintetik.

Selisih antara keduanya adalah temuan yang wajib dilaporkan apa adanya di proposal.
"""

from __future__ import annotations

import argparse
import sys
from pathlib import Path

# sklearn WAJIB diimpor sebelum torch. Urutan sebaliknya mematikan proses dengan
# heap corruption (0xC0000374) saat sklearn menarik pandas -> zoneinfo. Bukan
# urutan isort baku, jadi jangan dirapikan otomatis.
from sklearn.metrics import (
    classification_report,
    confusion_matrix,
    precision_recall_fscore_support,
)

import torch
from transformers import AutoModelForSequenceClassification, AutoTokenizer

REPO_ROOT = Path(__file__).resolve().parent.parent
sys.path.insert(0, str(REPO_ROOT))

from app.embedding_model import encode  # noqa: E402
from ml.dataset_io import (  # noqa: E402
    ID2LABEL,
    LABEL2ID,
    label_distribution,
    load_labeled_records,
)

DEFAULT_TEST_PATHS = (
    REPO_ROOT / "data" / "test_real.jsonl",
    REPO_ROOT / "data" / "test_synthetic.jsonl",
)
MODEL_DIR = REPO_ROOT / "ml" / "model" / "final"
MAX_LENGTH = 128
NEAR_DUPLICATE_THRESHOLD = 0.9


def run_finetuned_model(records: list[dict], model_dir: Path, max_length: int) -> list[int]:
    tokenizer = AutoTokenizer.from_pretrained(str(model_dir))
    model = AutoModelForSequenceClassification.from_pretrained(str(model_dir))
    model.eval()

    encodings = tokenizer(
        [r["text"] for r in records],
        truncation=True,
        padding="max_length",
        max_length=max_length,
        return_tensors="pt",
    )
    with torch.no_grad():
        logits = model(**encodings).logits
    return torch.argmax(logits, dim=-1).tolist()


def run_heuristic_baseline(records: list[dict]) -> list[int]:
    """Perkiraan Lapis 1 di granularitas per-review: near-duplicate ditandai bot."""
    embeddings = encode([r["text"] for r in records])
    similarity = embeddings @ embeddings.T
    predictions = []
    for i in range(len(records)):
        row = similarity[i].copy()
        row[i] = -1.0
        is_near_duplicate = bool((row >= NEAR_DUPLICATE_THRESHOLD).any())
        predictions.append(LABEL2ID["bot"] if is_near_duplicate else LABEL2ID["asli"])
    return predictions


def macro_f1(y_true: list[int], y_pred: list[int]) -> float:
    _, _, f1, _ = precision_recall_fscore_support(
        y_true, y_pred, average="macro", zero_division=0
    )
    return float(f1)


def bot_recall(y_true: list[int], y_pred: list[int]) -> float:
    """Porsi review bot yang benar-benar tertangkap - angka gunanya produk ini."""
    total_bot = sum(1 for t in y_true if t == LABEL2ID["bot"])
    if total_bot == 0:
        return float("nan")
    caught = sum(1 for t, p in zip(y_true, y_pred) if t == LABEL2ID["bot"] and p == t)
    return caught / total_bot


def majority_class_f1(y_true: list[int]) -> float:
    """Macro F1 dari penebak bodoh yang selalu menjawab kelas terbanyak.

    Model apa pun yang tidak melewati angka ini tidak belajar apa-apa yang
    berguna, seberapa pun tipis selisihnya terhadap baseline lain.
    """
    majority = max(set(y_true), key=y_true.count)
    return macro_f1(y_true, [majority] * len(y_true))


def report(name: str, y_true: list[int], y_pred: list[int]) -> float:
    print(f"\n--- {name} ---")
    labels_present = sorted(set(y_true) | set(y_pred))
    print(
        classification_report(
            y_true,
            y_pred,
            labels=labels_present,
            target_names=[ID2LABEL[i] for i in labels_present],
            zero_division=0,
        )
    )
    print("Confusion matrix (baris=label asli, kolom=prediksi, urutan=[asli,bot]):")
    print(confusion_matrix(y_true, y_pred, labels=[0, 1]))
    return macro_f1(y_true, y_pred)


def evaluate_test_set(path: Path, model_dir: Path, max_length: int) -> dict[str, float | None]:
    records = load_labeled_records(path)
    y_true = [r["label"] for r in records]

    print(f"\n{'=' * 70}")
    print(f"TEST SET: {path.name}  ({len(records)} record, {label_distribution(records)})")
    print("=" * 70)

    model_f1 = None
    model_bot_recall = None
    if model_dir.exists():
        y_pred = run_finetuned_model(records, model_dir, max_length)
        model_f1 = report("IndoBERT fine-tuned", y_true, y_pred)
        model_bot_recall = bot_recall(y_true, y_pred)
    else:
        print(f"\nModel belum ada di {model_dir} - jalankan `python ml/train.py` dulu.")

    y_pred_heuristic = run_heuristic_baseline(records)
    heuristic_f1 = report("Baseline heuristik (near-duplicate)", y_true, y_pred_heuristic)

    return {
        "model": model_f1,
        "heuristic": heuristic_f1,
        "majority": majority_class_f1(y_true),
        "model_bot_recall": model_bot_recall,
        "heuristic_bot_recall": bot_recall(y_true, y_pred_heuristic),
    }


def print_verdict(results: dict[str, dict[str, float | None]]) -> None:
    print(f"\n{'=' * 70}")
    print("RINGKASAN - macro F1 (makin tinggi makin baik)")
    print("=" * 70)
    print(f"{'test set':<26}{'fine-tuned':>12}{'heuristik':>12}{'kelas mayoritas':>17}")
    for name, scores in results.items():
        model = scores["model"]
        model_txt = f"{model:>12.3f}" if model is not None else f"{'(belum ada)':>12}"
        print(f"{name:<26}{model_txt}{scores['heuristic']:>12.3f}{scores['majority']:>17.3f}")

    print(f"\n{'test set':<26}{'recall bot model':>18}{'recall bot heuristik':>22}")
    for name, scores in results.items():
        model_rec = scores["model_bot_recall"]
        model_txt = f"{model_rec:>18.3f}" if model_rec is not None else f"{'-':>18}"
        print(f"{name:<26}{model_txt}{scores['heuristic_bot_recall']:>22.3f}")

    real = results.get("test_real.jsonl")
    if not real or real["model"] is None:
        return

    print("\nGerbang GO/NO-GO (master plan Fase 2), dinilai dari test_real.jsonl:")
    beats_heuristic = real["model"] > real["heuristic"]
    beats_majority = real["model"] > real["majority"]

    if beats_heuristic and beats_majority:
        print("  GO - model melewati heuristik DAN penebak kelas mayoritas.")
        print(f"  Recall bot {real['model_bot_recall']:.1%} - pastikan ini layak secara produk")
        print("  sebelum dipasang lewat run_finetuned_classifier() di app/review_analysis/.")
        return

    print("  NO-GO.")
    if not beats_majority:
        print(
            f"  Macro F1 model ({real['model']:.3f}) tidak melewati penebak kelas "
            f"mayoritas ({real['majority']:.3f})."
        )
        print("  Artinya model belum belajar apa pun yang berguna di data nyata,")
        print("  walau angkanya kelihatan lebih tinggi dari heuristik.")
    if not beats_heuristic:
        print(f"  Model ({real['model']:.3f}) tidak melewati heuristik ({real['heuristic']:.3f}).")
    print(f"  Recall bot model hanya {real['model_bot_recall']:.1%} dari review bot yang ada.")
    print("  Periksa dulu kualitas label gold set dan kesenjangan distribusi latih-vs-nyata")
    print("  sebelum memutuskan pakai heuristik (master plan section 6) atau Plan B RAG (section 8).")


def parse_args() -> argparse.Namespace:
    parser = argparse.ArgumentParser(description="Evaluasi model vs baseline heuristik")
    parser.add_argument("--test", type=Path, nargs="*", default=list(DEFAULT_TEST_PATHS))
    parser.add_argument("--model-dir", type=Path, default=MODEL_DIR)
    parser.add_argument("--max-length", type=int, default=MAX_LENGTH)
    return parser.parse_args()


def main() -> None:
    args = parse_args()
    results = {
        Path(path).name: evaluate_test_set(Path(path), args.model_dir, args.max_length)
        for path in args.test
    }
    print_verdict(results)
    print(
        "\nCatatan: baseline heuristik di sini memperkirakan Lapis 1 di granularitas "
        "per-review (cek near-duplicate antar review). Tidak identik dengan "
        "get_review_authenticity_score() yang bekerja per-toko dan juga memakai "
        "clustering waktu posting."
    )


if __name__ == "__main__":
    main()
