"""
app/langchain/retriever.py
==========================
LangChain-compatible retriever that wraps ChromaDB + temporal re-ranking.

Why this exists
---------------
`app/vectordb/retrieval.py` calls ChromaDB directly. That is fine for the
current /api/analyze pipeline, but LangChain's chain abstraction (chain.py)
requires a retriever that implements the BaseRetriever interface so it can be
composed with other LangChain components (e.g., a future LLM summarization
step, RetrievalQA, or a multi-retriever ensemble).

This module bridges the gap:

    LangChain Chain
         │
         ▼
    TemporalChromaRetriever  (this file)
         │  get_relevant_documents(query)
         ▼
    retrieval.retrieve_similar()   ── ChromaDB cosine search
         │
         ▼
    temporal_reranker.temporal_rerank()   ── time-decay re-scoring
         │
         ▼
    list[Document]   ← LangChain Document objects

Usage:
    from app.langchain.retriever import build_retriever

    retriever = build_retriever(top_k=5)
    docs = retriever.get_relevant_documents("fire near main road")
    # Each doc.page_content = incident text
    # doc.metadata = {label, severity, timestamp, cosine_score, adjusted_score}
"""

from __future__ import annotations

import logging
import os
from typing import List

logger = logging.getLogger(__name__)

TOP_K_DEFAULT: int = int(os.environ.get("RETRIEVER_TOP_K", "5"))
FETCH_K: int       = int(os.environ.get("RETRIEVER_FETCH_K", "20"))   # over-fetch before rerank


# ── LangChain Document shim (avoids hard dependency on specific langchain ver) ─

try:
    from langchain_core.documents import Document
    from langchain_core.retrievers import BaseRetriever
    _LANGCHAIN_AVAILABLE = True
except ImportError:
    try:
        from langchain.schema import Document, BaseRetriever
        _LANGCHAIN_AVAILABLE = True
    except ImportError:
        _LANGCHAIN_AVAILABLE = False
        logger.warning(
            "langchain not installed — TemporalChromaRetriever will return "
            "raw dicts instead of Document objects. Install langchain>=0.2.0."
        )


# ── Retriever implementation ──────────────────────────────────────────────────

if _LANGCHAIN_AVAILABLE:

    class TemporalChromaRetriever(BaseRetriever):
        """
        LangChain BaseRetriever that:
          1. Queries ChromaDB for the top FETCH_K semantically similar incidents
          2. Applies exponential time-decay re-ranking (Novelty ③)
          3. Returns the top_k results as LangChain Document objects

        The retriever is stateless — it reads from ChromaDB on every call.

        Attributes
        ----------
        top_k  : int  Number of documents to return after re-ranking.
        fetch_k: int  Number of candidates to fetch from ChromaDB before rerank.
        """

        top_k:   int = TOP_K_DEFAULT
        fetch_k: int = FETCH_K

        class Config:
            arbitrary_types_allowed = True

        def _get_relevant_documents(self, query: str) -> List[Document]:
            return _fetch_and_rerank(query, self.top_k, self.fetch_k)

        async def _aget_relevant_documents(self, query: str) -> List[Document]:
            # Sync fallback — async ChromaDB client is not used in this project
            return self._get_relevant_documents(query)


def _fetch_and_rerank(
    query: str,
    top_k: int,
    fetch_k: int,
) -> list:
    """
    Core retrieval logic shared by both the LangChain retriever and the
    plain-dict fallback (used when langchain is not installed).
    """
    from app.vectordb.retrieval import retrieve_similar
    from app.langchain.temporal_reranker import temporal_rerank

    raw = retrieve_similar(query, top_k=fetch_k)
    reranked = temporal_rerank(raw, top_k=top_k)

    if not _LANGCHAIN_AVAILABLE:
        return reranked   # Return raw dicts if langchain not available

    documents = []
    for r in reranked:
        doc = Document(
            page_content=r.get("text", ""),
            metadata={
                "label":          r.get("label", ""),
                "severity":       r.get("severity", ""),
                "timestamp":      r.get("timestamp", ""),
                "date":           r.get("date", ""),
                "cosine_score":   r.get("cosine_score", 0.0),
                "adjusted_score": r.get("adjusted_score", 0.0),
            },
        )
        documents.append(doc)

    logger.info(
        "TemporalChromaRetriever: fetched=%d reranked=%d returned=%d",
        fetch_k, len(reranked), len(documents),
    )
    return documents


# ── Factory function ──────────────────────────────────────────────────────────

def build_retriever(top_k: int = TOP_K_DEFAULT, fetch_k: int = FETCH_K):
    """
    Factory that returns a TemporalChromaRetriever (if LangChain is available)
    or a lightweight callable wrapper (if not).

    Parameters
    ----------
    top_k  : int  Documents to return after temporal re-ranking.
    fetch_k: int  Candidates to retrieve from ChromaDB before re-ranking.

    Returns
    -------
    TemporalChromaRetriever | _FallbackRetriever
    """
    if _LANGCHAIN_AVAILABLE:
        return TemporalChromaRetriever(top_k=top_k, fetch_k=fetch_k)

    logger.warning("Returning fallback retriever (raw dicts, no LangChain).")
    return _FallbackRetriever(top_k=top_k, fetch_k=fetch_k)


class _FallbackRetriever:
    """
    Minimal retriever that returns raw dicts when LangChain is not installed.
    Has the same .get_relevant_documents() interface for duck-typing.
    """

    def __init__(self, top_k: int, fetch_k: int):
        self.top_k   = top_k
        self.fetch_k = fetch_k

    def get_relevant_documents(self, query: str) -> list[dict]:
        return _fetch_and_rerank(query, self.top_k, self.fetch_k)