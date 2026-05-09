"""
ChromaDB vector retrieval module.
Embeds incoming complaint text and retrieves the top-k most
semantically similar historical incidents.

retrieve_similar(text, top_k) → list[dict] ready for temporal re-ranking.
"""

from __future__ import annotations

import logging
import os
import functools

import chromadb
from sentence_transformers import SentenceTransformer

logger = logging.getLogger(__name__)

CHROMA_DIR      = os.environ.get("CHROMA_PERSIST_DIR", "./app/vectordb/chroma_db")
COLLECTION_NAME = "incidents"
EMBED_MODEL     = "all-MiniLM-L6-v2"


@functools.lru_cache(maxsize=1)
def _get_embed_model() -> SentenceTransformer:
    logger.info("Loading sentence-transformer: %s", EMBED_MODEL)
    return SentenceTransformer(EMBED_MODEL)


@functools.lru_cache(maxsize=1)
def _get_collection():
    client = chromadb.PersistentClient(path=CHROMA_DIR)
    col = client.get_or_create_collection(
        name=COLLECTION_NAME,
        metadata={"hnsw:space": "cosine"},
    )
    logger.info("ChromaDB collection '%s' ready (%d items)", COLLECTION_NAME, col.count())
    return col


def embed_text(text: str) -> list[float]:
    """Return the sentence-transformer embedding for a single text."""
    model = _get_embed_model()
    return model.encode(text, normalize_embeddings=True).tolist()


def retrieve_similar(text: str, top_k: int = 20) -> list[dict]:
    """
    Query ChromaDB and return up to *top_k* similar incidents.

    Each returned dict contains:
        text, label, severity, timestamp, cosine_score, adjusted_score (= cosine_score initially)
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
    documents  = results["documents"][0]
    metadatas  = results["metadatas"][0]
    distances  = results["distances"][0]       # cosine distance = 1 - similarity

    for doc, meta, dist in zip(documents, metadatas, distances):
        cosine_sim = float(1.0 - dist)
        incidents.append({
            "text":           doc,
            "label":          meta.get("label", ""),
            "severity":       meta.get("severity", ""),
            "timestamp":      meta.get("timestamp", ""),
            "cosine_score":   round(cosine_sim, 4),
            "adjusted_score": round(cosine_sim, 4),  # will be updated by temporal_reranker
        })

    return incidents