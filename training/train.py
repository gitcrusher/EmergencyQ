# training/train.py
# Fine-tune DistilBERT for 5-class emergency classification
# Fixes: class imbalance, keyword overfitting, label smoothing
# Adds:  MLflow experiment tracking, synonym augmentation
#
# Usage (run from ANY directory):
#   python training/train.py
#   cd training && python train.py

import os
import sys
import random
import joblib
import threading
import concurrent.futures
from functools import lru_cache
from pathlib import Path

# Always resolve paths relative to PROJECT ROOT (one level up from this file)
ROOT = Path(__file__).resolve().parent.parent
os.chdir(ROOT)
print(f"Working directory set to: {ROOT}")

import mlflow
import mlflow.pytorch
import pandas as pd
import numpy as np
import torch
import torch.nn as nn
import nltk

from transformers import (
    DistilBertTokenizer,
    DistilBertForSequenceClassification,
    Trainer,
    TrainingArguments,
    EarlyStoppingCallback,
)
from datasets import Dataset
from sklearn.metrics import accuracy_score, f1_score
from nltk.corpus import wordnet

# ─────────────────────────────────────────────────────────────────────────────
# CONFIG
# ─────────────────────────────────────────────────────────────────────────────

MODEL_NAME  = "distilbert-base-uncased"
NUM_LABELS  = 5
OUTPUT_DIR  = "backend/app/model/trained_model"
ENCODER_PKL = "backend/app/model/label_encoder.pkl"
TRAIN_CSV   = "dataset/processed/train.csv"
VAL_CSV     = "dataset/processed/val.csv"
MAX_LENGTH  = 128
BATCH_TRAIN = 16
BATCH_EVAL  = 32
EPOCHS      = 5
LR          = 2e-5
SEED        = 42
MLFLOW_EXP  = "EmergencyQ-DistilBERT"

# Augmentation: probability of replacing a word with a synonym per token
AUG_PROB    = 0.15
AUG_FRAC    = 0.4   # fraction of training examples to augment

# ─────────────────────────────────────────────────────────────────────────────
# SETUP
# ─────────────────────────────────────────────────────────────────────────────

device = torch.device("cuda" if torch.cuda.is_available() else "cpu")

print("=" * 70)
print("  Emergency Complaint Analyzer — DistilBERT Training (v2) ")
print("=" * 70)
print(f"\n PyTorch      : {torch.__version__}")

if torch.cuda.is_available():
    torch.cuda.empty_cache()
    print(f" GPU          : {torch.cuda.get_device_name(0)}")
    gpu_mem = torch.cuda.get_device_properties(0).total_memory / 1024**3
    print(f" GPU Memory   : {gpu_mem:.2f} GB")
else:
    print("  CPU mode (no CUDA)")

print(f" Device       : {device}")

torch.manual_seed(SEED)
if torch.cuda.is_available():
    torch.cuda.manual_seed_all(SEED)

os.makedirs(OUTPUT_DIR, exist_ok=True)

# ─────────────────────────────────────────────────────────────────────────────
# DOWNLOAD NLTK WORDNET (for synonym augmentation)
# ─────────────────────────────────────────────────────────────────────────────

print("\n Ensuring NLTK WordNet data...")
nltk.download("wordnet", quiet=True)
nltk.download("omw-1.4", quiet=True)

# ─────────────────────────────────────────────────────────────────────────────
# SYNONYM AUGMENTATION
# Replaces random words with synonyms so model learns MEANING not exact words.
# e.g. "trapped" → "stuck", "snared", "confined" — all treated equally
# This directly fixes: "trapped" = high confidence, "stucked" = medium
# ─────────────────────────────────────────────────────────────────────────────

wn_lock = threading.Lock()

@lru_cache(maxsize=10000)
def get_synonyms(word: str) -> tuple:
    """
    Return synonyms for a word from WordNet.
    lru_cache: same word is looked up only ONCE — results cached in memory.
    Returns tuple (hashable) so lru_cache works.
    NLTK WordNet is not thread-safe, so we use a lock for cache misses.
    """
    synonyms = set()
    with wn_lock:
        for syn in wordnet.synsets(word):
            for lemma in syn.lemmas():
                name = lemma.name().replace("_", " ")
                if name.lower() != word.lower():
                    synonyms.add(name)
    return tuple(synonyms)


