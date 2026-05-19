"""
ChromaDB vector retrieval module.
Embeds incoming complaint text and retrieves the top-k most
semantically similar historical incidents.
"""

from __future__ import annotations

import logging
import os
import functools

import chromadb

logger = logging.getLogger(__name__)

CHROMA_DIR      = os.environ.get("CHROMA_PERSIST_DIR", "./app/vectordb/chroma_db")
COLLECTION_NAME = "incidents"
EMBED_MODEL     = "all-MiniLM-L6-v2"


@functools.lru_cache(maxsize=1)
def _get_embed_model():
    """
    Load sentence-transformer model.
    Uses HuggingFace local cache after first download.
    Set HF_HUB_OFFLINE=1 in .env to force offline mode.
    """
    logger.info("Loading sentence-transformer: %s", EMBED_MODEL)

    # Force offline mode — prevents any network call, uses local cache only
    os.environ["HF_HUB_OFFLINE"]       = "1"
    os.environ["TRANSFORMERS_OFFLINE"]  = "1"

    from sentence_transformers import SentenceTransformer

    model = SentenceTransformer(
        EMBED_MODEL,
        device="cpu",
    )

    logger.info("Sentence-transformer loaded successfully.")
    return model


@functools.lru_cache(maxsize=1)
def _get_collection():
    """Connect to ChromaDB and return the incidents collection."""
    logger.info("Connecting to ChromaDB at: %s", CHROMA_DIR)

    client = chromadb.PersistentClient(path=CHROMA_DIR)
    col = client.get_or_create_collection(
        name=COLLECTION_NAME,
        metadata={"hnsw:space": "cosine"},
    )

    logger.info("ChromaDB ready — %d documents loaded.", col.count())
    return col


def embed_text(text: str) -> list[float]:
    """Return normalized embedding for a single text string."""
    model = _get_embed_model()
    return model.encode(text, normalize_embeddings=True).tolist()


def retrieve_similar(text: str, top_k: int = 20) -> list[dict]:
    """
    Query ChromaDB and return up to top_k similar incidents.
    """
    col = _get_collection()

    if col.count() == 0:
        logger.warning("ChromaDB collection is empty. Run scripts/populate_vectordb.py first.")
        return []

    query_embedding = embed_text(text)

    results = col.query(
        query_embeddings=[query_embedding],
        n_results=min(top_k, col.count()),
        include=["documents", "metadatas", "distances"],
    )

    incidents = []
    for doc, meta, dist in zip(
        results["documents"][0],
        results["metadatas"][0],
        results["distances"][0],
    ):
        cosine_sim = float(1.0 - dist)
        incidents.append({
            "text":           doc,
            "label":          meta.get("label", ""),
            "severity":       meta.get("severity", ""),
            "timestamp":      meta.get("timestamp", ""),
            "cosine_score":   round(cosine_sim, 4),
            "adjusted_score": round(cosine_sim, 4),
        })

    logger.info("Retrieved %d incidents from ChromaDB.", len(incidents))
    return incidents