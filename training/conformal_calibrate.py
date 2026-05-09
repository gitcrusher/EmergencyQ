"""
training/conformal_calibrate.py  —  Novelty ②
===============================================
Run AFTER fine-tuning is complete (training/train.py).

This script:
  1. Loads the fine-tuned DistilBERT + label encoder
  2. Runs inference on the validation split
  3. Calibrates an IcpClassifier using nonconformist
  4. Saves icp_model.pkl alongside the trained model

Usage:
    python training/conformal_calibrate.py

Output:
    backend/app/model/icp_model.pkl
"""

from __future__ import annotations

import sys
import os
import logging
from pathlib import Path

# Allow imports from project root
sys.path.insert(0, str(Path(__file__).parent.parent / "backend"))

import joblib
import numpy as np
import pandas as pd
from dotenv import load_dotenv

load_dotenv()

from app.model.loader import load_model, get_model
from app.model.predictor import predict_proba_batch

logging.basicConfig(level=logging.INFO, format="%(asctime)s | %(levelname)s | %(message)s")
logger = logging.getLogger(__name__)

MODEL_DIR  = Path(os.environ.get("MODEL_PATH", "./backend/app/model/trained_model"))
ICP_PATH   = MODEL_DIR.parent / "icp_model.pkl"
VAL_CSV    = Path("dataset/processed/val.csv")
ALPHA      = float(os.environ.get("CONFORMAL_ALPHA", "0.05"))


def main():
    logger.info("Loading model …")
    load_model()
    _, _, le = get_model()

    logger.info("Reading calibration set from %s", VAL_CSV)
    df = pd.read_csv(VAL_CSV)
    X_cal = df["text"].tolist()
    y_cal = le.transform(df["label"].tolist()).astype(int)

    logger.info("Running batch inference on %d samples …", len(X_cal))
    proba_matrix = predict_proba_batch(X_cal)   # shape (N, num_labels)

    # ── Compute nonconformity scores ────────────────────────────────────────
    # Nonconformity score for sample i, true class y_i:
    #   nc_i = 1 − P(y_i | x_i)
    n_classes = proba_matrix.shape[1]
    nc_scores = np.array([1.0 - proba_matrix[i, y_cal[i]] for i in range(len(y_cal))])

    # ── Compute per-class thresholds ────────────────────────────────────────
    # For each class c, the threshold is the (1−α) quantile of nc_scores
    # restricted to samples where y_i == c.
    thresholds = {}
    for c in range(n_classes):
        idx = np.where(y_cal == c)[0]
        if len(idx) == 0:
            thresholds[c] = 1.0
            continue
        q = np.quantile(nc_scores[idx], 1.0 - ALPHA)
        thresholds[c] = float(q)
        logger.info("  Class %s  threshold=%.4f  (n=%d)", le.classes_[c], q, len(idx))

    # ── Save calibration artifact ───────────────────────────────────────────
    artifact = {
        "thresholds":  thresholds,      # {class_idx: nc_threshold}
        "alpha":       ALPHA,
        "classes":     list(le.classes_),
        "n_cal":       len(y_cal),
    }
    ICP_PATH.parent.mkdir(parents=True, exist_ok=True)
    joblib.dump(artifact, ICP_PATH)
    logger.info("Calibration artifact saved to %s", ICP_PATH)

    # ── Empirical coverage check ────────────────────────────────────────────
    correct = 0
    for i in range(len(y_cal)):
        nc_i = 1.0 - proba_matrix[i, y_cal[i]]
        if nc_i <= thresholds[int(y_cal[i])]:
            correct += 1
    coverage = correct / len(y_cal)
    logger.info("Empirical coverage = %.3f  (target ≥ %.3f)", coverage, 1.0 - ALPHA)
    if coverage < 1.0 - ALPHA:
        logger.warning("Coverage below target. Consider increasing calibration set size.")

    logger.info("Conformal calibration complete.")


if __name__ == "__main__":
    main()