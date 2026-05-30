# training/baseline_tfidf.py
# TF-IDF + Logistic Regression baseline
# Run this BEFORE or AFTER train.py to get a comparison benchmark.
#
# Usage (run from ANY directory):
#   python training/baseline_tfidf.py
#   cd training && python baseline_tfidf.py
#
# Output:
#   - Prints classification report (F1 per class)
#   - Prints comparison table: TF-IDF vs DistilBERT
#   - Saves dataset/processed/baseline_confusion_matrix.png

import os
import sys
from pathlib import Path
import joblib
import pandas as pd
import numpy as np
import matplotlib.pyplot as plt
import seaborn as sns

# Always resolve paths relative to PROJECT ROOT (one level up from this file)
ROOT = Path(__file__).resolve().parent.parent
os.chdir(ROOT)   # make all relative paths work from project root
print(f"Working directory set to: {ROOT}")

from sklearn.feature_extraction.text import TfidfVectorizer
from sklearn.linear_model import LogisticRegression
from sklearn.pipeline import Pipeline
from sklearn.metrics import (
    classification_report,
    confusion_matrix,
    f1_score,
    accuracy_score,
)

# ─────────────────────────────────────────────────────────────────────────────
# CONFIG
# ─────────────────────────────────────────────────────────────────────────────

TRAIN_CSV   = "dataset/processed/train.csv"
VAL_CSV     = "dataset/processed/val.csv"
TEST_CSV    = "dataset/processed/test.csv"
ENCODER_PKL = "backend/app/model/label_encoder.pkl"
OUT_DIR     = "dataset/processed"
MODEL_SAVE  = "backend/app/model/tfidf_baseline.pkl"

# ─────────────────────────────────────────────────────────────────────────────
# LOAD DATA
# ─────────────────────────────────────────────────────────────────────────────

print("=" * 70)
print("  TF-IDF + Logistic Regression Baseline")
print("=" * 70)

print("\n Loading data...")
train_df = pd.read_csv(TRAIN_CSV)
val_df   = pd.read_csv(VAL_CSV)
test_df  = pd.read_csv(TEST_CSV)

print(f"  Train : {len(train_df):,} rows")
print(f"  Val   : {len(val_df):,} rows")
print(f"  Test  : {len(test_df):,} rows")

# combine train + val for fitting (same data the DistilBERT used)
train_all = pd.concat([train_df, val_df], ignore_index=True)

X_train = train_all["text"].astype(str).tolist()
y_train = train_all["label"].tolist()
X_test  = test_df["text"].astype(str).tolist()
y_test  = test_df["label"].tolist()

le = joblib.load(ENCODER_PKL)
classes = le.classes_.tolist()

# ─────────────────────────────────────────────────────────────────────────────
# BUILD PIPELINE
# TF-IDF: converts text into a sparse matrix of word importance scores
# Logistic Regression: fast, interpretable linear classifier
# ─────────────────────────────────────────────────────────────────────────────

print("\n Building TF-IDF pipeline...")
pipeline = Pipeline([
    ("tfidf", TfidfVectorizer(
        ngram_range=(1, 2),     # unigrams + bigrams
        max_features=50_000,    # top 50k features
        sublinear_tf=True,      # log-scale TF to reduce impact of high freq words
        min_df=2,               # ignore terms appearing in <2 docs
        strip_accents="unicode",
        analyzer="word",
    )),
    ("clf", LogisticRegression(
        max_iter=1000,
        C=5.0,
        class_weight="balanced",    # handles class imbalance same as our DistilBERT fix
        solver="lbfgs",
        random_state=42,
    )),
])

# ─────────────────────────────────────────────────────────────────────────────
# TRAIN
# ─────────────────────────────────────────────────────────────────────────────

print("\n Training TF-IDF baseline...")
pipeline.fit(X_train, y_train)
print(" Training complete")

# ─────────────────────────────────────────────────────────────────────────────
# EVALUATE ON TEST SET
# ─────────────────────────────────────────────────────────────────────────────

print("\n Evaluating on test set...")
y_pred = pipeline.predict(X_test)

macro_f1    = f1_score(y_test, y_pred, average="macro",    labels=classes)
weighted_f1 = f1_score(y_test, y_pred, average="weighted", labels=classes)
accuracy    = accuracy_score(y_test, y_pred)

print("\n" + "=" * 70)
print("  CLASSIFICATION REPORT — TF-IDF + Logistic Regression")
print("=" * 70)
print(classification_report(y_test, y_pred, target_names=classes))

