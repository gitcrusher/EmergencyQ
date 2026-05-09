"""
Pydantic v2 schemas for the /api/analyze endpoint.
"""

from pydantic import BaseModel, Field


class ComplaintRequest(BaseModel):
    complaint: str = Field(
        ...,
        min_length=10,
        max_length=2000,
        description="Free-text emergency complaint submitted by citizen.",
        examples=["Child trapped inside flooded house near Main Road"],
    )


class AtomicFacts(BaseModel):
    location:     str = ""
    victim_count: str = ""
    hazard_type:  str = ""
    environment:  str = ""


class SimilarIncident(BaseModel):
    text:           str
    date:           str
    label:          str
    severity:       str
    cosine_score:   float
    adjusted_score: float


class AnalyzeResponse(BaseModel):
    complaint_id:     str
    category:         str
    prediction_set:   list[str]
    confidence:       float
    severity:         str
    urgency:          str
    atomic_facts:     AtomicFacts
    similar_incidents: list[SimilarIncident]