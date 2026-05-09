"""
scripts/seed_weights.py
=======================
One-time script to populate the severity_weights table with initial
keyword scores. Safe to re-run — uses INSERT OR REPLACE semantics
via SQLAlchemy's db.merge().

Usage:
    python scripts/seed_weights.py
"""

import sys
import logging
from pathlib import Path

sys.path.insert(0, str(Path(__file__).parent.parent / "backend"))

from dotenv import load_dotenv
load_dotenv()

from app.database.db import init_db, get_db
from app.database.models import SeverityWeight

logging.basicConfig(level=logging.INFO, format="%(asctime)s | %(levelname)s | %(message)s")
logger = logging.getLogger(__name__)

# ── Initial keyword weight table ────────────────────────────────────────────
# Scores are additive — a complaint containing multiple high-score words
# will accumulate a high total and hit the Critical threshold (≥ 35).
INITIAL_WEIGHTS: dict[str, float] = {
    # Life-threatening
    "explosion":      42.0,
    "collapsed":      45.0,
    "trapped":        35.0,
    "drowning":       40.0,
    "choking":        38.0,
    "electrocution":  38.0,
    "unconscious":    35.0,
    "chemical":       38.0,
    # Serious
    "bleeding":       30.0,
    "critical":       30.0,
    "fire":           26.0,
    "flood":          26.0,
    "gas":            30.0,
    "crash":          25.0,
    "collision":      24.0,
    # Moderate
    "smoke":          20.0,
    "injury":         20.0,
    "injured":        20.0,
    "accident":       18.0,
    "fallen":         18.0,
    "burning":        22.0,
    "water":          12.0,
    "flooding":       22.0,
    "child":          14.0,   # boosts severity when victim is a child
    "children":       14.0,
    "baby":           16.0,
    "elderly":        12.0,
    # Low
    "damage":          8.0,
    "broken":          6.0,
    "stuck":           8.0,
}


def main():
    logger.info("Initializing database …")
    init_db()

    logger.info("Seeding %d severity keywords …", len(INITIAL_WEIGHTS))
    with get_db() as db:
        for keyword, score in INITIAL_WEIGHTS.items():
            db.merge(SeverityWeight(keyword=keyword, score=score))
        db.commit()

    logger.info("Severity weights seeded successfully.")


if __name__ == "__main__":
    main()