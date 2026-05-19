"""
app/vectordb/embedding.py
==========================
Centralized sentence-transformer embedding utility for the vector database layer.

Previously, both retrieval.py and populate_vectordb.py had their own inline
`embed_text()` / `model.encode()` calls using the same model name. This module
consolidates them into a single shared loader so:

  • The model is loaded once per process (lru_cache singleton)
  • Both retrieval and population use identical normalization settings
  • The model name and device are configured in one place via .env
  • Future model swaps (e.g., to 'all-mpnet-base-v2') require only one change

Usage:
    from app.vectordb.embedding import embed_text, embed_batch

    # Single text
    vector = embed_text("Child trapped inside flooded house")
    # → list[float], length 384

    # Batch (for populate_vectordb or bulk re-indexing)
    vectors = embed_batch(["complaint one", "complaint two"], batch_size=64)
    # → np.ndarray of shape (2, 384)
"""

from __future__ import annotations

import functools
import logging
import os
from typing import Sequence

import numpy as np

logger = logging.getLogger(__name__)

# ── Config ────────────────────────────────────────────────────────────────────

EMBED_MODEL: str = os.environ.get("EMBED_MODEL", "all-MiniLM-L6-v2")
EMBED_DEVICE: str = os.environ.get("EMBED_DEVICE", "cpu")


# ── Lazy singleton loader ─────────────────────────────────────────────────────

@functools.lru_cache(maxsize=1)
def _get_model():
    """
    Load the sentence-transformer model exactly once per process.

    Respects HF_HUB_OFFLINE=1 to prevent any network call in production —
    the model must be pre-downloaded into the HuggingFace local cache
    (happens automatically on first run in a networked environment).
    """
    logger.info("Loading sentence-transformer: %s (device=%s)", EMBED_MODEL, EMBED_DEVICE)

    # Enforce offline mode in production to avoid surprise downloads
    os.environ.setdefault("HF_HUB_OFFLINE", "1")
    os.environ.setdefault("TRANSFORMERS_OFFLINE", "1")

    from sentence_transformers import SentenceTransformer

    model = SentenceTransformer(EMBED_MODEL, device=EMBED_DEVICE)
    logger.info("Sentence-transformer loaded (output_dim=%d).", model.get_sentence_embedding_dimension())
    return model


# ── Public API ────────────────────────────────────────────────────────────────

def embed_text(text: str) -> list[float]:
    """
    Embed a single text string and return a L2-normalised float list.

    This is the primary function used by retrieval.py when querying ChromaDB.
    The output is a Python list (not numpy) for direct JSON serialization and
    ChromaDB compatibility.

    Parameters
    ----------
    text : str  Any cleaned complaint text or query string.

    Returns
    -------
    list[float]  Embedding vector of length EMBED_DIM (384 for MiniLM-L6-v2).
    """
    model = _get_model()
    vector: np.ndarray = model.encode(
        text,
        normalize_embeddings=True,
        show_progress_bar=False,
    )
    return vector.tolist()


def embed_batch(
    texts: Sequence[str],
    batch_size: int = 128,
    show_progress: bool = False,
) -> np.ndarray:
    """
    Embed a list of texts in batches and return a normalised numpy array.

    This is the primary function used by populate_vectordb.py for bulk indexing.
    Using batched encoding is significantly faster than looping embed_text().

    Parameters
    ----------
    texts         : Sequence[str]  Input texts.
    batch_size    : int            Rows per encoder forward pass.
    show_progress : bool           Show tqdm progress bar (useful for large CSVs).

    Returns
    -------
    np.ndarray of shape (len(texts), EMBED_DIM), dtype float32.
    Each row is L2-normalised so dot-product == cosine similarity.
    """
    model = _get_model()
    embeddings: np.ndarray = model.encode(
        list(texts),
        batch_size=batch_size,
        normalize_embeddings=True,
        show_progress_bar=show_progress,
    )
    return embeddings.astype(np.float32)


def get_embedding_dim() -> int:
    """Return the output dimensionality of the loaded model."""
    return _get_model().get_sentence_embedding_dimension()