def synonym_augment(text: str, aug_prob: float = AUG_PROB) -> str:
    """
    Randomly replace words with WordNet synonyms.
    aug_prob = probability of replacing each individual word.
    """
    words = text.split()
    new_words = []
    for word in words:
        if random.random() < aug_prob:
            syns = get_synonyms(word)   # cached — no repeated WordNet disk reads
            if syns:
                new_words.append(random.choice(syns))
            else:
                new_words.append(word)
        else:
            new_words.append(word)
    return " ".join(new_words)


def _augment_one(args) -> dict:
    """Worker function for multiprocessing — augments a single row."""
    text, label = args
    return {"text": synonym_augment(str(text)), "label": label}


def augment_dataframe(df: pd.DataFrame, frac: float = AUG_FRAC) -> pd.DataFrame:
    """
    Augment training data using parallel multiprocessing.
    - iterrows() REMOVED — was the main bottleneck
    - Uses all available CPU cores via multiprocessing.Pool
    - lru_cache on get_synonyms avoids repeated WordNet disk reads
    - Minority classes augmented more aggressively to fix class imbalance
    """
    n_cores = min(32, os.cpu_count() or 4)
    print(f"\n Augmenting {frac*100:.0f}% of training data with synonym replacement...")
    print(f"   Using {n_cores} threads in parallel")

    label_counts = df["label"].value_counts()
    max_count    = label_counts.max()

    all_args = []   # collect (text, label) pairs first, then parallel process

    for label in df["label"].unique():
        class_df    = df[df["label"] == label]
        class_count = len(class_df)

        # Minority classes (Accident=1050) get 25x more augmentation than majority (Other=26K)
        ratio      = max_count / class_count
        class_frac = min(frac * ratio, 1.5)   # cap at 150% of class size

        n_aug  = int(len(class_df) * class_frac)
        sampled = class_df.sample(
            n=min(n_aug, len(class_df)), random_state=SEED, replace=True
        )

        # collect as list of tuples — much faster than iterrows()
        all_args.extend(
            zip(sampled["text"].tolist(), sampled["label"].tolist())
        )

    print(f"   Augmenting {len(all_args):,} rows in parallel...")

    # Parallel augmentation using threads (bypasses Windows multiprocessing spawn bug)
    augmented_rows = []
    with concurrent.futures.ThreadPoolExecutor(max_workers=n_cores) as executor:
        augmented_rows = list(executor.map(_augment_one, all_args))

    aug_df   = pd.DataFrame(augmented_rows)
    combined = pd.concat([df, aug_df], ignore_index=True).sample(frac=1, random_state=SEED)

    print(f"   Original : {len(df):,} rows")
    print(f"   Augmented: {len(aug_df):,} rows added")
    print(f"   Total    : {len(combined):,} rows")
    return combined

# ─────────────────────────────────────────────────────────────────────────────
# LOAD DATA
# ─────────────────────────────────────────────────────────────────────────────

print("\n Loading datasets...")
train_df = pd.read_csv(TRAIN_CSV)
val_df   = pd.read_csv(VAL_CSV)

print(f" Train rows : {len(train_df):,}")
print(f" Val rows   : {len(val_df):,}")
print("\n Class distribution (train):")
print(train_df["label"].value_counts().to_string())

# ─────────────────────────────────────────────────────────────────────────────
# CLASS WEIGHTS (Fix imbalance — model was cheating on 'Other' class)
# Formula: weight_c = total_samples / (n_classes * count_c)
# Rare classes like Accident (1050) get high weight, Other (26851) gets low weight
# ─────────────────────────────────────────────────────────────────────────────

print("\n  Computing class weights to fix imbalance...")
le = joblib.load(ENCODER_PKL)

label_counts = train_df["label"].value_counts()
total        = len(train_df)
n_classes    = len(le.classes_)

class_weights = torch.zeros(n_classes, dtype=torch.float)
for i, cls in enumerate(le.classes_):
    count = label_counts.get(cls, 1)
    weight = total / (n_classes * count)
    class_weights[i] = weight
    print(f"   {cls:<12}: count={count:>6,}  weight={weight:.3f}")

class_weights = class_weights.to(device)

# ─────────────────────────────────────────────────────────────────────────────
# APPLY AUGMENTATION
# ─────────────────────────────────────────────────────────────────────────────

train_df = augment_dataframe(train_df)

# ─────────────────────────────────────────────────────────────────────────────
# LABEL ENCODING
# ─────────────────────────────────────────────────────────────────────────────

print("\n🏷  Encoding labels...")
train_df["label"] = le.transform(train_df["label"])
val_df["label"]   = le.transform(val_df["label"])
print(f" Classes : {le.classes_.tolist()}")

