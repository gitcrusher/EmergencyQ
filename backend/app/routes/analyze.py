"""
POST /api/analyze  —  Main emergency triage pipeline route.

Pipeline order:
  1. Atomic Fact Decomposition     (Novelty ①)
  2. DistilBERT classification
  3. Conformal Prediction Set      (Novelty ②)
  4. ChromaDB retrieval
  5. Temporal Re-ranking           (Novelty ③)
  6. Severity + Urgency scoring    (uses adaptive weights — Novelty ④)
  7. DB persistence
  8. Return response
"""

from __future__ import annotations

import logging

from fastapi import APIRouter, HTTPException

from app.schemas.request_schema import ComplaintRequest, AnalyzeResponse
from app.fact_decomposer.decomposer import decompose, build_enriched_prefix
from app.model.conformal import get_prediction_set_from_text
from app.vectordb.retrieval import retrieve_similar
from app.langchain_chain.temporal_reranker import temporal_rerank
from app.utils.severity_engine import calculate_severity
from app.database.db import get_db
from app.database.models import Complaint

logger = logging.getLogger(__name__)

router = APIRouter(prefix="/api", tags=["analyze"])


@router.post("/analyze", response_model=AnalyzeResponse)
async def analyze_complaint(req: ComplaintRequest):
    """
    Accept a free-text emergency complaint and return a full triage response
    including category, prediction set, severity, urgency, atomic facts,
    and temporally re-ranked similar historical incidents.
    """
    complaint_text = req.complaint.strip()

    try:
        # ── Step 1: Atomic Fact Decomposition (Novelty ①) ──────────────────
        atomic_facts = decompose(complaint_text)
        enriched_text = build_enriched_prefix(atomic_facts) + complaint_text

        # ── Step 2 + 3: DistilBERT + Conformal Prediction Set (Novelty ②) ──
        prediction_set, proba, top_label, confidence = get_prediction_set_from_text(
            enriched_text
        )

        # ── Step 4: ChromaDB semantic retrieval ─────────────────────────────
        raw_results = retrieve_similar(complaint_text, top_k=20)

        # ── Step 5: Temporal Re-ranking (Novelty ③) ────────────────────────
        reranked = temporal_rerank(raw_results, top_k=5)

        # ── Step 6: Severity + Urgency ──────────────────────────────────────
        severity, urgency = calculate_severity(complaint_text)

        # ── Step 7: Persist to DB ───────────────────────────────────────────
        record = Complaint(
            text=complaint_text,
            category=top_label,
            prediction_set=prediction_set,
            severity=severity,
            urgency=urgency,
            confidence=round(float(confidence), 4),
            atomic_facts=atomic_facts,
        )
        with get_db() as db:
            db.add(record)
            db.commit()
            db.refresh(record)

        # ── Step 8: Return response ─────────────────────────────────────────
        return {
            "complaint_id":      record.id,
            "category":          top_label,
            "prediction_set":    prediction_set,
            "confidence":        round(float(confidence), 4),
            "severity":          severity,
            "urgency":           urgency,
            "atomic_facts":      atomic_facts,
            "similar_incidents": reranked,
        }

    except FileNotFoundError as exc:
        logger.error("Model asset missing: %s", exc)
        raise HTTPException(status_code=503, detail=str(exc))
    except Exception as exc:
        logger.exception("Unhandled error in /api/analyze: %s", exc)
        raise HTTPException(status_code=500, detail="Internal server error")