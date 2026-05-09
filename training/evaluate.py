# training/evaluate.py
# SRS Phase 2 — Evaluate trained model on test split
# Run AFTER train.py completes.
#
# Run:  python training/evaluate.py

import joblib
import pandas as pd
import numpy as np
import torch
from transformers import DistilBertTokenizer, DistilBertForSequenceClassification
from torch.utils.data import DataLoader, TensorDataset
from sklearn.metrics import classification_report, confusion_matrix
import matplotlib.pyplot as plt
import seaborn as sns
import os

MODEL_DIR   = "backend/app/model/trained_model"
ENCODER_PKL = "backend/app/model/label_encoder.pkl"
TEST_CSV    = "dataset/processed/test.csv"
MAX_LENGTH  = 128
BATCH_SIZE  = 32

device = torch.device("cuda" if torch.cuda.is_available() else "cpu")
print(f"Device: {device}")

# Load
le        = joblib.load(ENCODER_PKL)
tokenizer = DistilBertTokenizer.from_pretrained(MODEL_DIR)
model     = DistilBertForSequenceClassification.from_pretrained(MODEL_DIR)
model.to(device)
model.eval()

test_df = pd.read_csv(TEST_CSV)
print(f"Test rows: {len(test_df):,}")

# Tokenise
enc = tokenizer(
    test_df["text"].tolist(),
    truncation=True,
    padding="max_length",
    max_length=MAX_LENGTH,
    return_tensors="pt",
)
labels_true = torch.tensor(le.transform(test_df["label"].tolist()))
dataset = TensorDataset(enc["input_ids"], enc["attention_mask"], labels_true)
loader  = DataLoader(dataset, batch_size=BATCH_SIZE)

# Inference
all_preds, all_labels = [], []
with torch.no_grad():
    for input_ids, attn_mask, labs in loader:
        input_ids = input_ids.to(device)
        attn_mask = attn_mask.to(device)
        logits    = model(input_ids=input_ids, attention_mask=attn_mask).logits
        preds     = torch.argmax(logits, dim=-1).cpu().numpy()
        all_preds.extend(preds)
        all_labels.extend(labs.numpy())

all_preds  = np.array(all_preds)
all_labels = np.array(all_labels)

# Report
print("\n=== Classification Report (SRS Target: Macro-F1 > 0.85) ===")
print(classification_report(all_labels, all_preds, target_names=le.classes_))

# Confusion matrix
cm = confusion_matrix(all_labels, all_preds)
plt.figure(figsize=(8, 6))
sns.heatmap(cm, annot=True, fmt="d", cmap="Blues",
            xticklabels=le.classes_, yticklabels=le.classes_)
plt.title("Confusion Matrix — Test Set")
plt.ylabel("True Label")
plt.xlabel("Predicted Label")
plt.tight_layout()
plt.savefig("dataset/processed/confusion_matrix.png", dpi=150)
plt.show()
print("Confusion matrix saved.")