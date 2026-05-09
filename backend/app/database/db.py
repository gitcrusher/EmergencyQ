"""
Database engine + session factory.
Uses DATABASE_URL from environment (set in .env).
Call init_db() once at application startup to create all tables.
"""

import os
from contextlib import contextmanager

from sqlalchemy import create_engine
from sqlalchemy.orm import sessionmaker, Session

from app.database.models import Base

DATABASE_URL: str = os.environ["DATABASE_URL"]

engine = create_engine(
    DATABASE_URL,
    pool_pre_ping=True,          # drop stale connections before using
    pool_size=10,
    max_overflow=20,
    echo=False,                  # set True only for query-level debug
)

SessionLocal = sessionmaker(autocommit=False, autoflush=False, bind=engine)


def init_db() -> None:
    """Create all tables that do not exist yet. Safe to call multiple times."""
    Base.metadata.create_all(bind=engine)


@contextmanager
def get_db() -> Session:
    """Context-manager session — always commits or rolls back."""
    db = SessionLocal()
    try:
        yield db
        db.commit()
    except Exception:
        db.rollback()
        raise
    finally:
        db.close()