"""
Severity Engine
===============
Reads keyword weights from the severity_weights PostgreSQL table
and scores the incoming complaint text.

Severity  thresholds (tunable):
    score ≥ 35 → Critical
    score ≥ 22 → High
    score ≥ 12 → Moderate
    else       → Low

Urgency is derived from severity:
    Critical  → Immediate
    High      → Urgent
    Moderate  → Medium
    Low       → Normal
"""

from __future__ import annotations

import logging
from functools import lru_cache

from app.database.db import get_db
from app.database.models import SeverityWeight

logger = logging.getLogger(__name__)

SEVERITY_THRESHOLDS: list[tuple[float, str]] = [
    (35.0, "Critical"),
    (22.0, "High"),
    (12.0, "Moderate"),
    (0.0,  "Low"),
]

URGENCY_MAP: dict[str, str] = {
    "Critical": "Immediate",
    "High":     "Urgent",
    "Moderate": "Medium",
    "Low":      "Normal",
}

# Cache TTL: weights are re-loaded every N calls to avoid DB round-trip per request.
# In a high-throughput system consider a Redis-backed cache with TTL instead.
_CACHE_REFRESH_EVERY = 100
_call_count = 0
_weight_cache: dict[str, float] = {}


def _refresh_weights() -> dict[str, float]:
    """Load all keyword weights from DB into an in-memory dict."""
    with get_db() as db:
        rows = db.query(SeverityWeight).all()
    return {row.keyword: row.score for row in rows}


def _get_weights() -> dict[str, float]:
    global _call_count, _weight_cache
    _call_count += 1
    if _call_count == 1 or _call_count % _CACHE_REFRESH_EVERY == 0:
        _weight_cache = _refresh_weights()
        logger.debug("Severity weights refreshed (%d keywords)", len(_weight_cache))
    return _weight_cache


def _score_text(text: str, weights: dict[str, float]) -> float:
    """Sum the weights of all keywords found in *text*."""
    tokens = set(text.lower().split())
    return sum(weights.get(t, 0.0) for t in tokens)


def calculate_severity(text: str) -> tuple[str, str]:
    """
    Score *text* against adaptive keyword weights and return (severity, urgency).

    Parameters
    ----------
    text : str  Complaint text.

    Returns
    -------
    (severity, urgency) — both are human-readable label strings.
    """
    weights = _get_weights()
    score   = _score_text(text, weights)

    severity = "Low"
    for threshold, label in SEVERITY_THRESHOLDS:
        if score >= threshold:
            severity = label
            break

    urgency = URGENCY_MAP[severity]
    logger.debug("Severity score=%.1f → %s / %s", score, severity, urgency)
    return severity, urgency