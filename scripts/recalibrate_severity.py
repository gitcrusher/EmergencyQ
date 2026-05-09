"""
scripts/recalibrate_severity.py  —  Novelty ④
===============================================
Nightly cron job that re-averages severity keyword weights
from the full feedback_log history.

Logic:
  For every (complaint_id, predicted, actual) row where actual > predicted:
    - Extract keywords from the original complaint text
    - Add a correction signal to each keyword's running total
  After processing all rows, reset each keyword's score to the
  weighted average of its initial seed value and the cumulative
  correction total.

Run via cron:
    0 2 * * * cd /app && python scripts/recalibrate_severity.py >> /var/log/recalibrate.log 2>&1

Usage:
    python scripts/recalibrate_severity.py [--dry-run]
"""

from __future__ import annotations

import argparse
import logging
import sys
from pathlib import Path
from collections import defaultdict

sys.path.insert(0, str(Path(__file__).parent.parent / "backend"))

from dotenv import load_dotenv
load_dotenv()

from app.database.db import get_db
from app.database.models import Complaint, FeedbackLog, SeverityWeight

logging.basicConfig(level=logging.INFO, format="%(asctime)s | %(levelname)s | %(message)s")
logger = logging.getLogger(__name__)

SEVERITY_SCORES = {"Critical": 4, "High": 3, "Moderate": 2, "Low": 1}
ALPHA = 0.8


def main(dry_run: bool = False):
    logger.info("=== Severity Recalibration Start (dry_run=%s) ===", dry_run)

    with get_db() as db:
        # Load all feedback rows where model under-predicted
        feedback_rows = db.query(FeedbackLog).all()
        complaints_map = {
            c.id: c.text
            for c in db.query(Complaint.id, Complaint.text).all()
        }
        current_weights = {
            row.keyword: row.score
            for row in db.query(SeverityWeight).all()
        }

    # Accumulate correction signals per keyword
    keyword_corrections: dict[str, list[float]] = defaultdict(list)

    for fb in feedback_rows:
        actual_score = SEVERITY_SCORES.get(fb.actual, 0)
        pred_score   = SEVERITY_SCORES.get(fb.predicted, 0)
        if actual_score <= pred_score:
            continue

        delta = float(actual_score - pred_score)
        text  = complaints_map.get(fb.complaint_id, "")
        words = {w for w in text.lower().split() if len(w) > 2}
        matched = words & current_weights.keys()

        if not matched:
            continue

        correction_per_kw = delta / len(matched)
        for kw in matched:
            keyword_corrections[kw].append(correction_per_kw)

    logger.info("Keywords with corrections: %d", len(keyword_corrections))

    # Compute new weights
    new_weights: dict[str, float] = {}
    for kw, corrections in keyword_corrections.items():
        old = current_weights.get(kw, 0.0)
        avg_correction = sum(corrections) / len(corrections)
        new_weights[kw] = ALPHA * old + (1 - ALPHA) * (old + avg_correction)
        logger.info("  %s: %.2f → %.2f", kw, old, new_weights[kw])

    if dry_run:
        logger.info("Dry run — no DB writes performed.")
        return

    # Write updated weights
    with get_db() as db:
        for kw, score in new_weights.items():
            row = db.query(SeverityWeight).filter(SeverityWeight.keyword == kw).first()
            if row:
                row.score = score
        db.commit()

    logger.info("=== Recalibration Complete: %d keywords updated ===", len(new_weights))


if __name__ == "__main__":
    parser = argparse.ArgumentParser()
    parser.add_argument("--dry-run", action="store_true",
                        help="Compute updates but do not write to DB")
    args = parser.parse_args()
    main(dry_run=args.dry_run)