"""
scripts/populate_vectordb.py
============================
Embed all historical incidents and upsert them into ChromaDB.

Input:  dataset/processed/historical_incidents.csv
        Required columns: text, label, severity, timestamp (ISO-8601)

Output: Populated ChromaDB collection at CHROMA_PERSIST_DIR

Usage:
    python scripts/populate_vectordb.py [--csv path/to/file.csv]

Safe to re-run — existing IDs are overwritten with fresh embeddings.
"""

from __future__ import annotations

import argparse
import logging
import sys
import uuid
from pathlib import Path

sys.path.insert(0, str(Path(__file__).parent.parent / "backend"))

from dotenv import load_dotenv
load_dotenv()

import os
import pandas as pd
import chromadb
from sentence_transformers import SentenceTransformer
from tqdm import tqdm

logging.basicConfig(level=logging.INFO, format="%(asctime)s | %(levelname)s | %(message)s")
logger = logging.getLogger(__name__)

CHROMA_DIR      = os.environ.get("CHROMA_PERSIST_DIR", "./backend/app/vectordb/chroma_db")
EMBED_MODEL     = "all-MiniLM-L6-v2"
COLLECTION_NAME = "incidents"
BATCH_SIZE      = 128
DEFAULT_CSV     = Path("dataset/processed/historical_incidents.csv")


def main(csv_path: Path):
    if not csv_path.exists():
        logger.error("CSV not found at %s", csv_path)
        sys.exit(1)

    logger.info("Loading incidents from %s", csv_path)
    df = pd.read_csv(csv_path)

    required_cols = {"text", "label", "severity", "timestamp"}
    missing = required_cols - set(df.columns)
    if missing:
        logger.error("Missing columns: %s", missing)
        sys.exit(1)

    df = df.dropna(subset=["text"]).reset_index(drop=True)
    logger.info("%d incidents loaded after dropping NaN rows.", len(df))

    logger.info("Loading sentence-transformer: %s", EMBED_MODEL)
    model = SentenceTransformer(EMBED_MODEL)

    logger.info("Connecting to ChromaDB at %s", CHROMA_DIR)
    client = chromadb.PersistentClient(path=CHROMA_DIR)
    col    = client.get_or_create_collection(
        name=COLLECTION_NAME,
        metadata={"hnsw:space": "cosine"},
    )

    texts     = df["text"].tolist()
    labels    = df["label"].tolist()
    severities = df["severity"].tolist()
    timestamps = df["timestamp"].tolist()

    logger.info("Embedding %d incidents in batches of %d …", len(texts), BATCH_SIZE)
    all_embeddings = model.encode(
        texts,
        batch_size=BATCH_SIZE,
        show_progress_bar=True,
        normalize_embeddings=True,
    )

    # Upsert in batches to stay within ChromaDB's recommended chunk size
    for start in tqdm(range(0, len(texts), BATCH_SIZE), desc="Upserting"):
        end = min(start + BATCH_SIZE, len(texts))
        col.upsert(
            ids=[str(uuid.uuid4()) for _ in range(end - start)],
            documents=texts[start:end],
            embeddings=all_embeddings[start:end].tolist(),
            metadatas=[
                {
                    "label":     labels[i],
                    "severity":  severities[i],
                    "timestamp": str(timestamps[i]),
                }
                for i in range(start, end)
            ],
        )

    final_count = col.count()
    logger.info("ChromaDB collection '%s' now has %d incidents.", COLLECTION_NAME, final_count)


if __name__ == "__main__":
    parser = argparse.ArgumentParser()
    parser.add_argument("--csv", type=Path, default=DEFAULT_CSV)
    args = parser.parse_args()
    main(args.csv)