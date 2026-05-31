"""
Lazy singleton loader for DistilBERT.
"""

from __future__ import annotations

print("LOADER IMPORT 1")

import os

print(" LOADER IMPORT 2")

import logging

print("LOADER IMPORT 3")

import torch

print("TORCH IMPORTED")

import joblib

print("JOBLIB IMPORTED")

from transformers import (
    DistilBertTokenizer,
    DistilBertForSequenceClassification,
)

print("TRANSFORMERS IMPORTED")

from sklearn.preprocessing import LabelEncoder

print("SKLEARN IMPORTED")

logger = logging.getLogger(__name__)

# ─────────────────────────────────────────────
# PATHS
MODEL_PATH = "app/model/trained_model/quantized"

LABEL_PATH = "app/model/label_encoder.pkl"

# ─────────────────────────────────────────────
# DEVICE
# ─────────────────────────────────────────────

DEVICE = torch.device(
    "cuda" if torch.cuda.is_available() else "cpu"
)

print(f"USING DEVICE: {DEVICE}")

# ─────────────────────────────────────────────
# SINGLETONS
# ─────────────────────────────────────────────

_tokenizer = None
_model = None
_le = None

# ─────────────────────────────────────────────
# LOAD MODEL
# ─────────────────────────────────────────────

def load_model():

    global _tokenizer, _model, _le

    # Avoid reloading
    if _model is not None:
        print(" MODEL ALREADY LOADED")
        return

    print("\n STARTING MODEL LOAD")

    print(" MODEL PATH:", MODEL_PATH)
    print(" LABEL PATH:", LABEL_PATH)

    # ───────────────── MODEL DIR ─────────────────

    print(" CHECKING MODEL DIRECTORY")

    if not os.path.exists(MODEL_PATH):
        raise FileNotFoundError(
            f"Model path not found: {MODEL_PATH}"
        )

    print(" MODEL DIRECTORY EXISTS")

    print(" MODEL FILES:")
    print(os.listdir(MODEL_PATH))

    # ───────────────── TOKENIZER ─────────────────

    print("\n LOADING TOKENIZER")

    try:
        _tokenizer = DistilBertTokenizer.from_pretrained(
            MODEL_PATH,
            local_files_only=True
        )

        print(" TOKENIZER LOADED")

    except Exception as e:
        print(" TOKENIZER ERROR:", str(e))
        raise e

    # ───────────────── MODEL ─────────────────

    print("\n LOADING DISTILBERT MODEL")

    try:
        import torch.quantization
        from transformers import DistilBertConfig
        
        # 1. Load model configuration
        config = DistilBertConfig.from_pretrained(MODEL_PATH, local_files_only=True)
        
        # 2. Initialize empty model architecture
        _model = DistilBertForSequenceClassification(config)
        
        # 3. Apply dynamic quantization to match the saved architecture
        _model = torch.quantization.quantize_dynamic(
            _model, {torch.nn.Linear}, dtype=torch.qint8
        )
        
        # 4. Load the INT8 state dict
        state_dict_path = os.path.join(MODEL_PATH, "model_quantized.pt")
        _model.load_state_dict(torch.load(state_dict_path, map_location=DEVICE))

        print("MODEL LOADED SUCCESSFULLY")

    except Exception as e:
        print(" MODEL ERROR:", str(e))
        raise e

    # ───────────────── DEVICE ─────────────────

    print("\n MOVING MODEL TO DEVICE")

    try:
        _model.to(DEVICE)
        _model.eval()

        print(f"MODEL MOVED TO {DEVICE}")

    except Exception as e:
        print("DEVICE ERROR:", str(e))
        raise e

    # ───────────────── LABEL ENCODER ─────────────────

    print("\n LOADING LABEL ENCODER")

    try:
        _le = joblib.load(LABEL_PATH)

        print("LABEL ENCODER LOADED")
        print(" CLASSES:", list(_le.classes_))

    except Exception as e:
        print(" LABEL ENCODER ERROR:", str(e))
        raise e

    print("\n MODEL SYSTEM FULLY LOADED")

    logger.info("Model loaded successfully.")

# ─────────────────────────────────────────────
# GET MODEL
# ─────────────────────────────────────────────

def get_model():

    if _model is None:
        raise RuntimeError(
            " Model not loaded. Call load_model() first."
        )

    return _model, _tokenizer, _le