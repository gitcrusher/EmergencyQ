"""
POST /api/analyze — Main emergency triage pipeline route.
"""

from __future__ import annotations

import logging

print("🟡 ANALYZE IMPORT 1")
from fastapi import APIRouter, HTTPException

print("🟡 ANALYZE IMPORT 2")
from app.schemas.request_schema import ComplaintRequest, AnalyzeResponse

print("🟡 ANALYZE IMPORT 3")
from app.fact_decomposer.decomposer import decompose, build_enriched_prefix

print("🟡 ANALYZE IMPORT 4")
from app.model.conformal import get_prediction_set_from_text

print("🟡 ANALYZE IMPORT 5")
from app.vectordb.retrieval import retrieve_similar

print("🟡 ANALYZE IMPORT 6")
from app.langchain.temporal_reranker import temporal_rerank

print("🟡 ANALYZE IMPORT 7")
from app.utils.severity_engine import calculate_severity

print("🟡 ANALYZE IMPORT 8")
from app.database.db import get_db

print("🟡 ANALYZE IMPORT 9")
from app.database.models import Complaint

print("✅ ANALYZE IMPORT COMPLETE")

logger = logging.getLogger(__name__)

router = APIRouter(prefix="/api", tags=["analyze"])


@router.post("/analyze", response_model=AnalyzeResponse)
async def analyze_complaint(req: ComplaintRequest):

    print("\n🚀 /api/analyze CALLED")

    complaint_text = req.complaint.strip()

    try:

        # ── STEP 1 — Atomic Fact Decomposition ──────────────────────────────
        print("🔥 STEP 1 — Atomic Fact Decomposition")

        atomic_facts  = decompose(complaint_text)
        enriched_text = build_enriched_prefix(atomic_facts) + complaint_text

        print("✅ Atomic Facts:", atomic_facts)

        # ── STEP 2 — Conformal Prediction ────────────────────────────────────
        print("🔥 STEP 2 — Conformal Prediction")

        prediction_set, proba, top_label, confidence = get_prediction_set_from_text(
            enriched_text
        )

        print("✅ Prediction:", top_label)
        print("✅ Confidence:", confidence)

        # ── STEP 3 — ChromaDB Retrieval ──────────────────────────────────────
        print("🔥 STEP 3 — Chroma Retrieval")

        raw_results = retrieve_similar(complaint_text, top_k=20)

        print("✅ Retrieved:", len(raw_results))

        # ── STEP 4 — Temporal Reranking ──────────────────────────────────────
        print("🔥 STEP 4 — Temporal Reranking")

        reranked = temporal_rerank(raw_results, top_k=5)

        print("✅ Reranked:", len(reranked))

        # ── STEP 5 — Severity Engine ─────────────────────────────────────────
        print("🔥 STEP 5 — Severity Engine")

        severity, urgency = calculate_severity(complaint_text)

        print("✅ Severity:", severity)
        print("✅ Urgency:", urgency)

        # ── STEP 6 — Save to Database ─────────────────────────────────────────
        print("🔥 STEP 6 — Database Save")

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
            complaint_id = record.id   # ✅ extract INSIDE session

        print("✅ Complaint Saved")
        print("🎉 ANALYSIS COMPLETE")

        # ── STEP 7 — Return Response ──────────────────────────────────────────
        return {
            "complaint_id":      complaint_id,
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
        print("❌ FILE NOT FOUND:", exc)
        raise HTTPException(status_code=503, detail=str(exc))

    except Exception as exc:
        logger.exception("Unhandled error in /api/analyze: %s", exc)
        print("INTERNAL ERROR:", exc)
        raise HTTPException(status_code=500, detail="Internal server error")