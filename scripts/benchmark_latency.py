"""
scripts/benchmark_latency.py
============================
Measures real ChromaDB retrieval latency so you can put ACTUAL numbers on your CV.

Measures two things:
  1. Cold start latency  — first query (model loading + ChromaDB connect + search)
  2. Warm latency        — subsequent queries (lru_cache active, just vector search)

This is where the latency improvement comes from:
  - lru_cache on _get_embed_model() and _get_collection() in retrieval.py
  - After first call, model is in memory and ChromaDB handle is cached
  - Only the actual vector search runs on each warm query

Usage:
    cd D:\\nlp project
    python scripts/benchmark_latency.py

Requirements:
    - ChromaDB must be populated first: python scripts/populate_vectordb.py
"""

from __future__ import annotations

import sys
import time
import statistics
from pathlib import Path

# Add backend to path so we can import from app.*
sys.path.insert(0, str(Path(__file__).parent.parent / "backend"))

from dotenv import load_dotenv
load_dotenv()

# ─────────────────────────────────────────────────────────────────────────────
# TEST QUERIES — realistic emergency complaints
# ─────────────────────────────────────────────────────────────────────────────

TEST_QUERIES = [
    "There is a fire in the building on MG Road, people are trapped",
    "Water level is rising rapidly, we are stuck on the rooftop",
    "Person collapsed on street near hospital, not breathing",
    "Car accident on highway, multiple injured, need ambulance",
    "Flood water entering homes in sector 5, need rescue boats",
    "Old man having chest pain, needs immediate medical help",
    "Building on fire, smoke everywhere, children inside",
    "Road blocked due to accident, injured people need help",
    "Woman is unconscious after fall, please send help",
    "River overflowing, village at risk of flooding",
]

N_WARM_RUNS = 20   # number of warm queries to average

# ─────────────────────────────────────────────────────────────────────────────
# BENCHMARK
# ─────────────────────────────────────────────────────────────────────────────

def measure_latency(query: str) -> float:
    """Returns retrieval latency in milliseconds for one query."""
    from app.vectordb.retrieval import retrieve_similar

    t0 = time.perf_counter()
    results = retrieve_similar(query, top_k=5)
    t1 = time.perf_counter()

    return (t1 - t0) * 1000   # convert to ms


def run_benchmark():
    print("=" * 65)
    print("  ChromaDB RAG Pipeline — Latency Benchmark")
    print("=" * 65)

    # ── COLD START ────────────────────────────────────────────────────────────
    # First query: loads sentence-transformer model + connects ChromaDB
    # This simulates a fresh server startup
    print("\n[1/3] Measuring COLD START latency (first query, no cache)...")
    print("      (Loading sentence-transformer model + ChromaDB connection)")

    cold_ms = measure_latency(TEST_QUERIES[0])
    print(f"      Cold start latency : {cold_ms:.1f} ms")

    # ── WARM LATENCY ──────────────────────────────────────────────────────────
    # Subsequent queries: lru_cache returns cached model + collection
    # Only the vector search itself runs
    print(f"\n[2/3] Measuring WARM latency over {N_WARM_RUNS} queries (cached)...")

    warm_times = []
    for i in range(N_WARM_RUNS):
        query = TEST_QUERIES[i % len(TEST_QUERIES)]
        ms = measure_latency(query)
        warm_times.append(ms)
        print(f"      Query {i+1:>2}: {ms:>7.1f} ms  —  \"{query[:45]}...\"" if len(query) > 45
              else f"      Query {i+1:>2}: {ms:>7.1f} ms  —  \"{query}\"")

    warm_avg    = statistics.mean(warm_times)
    warm_median = statistics.median(warm_times)
    warm_min    = min(warm_times)
    warm_max    = max(warm_times)
    warm_stdev  = statistics.stdev(warm_times)

    # ── RESULTS ───────────────────────────────────────────────────────────────
    improvement_pct = ((cold_ms - warm_avg) / cold_ms) * 100

    print("\n" + "=" * 65)
    print("  RESULTS")
    print("=" * 65)
    print(f"\n  Cold start (1st query)     : {cold_ms:>8.1f} ms")
    print(f"\n  Warm queries ({N_WARM_RUNS} runs):")
    print(f"    Average latency          : {warm_avg:>8.1f} ms")
    print(f"    Median latency           : {warm_median:>8.1f} ms")
    print(f"    Min latency              : {warm_min:>8.1f} ms")
    print(f"    Max latency              : {warm_max:>8.1f} ms")
    print(f"    Std deviation            : {warm_stdev:>8.1f} ms")
    print(f"\n  Improvement (cold → warm)  : {improvement_pct:>7.1f}%")
    print(f"  Latency reduced by         : {cold_ms - warm_avg:>8.1f} ms")

    print("\n" + "=" * 65)
    print("  CV-READY NUMBERS")
    print("=" * 65)
    print(f"""
  Use these in your CV/report (all real, measured numbers):

  \"Optimized ChromaDB HNSW vector retrieval latency from
   ~{cold_ms:.0f}ms (cold start) to ~{warm_avg:.0f}ms (cached warm queries),
   a {improvement_pct:.0f}% reduction, by implementing lru_cache on
   sentence-transformer model loading and ChromaDB collection
   handles — eliminating repeated I/O on every inference request.\"
""")

    # ── PER-QUERY BREAKDOWN ───────────────────────────────────────────────────
    print("=" * 65)
    print("  WHAT EACH PHASE COSTS (approx breakdown)")
    print("=" * 65)
    print(f"""
  Cold start = model load + ChromaDB connect + embedding + search
             ≈ {cold_ms:.0f} ms total

  Warm query = embedding + HNSW search only (cache handles rest)
             ≈ {warm_avg:.0f} ms total

  The lru_cache in retrieval.py removes model loading and
  ChromaDB client creation from every request after the first.
  That's the source of the {improvement_pct:.0f}% improvement.
""")


if __name__ == "__main__":
    run_benchmark()
