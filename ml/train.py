"""Fine-tune IndoBERT untuk klasifikasi review bot vs asli.

Contoh:
    python ml/train.py                                   # data/train.jsonl, 3 epoch
    python ml/train.py --epochs 4 --batch-size 16        # kalau pakai GPU
    python ml/train.py --train ml/data/annotations.jsonl # dataset dummy

Validation split diambil dari berkas latih secara stratified dan hanya hidup di
memori — berkas dataset di disk tidak pernah ditimpa, supaya gold set berlabel
tangan (`data/test_real.jsonl`) aman.
"""

from __future__ import annotations

import argparse
import sys
from pathlib import Path

import numpy as np
import torch
from sklearn.metrics import precision_recall_fscore_support
from sklearn.model_selection import train_test_split
from torch.utils.data import Dataset
from transformers import (
    AutoConfig,
    AutoModelForSequenceClassification,
    AutoTokenizer,
    Trainer,
    TrainingArguments,
)

REPO_ROOT = Path(__file__).resolve().parent.parent
# `python ml/train.py` menaruh ml/ di sys.path, bukan root repo - tambahkan sendiri
# supaya paket `ml` bisa diimpor tanpa perlu `python -m ml.train`.
sys.path.insert(0, str(REPO_ROOT))

from ml.dataset_io import (  # noqa: E402
    ID2LABEL,
    LABEL2ID,
    label_distribution,
    load_labeled_records,
)

DEFAULT_TRAIN_PATH = REPO_ROOT / "data" / "train.jsonl"
MODEL_OUTPUT_DIR = REPO_ROOT / "ml" / "model" / "final"
CHECKPOINT_DIR = REPO_ROOT / "ml" / "model" / "checkpoint"

MODEL_NAME = "indobenchmark/indobert-base-p1"
# p99 panjang review di data/train.jsonl = 61 kata, maksimum 92 kata.
# 128 token wordpiece menampung itu tanpa memotong ekor distribusi.
MAX_LENGTH = 128
VAL_FRACTION = 0.15
RANDOM_STATE = 42
LEARNING_RATE = 2e-5


class ReviewDataset(Dataset):
    def __init__(self, encodings, labels):
        self.encodings = encodings
        self.labels = labels

    def __len__(self):
        return len(self.labels)

    def __getitem__(self, idx):
        item = {k: v[idx] for k, v in self.encodings.items()}
        item["labels"] = torch.tensor(self.labels[idx])
        return item


def split_records(
    records: list[dict], val_fraction: float, seed: int
) -> tuple[list[dict], list[dict]]:
    labels = [r["label"] for r in records]
    return train_test_split(
        records,
        test_size=val_fraction,
        random_state=seed,
        stratify=labels,
    )


def build_dataset(records: list[dict], tokenizer, max_length: int) -> ReviewDataset:
    encodings = tokenizer(
        [r["text"] for r in records],
        truncation=True,
        padding="max_length",
        max_length=max_length,
        return_tensors="pt",
    )
    return ReviewDataset(encodings, [r["label"] for r in records])


def compute_metrics(eval_pred):
    logits, labels = eval_pred
    predictions = np.argmax(logits, axis=-1)
    precision, recall, f1, _ = precision_recall_fscore_support(
        labels, predictions, average="macro", zero_division=0
    )
    return {"precision": precision, "recall": recall, "f1": f1}


def parse_args() -> argparse.Namespace:
    parser = argparse.ArgumentParser(description="Fine-tune IndoBERT bot vs asli")
    parser.add_argument("--train", type=Path, default=DEFAULT_TRAIN_PATH)
    parser.add_argument("--output-dir", type=Path, default=MODEL_OUTPUT_DIR)
    parser.add_argument("--model-name", default=MODEL_NAME)
    parser.add_argument("--epochs", type=int, default=3)
    parser.add_argument("--batch-size", type=int, default=16)
    parser.add_argument("--max-length", type=int, default=MAX_LENGTH)
    parser.add_argument("--learning-rate", type=float, default=LEARNING_RATE)
    parser.add_argument("--val-fraction", type=float, default=VAL_FRACTION)
    parser.add_argument("--seed", type=int, default=RANDOM_STATE)
    return parser.parse_args()


def main() -> None:
    args = parse_args()

    records = load_labeled_records(args.train)
    if not records:
        raise SystemExit(f"tidak ada record berlabel di {args.train}")

    train_records, val_records = split_records(records, args.val_fraction, args.seed)
    use_gpu = torch.cuda.is_available()
    device_name = torch.cuda.get_device_name(0) if use_gpu else "CPU"

    print(f"sumber      : {args.train}")
    print(f"distribusi  : {label_distribution(records)} (total {len(records)})")
    print(f"split       : train={len(train_records)} val={len(val_records)}")
    print(f"perangkat   : {device_name}")
    print(f"max_length  : {args.max_length} token")

    tokenizer = AutoTokenizer.from_pretrained(args.model_name)
    config = AutoConfig.from_pretrained(
        args.model_name, num_labels=2, id2label=ID2LABEL, label2id=LABEL2ID
    )
    model = AutoModelForSequenceClassification.from_pretrained(args.model_name, config=config)

    train_dataset = build_dataset(train_records, tokenizer, args.max_length)
    val_dataset = build_dataset(val_records, tokenizer, args.max_length)

    training_args = TrainingArguments(
        output_dir=str(CHECKPOINT_DIR),
        num_train_epochs=args.epochs,
        per_device_train_batch_size=args.batch_size,
        per_device_eval_batch_size=args.batch_size * 2,
        learning_rate=args.learning_rate,
        eval_strategy="epoch",
        save_strategy="epoch",
        load_best_model_at_end=True,
        metric_for_best_model="f1",
        logging_steps=20,
        save_total_limit=1,
        seed=args.seed,
        fp16=use_gpu,
        # Pinned memory butuh RAM non-pageable. Di laptop 16 GB yang dipakai
        # bersamaan aplikasi lain, permintaan itu bisa gagal dan mematikan training
        # di step 0. Dataset ini kecil, jadi mematikannya nyaris tanpa biaya.
        dataloader_pin_memory=False,
        dataloader_num_workers=0,
        report_to=[],
    )

    trainer = Trainer(
        model=model,
        args=training_args,
        train_dataset=train_dataset,
        eval_dataset=val_dataset,
        compute_metrics=compute_metrics,
    )

    trainer.train()
    print(trainer.evaluate())

    args.output_dir.mkdir(parents=True, exist_ok=True)
    trainer.save_model(str(args.output_dir))
    tokenizer.save_pretrained(str(args.output_dir))
    print(f"\nmodel tersimpan di {args.output_dir}")
    print("langkah berikutnya: python ml/evaluate.py")


if __name__ == "__main__":
    main()
