"""
app/langchain/chain.py
=======================
LangChain retrieval chain that combines ChromaDB incident retrieval
with optional LLM-generated context summaries.

Current role (Phase 1 — no external LLM)
-----------------------------------------
The chain wraps the TemporalChromaRetriever and formats retrieved
incidents into a structured context string. This context is returned
as part of the /api/analyze response and can be shown to dispatchers.

Future role (Phase 2 — with LLM)
----------------------------------
By replacing the formatter with a real LLM (e.g., Claude via Anthropic
API, or a local Ollama model), the chain can generate:
  • A plain-English summary of what happened in similar past incidents
  • A recommended response protocol based on historical outcomes
  • An uncertainty explanation when the prediction set has 2+ labels

The chain is designed so Phase 2 requires only swapping out
`_format_context()` for an actual LLM call — no structural changes.

Usage:
    from app.langchain.chain import build_chain, run_chain

    chain = build_chain(top_k=5)
    result = run_chain(chain, "Child trapped inside flooded basement")
    # result["context"]   → formatted string of similar incidents
    # result["documents"] → raw list of Document / dict objects
    # result["query"]     → original query echoed back
"""

from __future__ import annotations

import logging
import os
from dataclasses import dataclass, field
from typing import Any

logger = logging.getLogger(__name__)

TOP_K_DEFAULT: int = int(os.environ.get("CHAIN_TOP_K", "5"))


# ── Result dataclass ──────────────────────────────────────────────────────────

@dataclass
class ChainResult:
    """Structured output from run_chain()."""
    query:     str
    documents: list[Any]          # list[Document] or list[dict]
    context:   str                # formatted context string for the UI / LLM
    metadata:  dict = field(default_factory=dict)


# ── Context formatter ─────────────────────────────────────────────────────────

def _format_context(documents: list, max_incidents: int = 5) -> str:
    """
    Format retrieved incidents into a readable plain-English context block.

    Each incident is rendered as:

        [1] Category: Flood | Severity: High | Date: 2024-11-03
            "Flooding reported near Sector 22 underpass. Three vehicles stuck."
            Relevance score: 0.8741

    Parameters
    ----------
    documents   : list  LangChain Documents or raw dicts from retriever.
    max_incidents: int  Cap to avoid context bloat.

    Returns
    -------
    str  Human-readable context block. Empty string if no documents.
    """
    if not documents:
        return "No similar historical incidents found."

    lines = ["Similar historical incidents (temporally re-ranked):\n"]

    for i, doc in enumerate(documents[:max_incidents], start=1):
        # Handle both LangChain Document objects and plain dicts
        if hasattr(doc, "page_content"):
            text     = doc.page_content
            meta     = doc.metadata
        else:
            text     = doc.get("text", "")
            meta     = doc

        label    = meta.get("label", "Unknown")
        severity = meta.get("severity", "Unknown")
        date     = meta.get("date", meta.get("timestamp", "Unknown"))[:10]
        score    = meta.get("adjusted_score", meta.get("cosine_score", 0.0))

        lines.append(
            f"[{i}] Category: {label} | Severity: {severity} | Date: {date}\n"
            f"    \"{text[:200]}{'...' if len(text) > 200 else ''}\"\n"
            f"    Relevance score: {score:.4f}\n"
        )

    return "\n".join(lines)


# ── Chain class ───────────────────────────────────────────────────────────────

class IncidentRetrievalChain:
    """
    Lightweight retrieval chain for emergency incident context.

    Architecture:
        query
          │
          ▼
        retriever.get_relevant_documents(query)   ← ChromaDB + temporal rerank
          │
          ▼
        _format_context(documents)                ← structured context string
          │
          ▼
        ChainResult(query, documents, context)

    Phase 2 extension point:
        Replace _format_context() with an LLM call:
            llm_summary = llm.predict(PROMPT_TEMPLATE.format(context=context, query=query))
    """

    def __init__(self, retriever, top_k: int = TOP_K_DEFAULT):
        self.retriever = retriever
        self.top_k     = top_k

    def run(self, query: str) -> ChainResult:
        """
        Execute the retrieval chain for a given complaint query.

        Parameters
        ----------
        query : str  The complaint text (should be cleaned by preprocessing.py).

        Returns
        -------
        ChainResult  Contains documents, formatted context, and original query.
        """
        logger.info("IncidentRetrievalChain.run — query length=%d chars", len(query))

        # Step 1: Retrieve similar incidents (with temporal re-ranking inside retriever)
        documents = self.retriever.get_relevant_documents(query)

        # Step 2: Format context string
        context = _format_context(documents, max_incidents=self.top_k)

        logger.info(
            "Chain produced context: %d incidents, %d chars",
            len(documents), len(context),
        )

        return ChainResult(
            query=query,
            documents=documents,
            context=context,
            metadata={"num_incidents": len(documents)},
        )


# ── Factory functions ─────────────────────────────────────────────────────────

def build_chain(top_k: int = TOP_K_DEFAULT) -> IncidentRetrievalChain:
    """
    Build and return a fully initialized IncidentRetrievalChain.

    Parameters
    ----------
    top_k : int  How many incidents to include in the final context.

    Returns
    -------
    IncidentRetrievalChain
    """
    from app.langchain.retriever import build_retriever

    retriever = build_retriever(top_k=top_k, fetch_k=top_k * 4)
    chain     = IncidentRetrievalChain(retriever=retriever, top_k=top_k)

    logger.info("IncidentRetrievalChain built (top_k=%d).", top_k)
    return chain


def run_chain(chain: IncidentRetrievalChain, query: str) -> dict:
    """
    Convenience wrapper that runs the chain and returns a plain dict.
    Safe to call from FastAPI route handlers.

    Returns
    -------
    dict with keys: query, documents, context, metadata
    """
    result = chain.run(query)
    return {
        "query":     result.query,
        "documents": result.documents,
        "context":   result.context,
        "metadata":  result.metadata,
    }