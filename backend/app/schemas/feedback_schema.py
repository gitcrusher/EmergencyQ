"""
Pydantic v2 schema for the /api/feedback endpoint (Novelty ④).
"""

from typing import Optional
from pydantic import BaseModel, Field

VALID_SEVERITIES = {"Critical", "High", "Moderate", "Low"}


class FeedbackRequest(BaseModel):
    complaint_id:       str = Field(..., description="UUID returned by /api/analyze")
    predicted_severity: str = Field(..., description="Severity the model predicted")
    actual_severity:    str = Field(..., description="Actual severity observed by responder")
    responder_notes:    Optional[str] = Field(None, max_length=1000)

    model_config = {"json_schema_extra": {
        "example": {
            "complaint_id":       "uuid-v4",
            "predicted_severity": "Moderate",
            "actual_severity":    "Critical",
            "responder_notes":    "Building was already partially collapsed on arrival",
        }
    }}


class FeedbackResponse(BaseModel):
    status:  str
    updated: bool
    message: str