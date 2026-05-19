"""
FastAPI application entry point for the Emergency Complaint Analyzer.
"""

from __future__ import annotations

import logging
import os
from contextlib import asynccontextmanager

print("🔥 IMPORT STEP 1")

from dotenv import load_dotenv

print("🔥 IMPORT STEP 2")

from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware

print("🔥 IMPORT STEP 3")

from prometheus_fastapi_instrumentator import Instrumentator

print("🔥 IMPORT STEP 4")

# Load environment variables
load_dotenv()

print("🔥 IMPORT STEP 5")

# ─────────────────────────────────────────────────────────────
# Internal Imports (DEBUG EACH)
# ─────────────────────────────────────────────────────────────

print("📦 Importing DB")
from app.database.db import init_db

print("📦 Importing Loader")
from app.model.loader import load_model

print("📦 Importing Analyze Route")
from app.routes.analyze import router as analyze_router

print("📦 Importing Feedback Route")
from app.routes.feedback import router as feedback_router

print("✅ ALL IMPORTS SUCCESSFUL")

# ─────────────────────────────────────────────────────────────
# Logging
# ─────────────────────────────────────────────────────────────

logging.basicConfig(
    level=logging.INFO,
    format="%(asctime)s | %(levelname)s | %(name)s | %(message)s",
)

logger = logging.getLogger(__name__)

# ─────────────────────────────────────────────────────────────
# Lifespan Events
# ─────────────────────────────────────────────────────────────

@asynccontextmanager
async def lifespan(app: FastAPI):

    print("🚀 APP STARTUP INIT")

    logger.info("=== Emergency Analyzer startup ===")

    # ───────────────── DB ─────────────────
    print("🔥 STEP 1 — Initializing Database")

    try:
        init_db()
        print("✅ Database Initialized")
    except Exception as e:
        print("❌ DATABASE ERROR:", e)
        raise e

    # ───────────────── MODEL ──────────────
    print("🔥 STEP 2 — Loading DistilBERT Model")

    try:
        load_model()
        print("✅ Model Loaded")
    except Exception as e:
        print("❌ MODEL LOADING ERROR:", e)
        raise e

    logger.info("DistilBERT model ready.")

    print("🚀 FastAPI Startup Complete")

    yield

    logger.info("=== Emergency Analyzer shutdown ===")


# ─────────────────────────────────────────────────────────────
# FastAPI App
# ─────────────────────────────────────────────────────────────

print("🔥 Creating FastAPI App")

app = FastAPI(
    title="Emergency Complaint Analyzer API",
    description=(
        "AI-powered emergency triage with Atomic Fact Decomposition, "
        "Conformal Prediction Sets, Temporal-Decayed Retrieval, "
        "and Adaptive Severity Feedback."
    ),
    version="2.0.0",
    lifespan=lifespan,
)

# ─────────────────────────────────────────────────────────────
# CORS
# ─────────────────────────────────────────────────────────────

print("🔥 Setting up CORS")

ALLOWED_ORIGINS = os.environ.get(
    "ALLOWED_ORIGINS",
    "http://localhost:5173,http://localhost:3000",
).split(",")

app.add_middleware(
    CORSMiddleware,
    allow_origins=ALLOWED_ORIGINS,
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

# ─────────────────────────────────────────────────────────────
# Routes
# ─────────────────────────────────────────────────────────────

print("🔥 Registering Routes")

app.include_router(analyze_router)
app.include_router(feedback_router)

# ─────────────────────────────────────────────────────────────
# Root Route
# ─────────────────────────────────────────────────────────────

@app.get("/")
async def root():
    return {
        "message": "Emergency Complaint Analyzer API Running"
    }

# ─────────────────────────────────────────────────────────────
# Health Route
# ─────────────────────────────────────────────────────────────

@app.get("/api/health", tags=["health"])
async def health_check():

    return {
        "status": "ok",
        "model": "loaded",
        "version": "2.0.0"
    }

# ─────────────────────────────────────────────────────────────
# Prometheus Metrics
# ─────────────────────────────────────────────────────────────

print("🔥 Setting up Prometheus")

Instrumentator().instrument(app).expose(app)

print("✅ MAIN.PY FULLY LOADED")