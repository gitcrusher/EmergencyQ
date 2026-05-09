# training/train.py
# SRS Phase 2 Step 2.2 — Fine-tune DistilBERT for 5-class emergency classification

import os
import joblib
import pandas as pd
import numpy as np
import torch

from transformers import (
    DistilBertTokenizer,
    DistilBertForSequenceClassification,
    Trainer,
    TrainingArguments,
    EarlyStoppingCallback,
)

from datasets import Dataset

from sklearn.metrics import (
    accuracy_score,
    f1_score,
)

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
BATCH_EVAL  = 16

EPOCHS      = 4
LR          = 2e-5

SEED        = 42

# ─────────────────────────────────────────────────────────────────────────────
# GPU / CUDA SETUP
# ─────────────────────────────────────────────────────────────────────────────

device = torch.device("cuda" if torch.cuda.is_available() else "cpu")

print("=" * 70)
print(" Emergency Complaint Analyzer — DistilBERT Training ")
print("=" * 70)

print(f"\n🔥 PyTorch Version : {torch.__version__}")

if torch.cuda.is_available():

    torch.cuda.empty_cache()

    print("✅ CUDA Available")
    print(f"✅ CUDA Version : {torch.version.cuda}")
    print(f"✅ GPU Name      : {torch.cuda.get_device_name(0)}")

    gpu_mem = torch.cuda.get_device_properties(0).total_memory / 1024**3
    print(f"✅ GPU Memory    : {gpu_mem:.2f} GB")

else:
    print("⚠ CUDA not available, running on CPU")

print(f"\n✅ Device Used : {device}")

# ─────────────────────────────────────────────────────────────────────────────
# REPRODUCIBILITY
# ─────────────────────────────────────────────────────────────────────────────

torch.manual_seed(SEED)

if torch.cuda.is_available():
    torch.cuda.manual_seed_all(SEED)

# ─────────────────────────────────────────────────────────────────────────────
# CREATE OUTPUT DIRECTORY
# ─────────────────────────────────────────────────────────────────────────────

os.makedirs(OUTPUT_DIR, exist_ok=True)

# ─────────────────────────────────────────────────────────────────────────────
# LOAD DATA
# ─────────────────────────────────────────────────────────────────────────────

print("\n📂 Loading datasets...")

train_df = pd.read_csv(TRAIN_CSV)
val_df   = pd.read_csv(VAL_CSV)

print(f"✅ Train rows : {len(train_df):,}")
print(f"✅ Val rows   : {len(val_df):,}")

# ─────────────────────────────────────────────────────────────────────────────
# LABEL ENCODER
# ─────────────────────────────────────────────────────────────────────────────

print("\n🏷 Loading label encoder...")

le = joblib.load(ENCODER_PKL)

train_df["label"] = le.transform(train_df["label"])
val_df["label"]   = le.transform(val_df["label"])

print(f"✅ Classes : {le.classes_.tolist()}")

# ─────────────────────────────────────────────────────────────────────────────
# TOKENIZER
# ─────────────────────────────────────────────────────────────────────────────

print("\n🧠 Loading tokenizer...")

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

print("\n⚙ Tokenizing datasets...")

train_ds = Dataset.from_pandas(
    train_df[["text", "label"]]
)

val_ds = Dataset.from_pandas(
    val_df[["text", "label"]]
)

train_ds = train_ds.map(tokenize, batched=True)
val_ds   = val_ds.map(tokenize, batched=True)

train_ds = train_ds.rename_column("label", "labels")
val_ds   = val_ds.rename_column("label", "labels")

train_ds.set_format(
    type="torch",
    columns=[
        "input_ids",
        "attention_mask",
        "labels"
    ]
)

val_ds.set_format(
    type="torch",
    columns=[
        "input_ids",
        "attention_mask",
        "labels"
    ]
)

# ─────────────────────────────────────────────────────────────────────────────
# MODEL
# ─────────────────────────────────────────────────────────────────────────────

print("\n🚀 Loading DistilBERT model...")

model = DistilBertForSequenceClassification.from_pretrained(
    MODEL_NAME,
    num_labels=NUM_LABELS
)

model.to(device)

print(f"✅ Model parameters : {model.num_parameters():,}")

# ─────────────────────────────────────────────────────────────────────────────
# METRICS
# ─────────────────────────────────────────────────────────────────────────────

def compute_metrics(eval_pred):

    logits, labels = eval_pred

    preds = np.argmax(logits, axis=-1)

    accuracy = accuracy_score(labels, preds)

    macro_f1 = f1_score(
        labels,
        preds,
        average="macro"
    )

    return {
        "accuracy": accuracy,
        "macro_f1": macro_f1,
    }

# ─────────────────────────────────────────────────────────────────────────────
# TRAINING ARGUMENTS
# ─────────────────────────────────────────────────────────────────────────────

print("\n⚙ Configuring training arguments...")

args = TrainingArguments(

    output_dir=OUTPUT_DIR,

    # TRAINING
    num_train_epochs=EPOCHS,

    per_device_train_batch_size=BATCH_TRAIN,
    per_device_eval_batch_size=BATCH_EVAL,

    gradient_accumulation_steps=2,

    # OPTIMIZATION
    learning_rate=LR,
    warmup_ratio=0.1,
    weight_decay=0.01,

    optim="adamw_torch",

    # EVALUATION
    eval_strategy="epoch",
    save_strategy="epoch",

    load_best_model_at_end=True,

    metric_for_best_model="macro_f1",
    greater_is_better=True,

    # LOGGING
    logging_steps=50,

    # REPRODUCIBILITY
    seed=SEED,

    # REPORTING
    report_to="none",

    # GPU OPTIMIZATION
    fp16=torch.cuda.is_available(),

    dataloader_pin_memory=True,

    # PYTORCH 2.x SPEEDUP
    #torch_compile=True,
)

# ─────────────────────────────────────────────────────────────────────────────
# TRAINER
# ─────────────────────────────────────────────────────────────────────────────

print("\n🧩 Building Trainer API...")

trainer = Trainer(

    model=model,

    args=args,

    train_dataset=train_ds,

    eval_dataset=val_ds,

    compute_metrics=compute_metrics,

    callbacks=[
        EarlyStoppingCallback(
            early_stopping_patience=2
        )
    ],
)

# ─────────────────────────────────────────────────────────────────────────────
# TRAINING
# ─────────────────────────────────────────────────────────────────────────────

print("\n🔥 Starting Training...\n")

trainer.train()

# ─────────────────────────────────────────────────────────────────────────────
# SAVE MODEL
# ─────────────────────────────────────────────────────────────────────────────

print("\n💾 Saving model...")

trainer.save_model(OUTPUT_DIR)

tokenizer.save_pretrained(OUTPUT_DIR)

print(f"✅ Model saved to : {OUTPUT_DIR}")

# ─────────────────────────────────────────────────────────────────────────────
# FINAL EVALUATION
# ─────────────────────────────────────────────────────────────────────────────

print("\n📊 Running final evaluation...\n")

results = trainer.evaluate()

print("=" * 70)
print(" FINAL VALIDATION METRICS ")
print("=" * 70)

for k, v in results.items():

    if isinstance(v, float):
        print(f"{k:<20}: {v:.4f}")

    else:
        print(f"{k:<20}: {v}")

print("\n Training Completed Successfully!")
print("=" * 70)