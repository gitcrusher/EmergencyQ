"""
Lazy singleton loader for the fine-tuned DistilBERT model and tokenizer.
Call load_model() once at FastAPI startup; the result is cached globally.
"""

import os
import logging

import torch
import joblib
from transformers import DistilBertTokenizer, DistilBertForSequenceClassification
from sklearn.preprocessing import LabelEncoder

logger = logging.getLogger(__name__)

MODEL_PATH:  str = os.environ.get("MODEL_PATH", "./app/model/trained_model")
LABEL_PATH:  str = os.path.join(os.path.dirname(MODEL_PATH), "label_encoder.pkl")
DEVICE:      torch.device = torch.device("cuda" if torch.cuda.is_available() else "cpu")

# Module-level singletons (populated by load_model)
_tokenizer: DistilBertTokenizer | None = None
_model:     DistilBertForSequenceClassification | None = None
_le:        LabelEncoder | None = None


def load_model() -> None:
    """Load model, tokenizer, and label encoder from disk. Call once at startup."""
    global _tokenizer, _model, _le

    logger.info("Loading DistilBERT from %s on device=%s", MODEL_PATH, DEVICE)
    _tokenizer = DistilBertTokenizer.from_pretrained(MODEL_PATH)
    _model     = DistilBertForSequenceClassification.from_pretrained(MODEL_PATH)
    _model.to(DEVICE)
    _model.eval()

    _le = joblib.load(LABEL_PATH)
    logger.info("Model loaded. Classes: %s", list(_le.classes_))


def get_model() -> tuple[DistilBertForSequenceClassification,
                          DistilBertTokenizer,
                          LabelEncoder]:
    """Return the loaded (model, tokenizer, label_encoder) triple."""
    if _model is None:
        raise RuntimeError("Model not loaded. Call load_model() first.")
    return _model, _tokenizer, _le