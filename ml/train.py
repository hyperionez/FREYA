from __future__ import annotations

import argparse
import json
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
    
MODEL_NAME = "indobenchmark/indobert-base-p1"
DATA_DIR = Path(__file__).resolve().parent / "data"
ANNOTATIONS_PATH = DATA_DIR / "annotations.jsonl"
TRAIN_SPLIT_PATH = DATA_DIR / "train.jsonl"
VAL_SPLIT_PATH = DATA_DIR / "val.jsonl"
MODEL_OUTPUT_DIR = Path(__file__).resolve().parent / "model" / "final"
CHECKPOINT_DIR = Path(__file__).resolve().parent / "model" / "checkpoint"

LABEL2ID = {"asli": 0, "bot": 1}
ID2LABEL = {v: k for k, v in LABEL2ID.items()}
VAL_FRACTION = 0.15
RANDOM_STATE = 42
MAX_LENGTH = 64


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


def load_records(path: Path) -> list[dict]:
    records = []
    with path.open(encoding="utf-8") as f:
        for line in f:
            line = line.strip()
            if not line:
                continue
            record = json.loads(line)
            if record["label"] in LABEL2ID:
                records.append(record)
    return records


def split_dataset() -> tuple[list[dict], list[dict]]:
    records = load_records(ANNOTATIONS_PATH)
    labels = [r["label"] for r in records]
    train_records, val_records = train_test_split(
        records,
        test_size=VAL_FRACTION,
        random_state=RANDOM_STATE,
        stratify=labels,
    )
    DATA_DIR.mkdir(parents=True, exist_ok=True)
    with TRAIN_SPLIT_PATH.open("w", encoding="utf-8") as f:
        for r in train_records:
            f.write(json.dumps(r, ensure_ascii=False) + "\n")
    with VAL_SPLIT_PATH.open("w", encoding="utf-8") as f:
        for r in val_records:
            f.write(json.dumps(r, ensure_ascii=False) + "\n")
    return train_records, val_records


def build_dataset(records: list[dict], tokenizer) -> ReviewDataset:
    texts = [r["text"] for r in records]
    labels = [LABEL2ID[r["label"]] for r in records]
    encodings = tokenizer(
        texts,
        truncation=True,
        padding="max_length",
        max_length=MAX_LENGTH,
        return_tensors="pt",
    )
    return ReviewDataset(encodings, labels)


def compute_metrics(eval_pred):
    logits, labels = eval_pred
    predictions = np.argmax(logits, axis=-1)
    precision, recall, f1, _ = precision_recall_fscore_support(
        labels, predictions, average="macro", zero_division=0
    )
    return {"precision": precision, "recall": recall, "f1": f1}


def main() -> None:
    parser = argparse.ArgumentParser()
    parser.add_argument("--epochs", type=int, default=3)
    parser.add_argument("--batch-size", type=int, default=8)
    args = parser.parse_args()

    train_records, val_records = split_dataset()
    print(f"train={len(train_records)} val={len(val_records)}")

    tokenizer = AutoTokenizer.from_pretrained(MODEL_NAME)
    config = AutoConfig.from_pretrained(
        MODEL_NAME, num_labels=2, id2label=ID2LABEL, label2id=LABEL2ID
    )
    model = AutoModelForSequenceClassification.from_pretrained(MODEL_NAME, config=config)

    train_dataset = build_dataset(train_records, tokenizer)
    val_dataset = build_dataset(val_records, tokenizer)

    training_args = TrainingArguments(
        output_dir=str(CHECKPOINT_DIR),
        num_train_epochs=args.epochs,
        per_device_train_batch_size=args.batch_size,
        per_device_eval_batch_size=args.batch_size * 2,
        eval_strategy="epoch",
        save_strategy="epoch",
        load_best_model_at_end=True,
        metric_for_best_model="f1",
        logging_steps=20,
        save_total_limit=1,
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
    metrics = trainer.evaluate()
    print(metrics)

    MODEL_OUTPUT_DIR.mkdir(parents=True, exist_ok=True)
    trainer.save_model(str(MODEL_OUTPUT_DIR))
    tokenizer.save_pretrained(str(MODEL_OUTPUT_DIR))


if __name__ == "__main__":
    main()
