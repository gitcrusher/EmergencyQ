"""
SQLAlchemy ORM models for the Emergency Complaint Analyzer.
Tables: complaints, severity_weights, feedback_log
"""

import uuid
import datetime

from sqlalchemy import Column, String, Float, DateTime, Text, Integer, JSON
from sqlalchemy.ext.declarative import declarative_base

Base = declarative_base()


class Complaint(Base):
    __tablename__ = "complaints"

    id             = Column(String, primary_key=True, default=lambda: str(uuid.uuid4()))
    text           = Column(Text, nullable=False)
    category       = Column(String(64))
    prediction_set = Column(JSON)           # list of label strings
    severity       = Column(String(32))
    urgency        = Column(String(32))
    confidence     = Column(Float)
    atomic_facts   = Column(JSON)           # dict: location, victim_count, hazard_type, environment
    created_at     = Column(DateTime, default=datetime.datetime.utcnow)

    def to_dict(self):
        return {
            "complaint_id":   self.id,
            "text":           self.text,
            "category":       self.category,
            "prediction_set": self.prediction_set,
            "severity":       self.severity,
            "urgency":        self.urgency,
            "confidence":     self.confidence,
            "atomic_facts":   self.atomic_facts,
            "created_at":     self.created_at.isoformat() if self.created_at else None,
        }


class SeverityWeight(Base):
    __tablename__ = "severity_weights"

    keyword    = Column(String(128), primary_key=True)
    score      = Column(Float, nullable=False)
    updated_at = Column(DateTime, default=datetime.datetime.utcnow,
                        onupdate=datetime.datetime.utcnow)


class FeedbackLog(Base):
    __tablename__ = "feedback_log"

    id           = Column(Integer, primary_key=True, autoincrement=True)
    complaint_id = Column(String, nullable=False)
    predicted    = Column(String(32))
    actual       = Column(String(32))
    notes        = Column(Text)
    created_at   = Column(DateTime, default=datetime.datetime.utcnow)