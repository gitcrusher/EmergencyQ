"""
Adaptive Severity Feedback Loop  —  Novelty ④
===============================================
Updates keyword weights in PostgreSQL when a responder reports that
the model's predicted severity was lower than the actual severity.

Update formula (exponential moving average):
    new_weight = α × old_weight + (1 − α) × (old_weight + correction)

where
    α           = SEVERITY_SMOOTHING_ALPHA  (default 0.8)
    correction  = (actual_score − predicted_score) / keyword_count

Only under-predictions are updated (over-predictions are discarded)
to avoid reducing weights on words that appeared coincidentally.
"""

from __future__ import annotations

import logging
import os
import datetime

from app.database.db import get_db
from app.database.models import SeverityWeight, FeedbackLog

logger = logging.getLogger(__name__)

ALPHA: float = float(os.environ.get("SEVERITY_SMOOTHING_ALPHA", "0.8"))

SEVERITY_SCORES: dict[str, int] = {
    "Critical": 4,
    "High":     3,
    "Moderate": 2,
    "Low":      1,
}


def update_weights(
    complaint_id:  str,
    complaint_text: str,
    predicted:     str,
    actual:        str,
    notes:         str | None = None,
) -> bool:
    """
    Apply the adaptive weight update if actual > predicted severity.

    Parameters
    ----------
    complaint_id   : UUID of the logged complaint.
    complaint_text : Raw text of the complaint (to identify keywords).
    predicted      : Severity predicted by the model ("Critical"|"High"|…).
    actual         : Severity observed by the responder.
    notes          : Optional responder notes (logged only).

    Returns
    -------
    bool  True if weights were updated, False if update was skipped.
    """
    pred_score   = SEVERITY_SCORES.get(predicted, 0)
    actual_score = SEVERITY_SCORES.get(actual, 0)

    # Log the feedback regardless of whether we update weights
    _log_feedback(complaint_id, predicted, actual, notes)

    if actual_score <= pred_score:
        logger.info(
            "Feedback for %s: actual=%s ≤ predicted=%s — no weight update.",
            complaint_id, actual, predicted,
        )
        return False

    delta = float(actual_score - pred_score)
    words = {w for w in complaint_text.lower().split() if len(w) > 2}

    with get_db() as db:
        rows = (
            db.query(SeverityWeight)
            .filter(SeverityWeight.keyword.in_(words))
            .all()
        )

        if not rows:
            logger.warning("No severity keywords matched complaint %s", complaint_id)
            return False

        correction = delta / len(rows)
        for row in rows:
            row.score = ALPHA * row.score + (1 - ALPHA) * (row.score + correction)
            row.updated_at = datetime.datetime.utcnow()

        db.commit()

    logger.info(
        "Updated %d keyword weights for complaint %s (delta=%.1f, α=%.2f)",
        len(rows), complaint_id, delta, ALPHA,
    )
    return True


def _log_feedback(
    complaint_id: str,
    predicted: str,
    actual: str,
    notes: str | None,
) -> None:
    """Persist the feedback event to feedback_log for auditing."""
    entry = FeedbackLog(
        complaint_id=complaint_id,
        predicted=predicted,
        actual=actual,
        notes=notes,
    )
    with get_db() as db:
        db.add(entry)
        db.commit()