"""
Conformal Prediction Sets — Novelty ②
=====================================

Uses custom threshold-based conformal calibration generated from:
training/conformal_calibrate.py

This version works with the saved dictionary artifact:
{
    "thresholds": {...},
    "alpha": ...,
    "classes": ...
}
"""

from __future__ import annotations

import logging
import os
from pathlib import Path

import joblib
import numpy as np

logger = logging.getLogger(__name__)

# ─────────────────────────────────────────────────────────────
# Config
# ─────────────────────────────────────────────────────────────

ICP_PATH = Path("app/model/icp_model.pkl")

CONFORMAL_ALPHA = float(
    os.environ.get("CONFORMAL_ALPHA", "0.05")
)

_icp = None


# ─────────────────────────────────────────────────────────────
# Lazy Loader
# ─────────────────────────────────────────────────────────────

def _load_icp():

    global _icp

    if _icp is None:

        if not ICP_PATH.exists():
            raise FileNotFoundError(
                f"ICP model not found at {ICP_PATH}. "
                f"Run training/conformal_calibrate.py first."
            )

        _icp = joblib.load(ICP_PATH)

        logger.info(
            "Conformal ICP model loaded from %s",
            ICP_PATH
        )

    return _icp


# ─────────────────────────────────────────────────────────────
# Prediction Set Logic
# ─────────────────────────────────────────────────────────────

def get_prediction_set(
    proba: np.ndarray
) -> list[str]:

    """
    Convert softmax probabilities into a conformal
    prediction set using calibrated thresholds.
    """

    from app.model.loader import get_model

    _, _, le = get_model()

    icp = _load_icp()

    thresholds = icp["thresholds"]

    included = []

    for class_idx, prob in enumerate(proba):

        # Nonconformity score
        nc_score = 1.0 - prob

        threshold = thresholds[class_idx]

        # Include class if below threshold
        if nc_score <= threshold:
            included.append(
                le.classes_[class_idx]
            )

    # Safety fallback
    if not included:

        top_idx = int(np.argmax(proba))

        included.append(
            le.classes_[top_idx]
        )

    return included


# ─────────────────────────────────────────────────────────────
# Full Convenience Pipeline
# ─────────────────────────────────────────────────────────────

def get_prediction_set_from_text(
    text: str
):

    """
    Full pipeline:
    text → probabilities → conformal prediction set
    """

    from app.model.predictor import predict_proba

    proba, top_label, confidence = predict_proba(text)

    prediction_set = get_prediction_set(proba)

    return (
        prediction_set,
        proba,
        top_label,
        confidence,
    )