# ─────────────────────────────────────────────────────────────────────────────
# CONFUSION MATRIX
# ─────────────────────────────────────────────────────────────────────────────

cm = confusion_matrix(y_test, y_pred, labels=classes)
plt.figure(figsize=(8, 6))
sns.heatmap(
    cm, annot=True, fmt="d", cmap="Oranges",
    xticklabels=classes, yticklabels=classes,
)
plt.title("Confusion Matrix — TF-IDF Baseline (Test Set)")
plt.ylabel("True Label")
plt.xlabel("Predicted Label")
plt.tight_layout()
cm_path = os.path.join(OUT_DIR, "baseline_confusion_matrix.png")
plt.savefig(cm_path, dpi=150)
plt.close()
print(f"\n Confusion matrix saved → {cm_path}")

# ─────────────────────────────────────────────────────────────────────────────
# QUICK KEYWORD GENERALIZATION TEST
# This shows HOW WELL the baseline generalises to paraphrases
# e.g. "trapped" vs "stucked" vs "stuck" vs "cannot get out"
# ─────────────────────────────────────────────────────────────────────────────

test_phrases = [
    # Accident variants — model should say "Accident"
    ("I am trapped inside the building",             "Accident"),
    ("I am stuck inside the building",               "Accident"),
    ("I am stucked inside the building",             "Accident"),  # intentional misspelling
    ("I cannot get out of the house",                "Accident"),
    ("We are stranded on the rooftop",               "Accident"),
    # Fire variants
    ("There is a fire in my house",                  "Fire"),
    ("My house is burning",                          "Fire"),
    ("Flames are coming from the building",          "Fire"),
    ("There is smoke everywhere I cant breathe",     "Fire"),
    ("The child is trapped inside fire house",       "Fire"),
    ("The child is stucked inside fire house",       "Fire"),
    # Medical variants
    ("Someone collapsed on the street",              "Medical"),
    ("Person is unconscious need help",              "Medical"),
    ("Man is not breathing please send ambulance",   "Medical"),
    # Flood variants — mix of context + keyword to stress-test
    ("Water level is rising in my area",             "Flood"),
    ("My street is completely flooded",              "Flood"),
    ("The river has overflowed into our colony",     "Flood"),
    ("The child is trapped inside flooded house",    "Flood"),
    ("The child is stucked inside flooded house",    "Flood"),
]

print("\n" + "=" * 70)
print("  KEYWORD GENERALIZATION TEST (TF-IDF Baseline)")
print("  Shows how model handles synonyms and misspellings")
print("=" * 70)
print(f"{'Input Text':<50} {'Expected':<18} {'Predicted':<12} {'Conf':>6}")
print("-" * 90)

for text, expected in test_phrases:
    pred   = pipeline.predict([text])[0]
    proba  = pipeline.predict_proba([text])[0]
    conf   = proba.max()
    match  = "Done" if pred == expected.split("/")[0] else "Fail "
    print(f"{match} {text:<48} {expected:<18} {pred:<12} {conf:.2%}")

# ─────────────────────────────────────────────────────────────────────────────
# SAVE BASELINE MODEL
# ─────────────────────────────────────────────────────────────────────────────

os.makedirs(os.path.dirname(MODEL_SAVE), exist_ok=True)
joblib.dump(pipeline, MODEL_SAVE)
print(f"\n Baseline model saved → {MODEL_SAVE}")

# ─────────────────────────────────────────────────────────────────────────────
# COMPARISON TABLE
# ─────────────────────────────────────────────────────────────────────────────

print("\n" + "=" * 70)
print("  BENCHMARK COMPARISON TABLE")
print("=" * 70)
print(f"  {'Model':<35} {'Accuracy':>10} {'Macro F1':>10} {'Weighted F1':>12}")
print(f"  {'-'*35} {'-'*10} {'-'*10} {'-'*12}")
print(f"  {'TF-IDF + Logistic Regression':<35} {accuracy:>10.2%} {macro_f1:>10.4f} {weighted_f1:>12.4f}")
print(f"  {'DistilBERT (run train.py first)':<35} {'???':>10} {'???':>10} {'???':>12}")
print()
print("   Run training/train.py to fill in the DistilBERT row")
print("=" * 70)

print("\n Baseline evaluation complete!")
print("  Files created:")
print(f"  → {cm_path}")
print(f"  → {MODEL_SAVE}")
