from __future__ import annotations

import json
import sys
from pathlib import Path

import numpy as np
import torch
from sklearn.metrics import classification_report, confusion_matrix
from transformers import AutoModelForSequenceClassification, AutoTokenizer

ML_DIR = Path(__file__).resolve().parent
sys.path.insert(0, str(ML_DIR.parent))

from app.embedding_model import encode  # noqa: E402

VAL_SPLIT_PATH = ML_DIR / "data" / "val.jsonl"
MODEL_DIR = ML_DIR / "model" / "final"
LABEL2ID = {"asli": 0, "bot": 1}
ID2LABEL = {v: k for k, v in LABEL2ID.items()}
MAX_LENGTH = 64
NEAR_DUPLICATE_THRESHOLD = 0.9


def load_val_records() -> list[dict]:
    records = []
    with VAL_SPLIT_PATH.open(encoding="utf-8") as f:
        for line in f:
            line = line.strip()
            if line:
                records.append(json.loads(line))
    return records


def run_finetuned_model(records: list[dict]) -> list[int]:
    tokenizer = AutoTokenizer.from_pretrained(str(MODEL_DIR))
    model = AutoModelForSequenceClassification.from_pretrained(str(MODEL_DIR))
    model.eval()

    texts = [r["text"] for r in records]
    encodings = tokenizer(
        texts, truncation=True, padding="max_length", max_length=MAX_LENGTH, return_tensors="pt"
    )
    with torch.no_grad():
        logits = model(**encodings).logits
    return torch.argmax(logits, dim=-1).tolist()


def run_heuristic_baseline(records: list[dict]) -> list[int]:
    texts = [r["text"] for r in records]
    embeddings = encode(texts)
    similarity = embeddings @ embeddings.T
    predictions = []
    for i in range(len(texts)):
        row = similarity[i].copy()
        row[i] = -1.0
        is_near_duplicate = bool((row >= NEAR_DUPLICATE_THRESHOLD).any())
        predictions.append(LABEL2ID["bot"] if is_near_duplicate else LABEL2ID["asli"])
    return predictions


def report(name: str, y_true: list[int], y_pred: list[int]) -> None:
    print(f"\n=== {name} ===")
    print(classification_report(y_true, y_pred, target_names=["asli", "bot"], zero_division=0))
    print("Confusion matrix (rows=true, cols=pred, order=[asli,bot]):")
    print(confusion_matrix(y_true, y_pred, labels=[0, 1]))


def main() -> None:
    records = load_val_records()
    y_true = [LABEL2ID[r["label"]] for r in records]

    if MODEL_DIR.exists():
        y_pred_model = run_finetuned_model(records)
        report("IndoBERT fine-tuned", y_true, y_pred_model)
    else:
        print(f"No fine-tuned model found at {MODEL_DIR}, skipping. Run ml/train.py first.")

    y_pred_heuristic = run_heuristic_baseline(records)
    report("Heuristic baseline (near-duplicate within val set)", y_true, y_pred_heuristic)
    print(
        "\nNote: this heuristic baseline approximates Lapis 1 at single-review granularity "
        "(cross-review near-duplicate check). It is not identical to the store-level "
        "get_review_authenticity_score() function, which also uses posting-time clustering "
        "across a single store's review list."
    )


if __name__ == "__main__":
    main()
