"""
app/fact_decomposer/atomic_embedder.py  —  Novelty ①
======================================================
Independently embeds each of the four atomic facts extracted by
decomposer.py using sentence-transformers, then concatenates the
four vectors into a single enriched representation.

This is the second half of the Atomic Fact Decomposition (AFD) pipeline:

    complaint text
        │
        ▼
    decomposer.py  ──► {location, victim_count, hazard_type, environment}
        │
        ▼
    atomic_embedder.py  ──► 4 × 384-dim vectors → concatenated 1536-dim vector

The concatenated vector can be used as:
  • A feature vector for downstream similarity comparisons
  • A richer query embedding when searching ChromaDB (replaces plain text embed)
  • An audit trail in the API response (planned extension)

Usage:
    from app.fact_decomposer.atomic_embedder import embed_atomic_facts, get_enriched_embedding

    facts = decompose("Child trapped inside flooded house near Station Road")
    fact_vector = embed_atomic_facts(facts)          # shape: (1536,)

    # Or get a combined embedding of the full complaint + facts
    enriched_vec = get_enriched_embedding(complaint_text, facts)  # shape: (1536,)
"""

from __future__ import annotations

import functools
import logging
import os
from typing import Optional

import numpy as np

logger = logging.getLogger(__name__)

# ── Config ────────────────────────────────────────────────────────────────────

EMBED_MODEL   = os.environ.get("EMBED_MODEL", "all-MiniLM-L6-v2")
EMBED_DIM     = 384          # all-MiniLM-L6-v2 output dimension
NUM_FACTS     = 4            # location, victim_count, hazard_type, environment
COMBINED_DIM  = EMBED_DIM * NUM_FACTS   # 1536

# Ordered list — embedding order is deterministic
FACT_KEYS: list[str] = ["location", "victim_count", "hazard_type", "environment"]

# Placeholder text used when a fact slot is empty, so the vector is not zero-padded
_EMPTY_PLACEHOLDER: dict[str, str] = {
    "location":     "unknown location",
    "victim_count": "unknown victims",
    "hazard_type":  "unknown hazard",
    "environment":  "unknown environment",
}


# ── Lazy model loader (same pattern as retrieval.py) ─────────────────────────

@functools.lru_cache(maxsize=1)
def _get_model():
    """
    Load sentence-transformer once per process lifetime.
    Respects HF_HUB_OFFLINE=1 to stay air-gapped in production.
    """
    logger.info("Loading atomic-fact sentence-transformer: %s", EMBED_MODEL)

    os.environ.setdefault("HF_HUB_OFFLINE", "1")
    os.environ.setdefault("TRANSFORMERS_OFFLINE", "1")

    from sentence_transformers import SentenceTransformer
    model = SentenceTransformer(EMBED_MODEL, device="cpu")

    logger.info("Atomic-fact encoder ready (dim=%d).", EMBED_DIM)
    return model


# ── Core functions ────────────────────────────────────────────────────────────

def embed_atomic_facts(facts: dict[str, str]) -> np.ndarray:
    """
    Embed each of the four atomic fact slots independently and
    concatenate the result into a single (COMBINED_DIM,) vector.

    Parameters
    ----------
    facts : dict
        Output of decomposer.decompose() — keys: location, victim_count,
        hazard_type, environment. Missing or empty values are replaced by
        a domain-specific placeholder so the vector is never zero.

    Returns
    -------
    np.ndarray of shape (COMBINED_DIM,) = (1536,), dtype float32.
    Each 384-element slice corresponds to one fact dimension in FACT_KEYS order.
    """
    model = _get_model()

    # Build one sentence per fact — use placeholder if slot is empty
    sentences: list[str] = [
        facts.get(key, "").strip() or _EMPTY_PLACEHOLDER[key]
        for key in FACT_KEYS
    ]

    logger.debug("Embedding atomic facts: %s", sentences)

    # Encode all four in a single batched call for efficiency
    embeddings: np.ndarray = model.encode(
        sentences,
        normalize_embeddings=True,
        show_progress_bar=False,
    )   # shape: (4, 384)

    # Concatenate along fact dimension → (1536,)
    combined = embeddings.flatten().astype(np.float32)

    logger.debug(
        "Atomic fact embedding produced: shape=%s, norm=%.4f",
        combined.shape,
        float(np.linalg.norm(combined)),
    )
    return combined


def get_enriched_embedding(
    complaint_text: str,
    facts: dict[str, str],
    alpha: float = 0.5,
) -> np.ndarray:
    """
    Produce a weighted combination of:
      • The plain complaint embedding (384-dim)
      • The concatenated atomic-fact embedding (1536-dim)

    Since dimensions differ, this function projects the plain embedding
    by repeating it across the four fact positions, then blends with the
    fact-specific embeddings.

        enriched = α × fact_embedding + (1 − α) × tiled_complaint_embedding

    Parameters
    ----------
    complaint_text : str    Raw complaint text.
    facts          : dict   Output of decomposer.decompose().
    alpha          : float  Weight for fact-specific embedding (0–1).
                            0.5 = equal blend; 1.0 = facts only.

    Returns
    -------
    np.ndarray of shape (COMBINED_DIM,) = (1536,), L2-normalised, float32.
    """
    if not 0.0 <= alpha <= 1.0:
        raise ValueError(f"alpha must be in [0, 1], got {alpha}")

    model = _get_model()

    # Plain complaint embedding → (384,)
    complaint_vec: np.ndarray = model.encode(
        complaint_text,
        normalize_embeddings=True,
        show_progress_bar=False,
    ).astype(np.float32)

    # Tile complaint embedding to match combined dimension → (1536,)
    tiled_complaint = np.tile(complaint_vec, NUM_FACTS)   # (1536,)

    # Atomic fact embedding → (1536,)
    fact_vec = embed_atomic_facts(facts)

    # Weighted blend
    enriched = alpha * fact_vec + (1.0 - alpha) * tiled_complaint

    # L2-normalise so cosine similarity is well-defined
    norm = np.linalg.norm(enriched)
    if norm > 0:
        enriched /= norm

    return enriched.astype(np.float32)


def fact_similarity(
    facts_a: dict[str, str],
    facts_b: dict[str, str],
) -> float:
    """
    Compute cosine similarity between the atomic-fact embeddings of two
    complaints. Useful for clustering or deduplication of similar incidents.

    Returns a float in [-1, 1] (typically [0, 1] for normalised embeddings).
    """
    vec_a = embed_atomic_facts(facts_a)
    vec_b = embed_atomic_facts(facts_b)
    return float(np.dot(vec_a, vec_b))   # both are L2-normalised