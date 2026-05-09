"""
DistilBERT inference module.

predict_proba(text)        → (proba_array, top_label, confidence)
predict_proba_batch(texts) → list of proba_arrays   (used by conformal calibration)
"""

from __future__ import annotations

import logging
from typing import Sequence

import numpy as np
import torch

from app.model.loader import get_model, DEVICE

logger = logging.getLogger(__name__)

MAX_LENGTH = 128


def _run_inference(texts: list[str]) -> np.ndarray:
    """
    Tokenize *texts* and return a (N, num_labels) float32 softmax array.
    All computation is done inside torch.no_grad().
    """
    model, tokenizer, _ = get_model()

    encoding = tokenizer(
        texts,
        padding="max_length",
        truncation=True,
        max_length=MAX_LENGTH,
        return_tensors="pt",
    )
    input_ids      = encoding["input_ids"].to(DEVICE)
    attention_mask = encoding["attention_mask"].to(DEVICE)

    with torch.no_grad():
        logits = model(input_ids=input_ids, attention_mask=attention_mask).logits

    proba = torch.softmax(logits, dim=-1).cpu().numpy()   # shape (N, num_labels)
    return proba.astype(np.float32)


def predict_proba(text: str) -> tuple[np.ndarray, str, float]:
    """
    Run inference on a single complaint string.

    Returns
    -------
    proba       : shape (num_labels,) softmax probability array
    top_label   : predicted class name (str)
    confidence  : probability of top class (float)
    """
    _, _, le = get_model()
    proba = _run_inference([text])[0]            # (num_labels,)

    top_idx    = int(np.argmax(proba))
    top_label  = le.classes_[top_idx]
    confidence = float(proba[top_idx])

    logger.debug("predict_proba → %s (%.3f)", top_label, confidence)
    return proba, top_label, confidence


def predict_proba_batch(texts: Sequence[str]) -> np.ndarray:
    """
    Batch inference — returns shape (N, num_labels).
    Used by conformal_calibrate.py during calibration.
    """
    CHUNK = 32
    results = []
    texts = list(texts)
    for i in range(0, len(texts), CHUNK):
        results.append(_run_inference(texts[i : i + CHUNK]))
    return np.vstack(results)