# ─────────────────────────────────────────────────────────────────────────────
# TOKENIZER
# ─────────────────────────────────────────────────────────────────────────────

print("\n Loading tokenizer...")
tokenizer = DistilBertTokenizer.from_pretrained(MODEL_NAME)

def tokenize(batch):
    return tokenizer(
        batch["text"],
        truncation=True,
        padding="max_length",
        max_length=MAX_LENGTH,
    )

# ─────────────────────────────────────────────────────────────────────────────
# HUGGINGFACE DATASET
# ─────────────────────────────────────────────────────────────────────────────

print("\n⚙  Tokenizing datasets...")
train_ds = Dataset.from_pandas(train_df[["text", "label"]])
val_ds   = Dataset.from_pandas(val_df[["text", "label"]])

train_ds = train_ds.map(tokenize, batched=True)
val_ds   = val_ds.map(tokenize, batched=True)

train_ds = train_ds.rename_column("label", "labels")
val_ds   = val_ds.rename_column("label", "labels")

cols = ["input_ids", "attention_mask", "labels"]
train_ds.set_format(type="torch", columns=cols)
val_ds.set_format(type="torch", columns=cols)

# ─────────────────────────────────────────────────────────────────────────────
# MODEL WITH LABEL SMOOTHING LOSS
# Label smoothing: instead of learning P(correct)=1.0, learn P(correct)=0.9
# This prevents overconfident predictions — fixes "trapped"=99% "stucked"=55%
# ─────────────────────────────────────────────────────────────────────────────

print("\n Loading DistilBERT model...")
model = DistilBertForSequenceClassification.from_pretrained(
    MODEL_NAME,
    num_labels=NUM_LABELS,
    dropout=0.2,            # DistilBERT uses 'dropout' (not 'hidden_dropout_prob' which is BERT-only)
    attention_dropout=0.2,  # default=0.1, higher = more regularization against overfitting
)
model.to(device)
print(f" Model parameters : {model.num_parameters():,}")


class WeightedLabelSmoothingTrainer(Trainer):
    """
    Custom Trainer that combines:
    1. Class weights   → forces model to pay attention to rare classes (Accident, Fire)
    2. Label smoothing → prevents overconfident predictions (fixes keyword memorization)
    """

    def __init__(self, *args, class_weights=None, label_smoothing=0.1, **kwargs):
        super().__init__(*args, **kwargs)
        self.class_weights   = class_weights
        self.label_smoothing = label_smoothing

    def compute_loss(self, model, inputs, return_outputs=False, **kwargs):
        labels = inputs.pop("labels")
        outputs = model(**inputs)
        logits  = outputs.logits

        loss_fn = nn.CrossEntropyLoss(
            weight=self.class_weights,
            label_smoothing=self.label_smoothing,
        )
        loss = loss_fn(logits, labels)

        return (loss, outputs) if return_outputs else loss

# ─────────────────────────────────────────────────────────────────────────────
# METRICS
# ─────────────────────────────────────────────────────────────────────────────

def compute_metrics(eval_pred):
    logits, labels = eval_pred
    preds    = np.argmax(logits, axis=-1)
    accuracy = accuracy_score(labels, preds)
    macro_f1 = f1_score(labels, preds, average="macro")
    weighted_f1 = f1_score(labels, preds, average="weighted")
    return {
        "accuracy":    accuracy,
        "macro_f1":    macro_f1,
        "weighted_f1": weighted_f1,
    }

# ─────────────────────────────────────────────────────────────────────────────
# TRAINING ARGUMENTS
# ─────────────────────────────────────────────────────────────────────────────

print("\n Configuring training arguments...")
args = TrainingArguments(
    output_dir=OUTPUT_DIR,

    # Training
    num_train_epochs=EPOCHS,
    per_device_train_batch_size=BATCH_TRAIN,
    per_device_eval_batch_size=BATCH_EVAL,
    gradient_accumulation_steps=2,

    # Optimization — stronger regularization vs v1
    learning_rate=LR,
    warmup_ratio=0.1,
    weight_decay=0.05,          # increased from 0.01 → reduces overfitting
    optim="adamw_torch",

    # Evaluation
    eval_strategy="epoch",
    save_strategy="epoch",
    load_best_model_at_end=True,
    save_total_limit=1,         # Only keep the best checkpoint to save disk space
    metric_for_best_model="macro_f1",
    greater_is_better=True,

    # Logging
    logging_steps=100,

    # Reproducibility
    seed=SEED,

    # Disable HF reporting (we use MLflow directly)
    report_to="none",

    # GPU
    fp16=torch.cuda.is_available(),
    dataloader_pin_memory=True,
)

