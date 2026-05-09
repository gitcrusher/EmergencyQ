"""
Temporal-Decayed Similarity Re-ranking  —  Novelty ③
======================================================
Re-ranks ChromaDB results by applying an exponential time-decay
to each incident's cosine similarity score.

Formula:
    adjusted_score = cosine_similarity × exp(−λ × days_since_incident)

λ (DECAY_LAMBDA) defaults to 0.01:
    - Incident from 7 days ago   → multiplier ≈ 0.93
    - Incident from 90 days ago  → multiplier ≈ 0.41
    - Incident from 365 days ago → multiplier ≈ 0.026

A larger λ makes the decay more aggressive (recent incidents dominate).
Set DECAY_LAMBDA in .env to tune for your dataset recency distribution.
"""

from __future__ import annotations

import logging
import math
import os
from datetime import datetime, timezone

logger = logging.getLogger(__name__)

DECAY_LAMBDA: float = float(os.environ.get("DECAY_LAMBDA", "0.01"))


def temporal_rerank(
    results: list[dict],
    top_k: int = 5,
    lambda_: float | None = None,
) -> list[dict]:
    """
    Re-rank *results* by time-decayed similarity and return the top *top_k*.

    Parameters
    ----------
    results : list[dict]
        Each dict must have 'cosine_score' (float) and 'timestamp' (ISO-8601 str).
        'adjusted_score' will be set in-place.
    top_k   : int   Number of results to return after re-ranking.
    lambda_ : float Override DECAY_LAMBDA for this call (useful in tests).

    Returns
    -------
    list[dict] sorted by adjusted_score descending, length ≤ top_k.
    """
    lam = lambda_ if lambda_ is not None else DECAY_LAMBDA
    now = datetime.now(timezone.utc)

    for r in results:
        cosine = float(r.get("cosine_score", 0.0))
        ts_str = r.get("timestamp", "")

        try:
            ts = datetime.fromisoformat(ts_str)
            # Make timezone-aware if naive
            if ts.tzinfo is None:
                ts = ts.replace(tzinfo=timezone.utc)
            days_old = max((now - ts).days, 0)
        except (ValueError, TypeError):
            # Missing or malformed timestamp → treat as old (max penalty)
            logger.debug("Bad timestamp '%s'; applying max decay.", ts_str)
            days_old = 3650   # 10 years

        decay = math.exp(-lam * days_old)
        r["adjusted_score"] = round(cosine * decay, 4)
        r["date"] = ts_str[:10] if ts_str else "unknown"  # YYYY-MM-DD for UI

    ranked = sorted(results, key=lambda x: x["adjusted_score"], reverse=True)
    return ranked[:top_k]