"""
POST /api/feedback  —  Responder severity feedback endpoint (Novelty ④).

Accepts the responder's observed severity, compares to the model's
prediction, and triggers adaptive weight updates when the model
under-predicted.
"""

from __future__ import annotations

import logging

from fastapi import APIRouter, HTTPException

from app.schemas.feedback_schema import FeedbackRequest, FeedbackResponse
from app.utils.adaptive_weights import update_weights
from app.database.db import get_db
from app.database.models import Complaint

logger = logging.getLogger(__name__)

router = APIRouter(prefix="/api", tags=["feedback"])


@router.post("/feedback", response_model=FeedbackResponse)
async def submit_feedback(req: FeedbackRequest):
    """
    Receive responder feedback on actual vs predicted severity.
    If actual > predicted, keyword weights in the DB are updated.
    """
    # Fetch original complaint text from DB
    with get_db() as db:
        record = db.query(Complaint).filter(Complaint.id == req.complaint_id).first()

    if record is None:
        raise HTTPException(
            status_code=404,
            detail=f"Complaint '{req.complaint_id}' not found.",
        )

    updated = update_weights(
        complaint_id=req.complaint_id,
        complaint_text=record.text,
        predicted=req.predicted_severity,
        actual=req.actual_severity,
        notes=req.responder_notes,
    )

    return FeedbackResponse(
        status="ok",
        updated=updated,
        message=(
            "Keyword weights updated based on responder feedback."
            if updated
            else "Prediction was correct or over-estimated — no weight update needed."
        ),
    )