# ─────────────────────────────────────────────────────────────────────────────
# TRAINER
# ─────────────────────────────────────────────────────────────────────────────

print("\n Building Trainer...")
trainer = WeightedLabelSmoothingTrainer(
    model=model,
    args=args,
    train_dataset=train_ds,
    eval_dataset=val_ds,
    compute_metrics=compute_metrics,
    class_weights=class_weights,
    label_smoothing=0.1,
    callbacks=[EarlyStoppingCallback(early_stopping_patience=2)],
)

# ─────────────────────────────────────────────────────────────────────────────
# MLFLOW TRACKING
# ─────────────────────────────────────────────────────────────────────────────

mlflow.set_experiment(MLFLOW_EXP)

print("\n Starting MLflow run...")
with mlflow.start_run(run_name="distilbert-v2-weighted-smoothing") as run:

    # Log all hyperparameters
    mlflow.log_params({
        "model":              MODEL_NAME,
        "num_labels":         NUM_LABELS,
        "epochs":             EPOCHS,
        "learning_rate":      LR,
        "batch_size_train":   BATCH_TRAIN,
        "max_length":         MAX_LENGTH,
        "weight_decay":       0.05,
        "label_smoothing":    0.1,
        "dropout":            0.2,
        "aug_prob":           AUG_PROB,
        "aug_frac":           AUG_FRAC,
        "seed":               SEED,
    })

    # Log class weights
    for i, cls in enumerate(le.classes_):
        mlflow.log_param(f"weight_{cls}", round(class_weights[i].item(), 3))

    # ── TRAINING ──────────────────────────────────────────────────────────────
    print("\n\ Starting Training...\n")
    train_result = trainer.train()

    # Log training metrics
    mlflow.log_metrics({
        "train_loss":          train_result.training_loss,
        "train_runtime_sec":   train_result.metrics.get("train_runtime", 0),
        "train_samples_per_sec": train_result.metrics.get("train_samples_per_second", 0),
    })

    # ── SAVE MODEL ────────────────────────────────────────────────────────────
    print("\n Saving model...")
    trainer.save_model(OUTPUT_DIR)
    tokenizer.save_pretrained(OUTPUT_DIR)
    print(f" Model saved to : {OUTPUT_DIR}")

    # ── QUANTIZE MODEL (For AWS Deployment) ───────────────────────────────────
    print("\n Shrinking model size for AWS (INT8 Dynamic Quantization)...")
    try:
        import torch.quantization
        # Must be on CPU for dynamic quantization
        model.to("cpu")
        quantized_model = torch.quantization.quantize_dynamic(
            model, {torch.nn.Linear}, dtype=torch.qint8
        )
        q_dir = os.path.join(OUTPUT_DIR, "quantized")
        os.makedirs(q_dir, exist_ok=True)
        # Save PyTorch quantized weights
        torch.save(quantized_model.state_dict(), os.path.join(q_dir, "model_quantized.pt"))
        tokenizer.save_pretrained(q_dir)
        print(f" Quantized AWS-ready model saved to : {q_dir} (~67MB)")
        
        # Restore model to original device so final evaluation doesn't crash
        model.to(device)
    except Exception as e:
        print(f" Warning: Quantization skipped due to error: {e}")

    # ── FINAL EVALUATION ──────────────────────────────────────────────────────
    print("\n Running final evaluation...\n")
    results = trainer.evaluate()

    # Log evaluation metrics to MLflow
    eval_metrics = {
        "val_accuracy":    results.get("eval_accuracy", 0),
        "val_macro_f1":    results.get("eval_macro_f1", 0),
        "val_weighted_f1": results.get("eval_weighted_f1", 0),
        "val_loss":        results.get("eval_loss", 0),
    }
    mlflow.log_metrics(eval_metrics)

    # Log model artifact
    mlflow.pytorch.log_model(model, artifact_path="distilbert-emergency")

    # Log label encoder
    mlflow.log_artifact(ENCODER_PKL, artifact_path="encoder")

    # Print results
    print("=" * 70)
    print("  FINAL VALIDATION METRICS")
    print("=" * 70)
    for k, v in results.items():
        if isinstance(v, float):
            print(f"  {k:<25}: {v:.4f}")
        else:
            print(f"  {k:<25}: {v}")

    print(f"\n MLflow Run ID  : {run.info.run_id}")
    print(f"MLflow UI      : run `mlflow ui` then open http://localhost:5000")
    print("\n Training Completed Successfully!")
    print("=" * 70)