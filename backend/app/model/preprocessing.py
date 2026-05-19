"""
app/model/preprocessing.py
===========================
Text cleaning and normalization pipeline applied to every complaint
BEFORE it reaches the DistilBERT tokenizer or the ChromaDB embedder.

Why this matters
----------------
Raw citizen complaints often contain:
  • URLs, phone numbers, hashtags  → noise for the classifier
  • Repeated punctuation ("!!!!!") → misleads tokenizer attention
  • All-caps words ("FIRE FIRE")   → DistilBERT is case-insensitive
    (distilbert-base-UNCASED) but normalizing avoids tokenizer edge-cases
  • Leading/trailing whitespace    → wastes max_length budget

Without this module the model still works (it tolerates noise) but:
  • Tokenization budget is wasted on junk tokens
  • Embedding quality for ChromaDB retrieval is slightly worse
  • Identical complaints with minor formatting differences produce
    different embeddings → near-duplicate retrieval misses

With this module:
  • Clean, normalized text → better token utilization
  • Consistent embeddings for semantically identical complaints
  • Safer downstream handling (no injection via URLs/scripts)

Usage:
    from app.model.preprocessing import clean_complaint, preprocess_for_model

    raw = "  FIRE!! Building on fire near Station Rd. Call 9988776655 NOW!!  "
    cleaned = clean_complaint(raw)
    # → "fire building on fire near station rd"

    # Full pipeline including fact-enriched prefix:
    final_text = preprocess_for_model(raw, enriched_prefix="Location: station rd. Hazard: fire. ")
"""

from __future__ import annotations

import logging
import re
import unicodedata

logger = logging.getLogger(__name__)

# ── Regex patterns (compiled once at import time) ─────────────────────────────

_RE_URL        = re.compile(r"https?://\S+|www\.\S+", re.IGNORECASE)
_RE_PHONE      = re.compile(r"\b\d[\d\s\-().]{7,}\d\b")          # 8+ digit sequences
_RE_HASHTAG    = re.compile(r"#\w+")
_RE_MENTION    = re.compile(r"@\w+")
_RE_EMOJIS     = re.compile(                                       # common emoji ranges
    "["
    "\U0001F600-\U0001F64F"   # emoticons
    "\U0001F300-\U0001F5FF"   # symbols & pictographs
    "\U0001F680-\U0001F6FF"   # transport & map
    "\U0001F1E0-\U0001F1FF"   # flags
    "\U00002702-\U000027B0"
    "\U000024C2-\U0001F251"
    "]+",
    flags=re.UNICODE,
)
_RE_REPEATED_PUNCT = re.compile(r"([!?,;.]){2,}")                 # !!!  →  !
_RE_MULTI_SPACE    = re.compile(r"\s{2,}")                        # collapse whitespace
_RE_NON_ASCII_ALPHA = re.compile(r"[^\x00-\x7F]+")               # strip non-ASCII


# ── Public API ────────────────────────────────────────────────────────────────

def clean_complaint(text: str, lowercase: bool = True) -> str:
    """
    Apply the full cleaning pipeline to a raw complaint string.

    Steps (in order):
      1. Unicode NFKC normalization  (handles accented chars, fancy quotes)
      2. Strip URLs
      3. Strip phone numbers
      4. Strip hashtags and @mentions
      5. Strip emojis
      6. Collapse repeated punctuation  ("!!!" → "!")
      7. Remove non-ASCII characters
      8. Optional lowercase
      9. Collapse multiple spaces
     10. Strip leading/trailing whitespace

    Parameters
    ----------
    text      : str   Raw input complaint text.
    lowercase : bool  Whether to lowercase (should match DistilBERT variant —
                      True for distilbert-base-UNCASED, False for CASED).

    Returns
    -------
    str  Cleaned complaint text. Never empty — falls back to original text
         stripped of whitespace if cleaning produces an empty string.
    """
    if not isinstance(text, str):
        text = str(text)

    original = text

    # Step 1 — Unicode normalization
    text = unicodedata.normalize("NFKC", text)

    # Steps 2-5 — Remove structured noise
    text = _RE_URL.sub(" ", text)
    text = _RE_PHONE.sub(" ", text)
    text = _RE_HASHTAG.sub(" ", text)
    text = _RE_MENTION.sub(" ", text)
    text = _RE_EMOJIS.sub(" ", text)

    # Step 6 — Normalize repeated punctuation
    text = _RE_REPEATED_PUNCT.sub(r"\1", text)

    # Step 7 — Drop non-ASCII (e.g. Unicode bullets, RTL marks)
    text = _RE_NON_ASCII_ALPHA.sub(" ", text)

    # Step 8 — Lowercase
    if lowercase:
        text = text.lower()

    # Steps 9-10 — Final whitespace cleanup
    text = _RE_MULTI_SPACE.sub(" ", text).strip()

    # Fallback: if cleaning nuked everything, return the stripped original
    if not text:
        logger.warning("Cleaning produced empty string; using stripped original.")
        text = original.strip()

    logger.debug("clean_complaint: '%s' → '%s'", original[:60], text[:60])
    return text


def preprocess_for_model(
    complaint_text: str,
    enriched_prefix: str = "",
    max_total_chars: int = 800,
    lowercase: bool = True,
) -> str:
    """
    Full pre-processing pipeline for DistilBERT input:

        raw complaint
            │
            ▼
        clean_complaint()  (noise removal, normalisation)
            │
            ▼
        truncate to max_total_chars
            │
            ▼
        prepend enriched_prefix (atomic fact prefix from decomposer)
            │
            ▼
        final string ready for tokenizer

    Parameters
    ----------
    complaint_text  : str  Raw complaint string.
    enriched_prefix : str  Optional atomic fact prefix from
                           decomposer.build_enriched_prefix().
    max_total_chars : int  Hard character limit BEFORE prefix is added.
                           DistilBERT max_length=128 tokens ≈ 500 chars;
                           800 gives headroom for the prefix without
                           exceeding the token budget.
    lowercase       : bool Passed through to clean_complaint().

    Returns
    -------
    str  Final text string ready for DistilBertTokenizer.
    """
    cleaned = clean_complaint(complaint_text, lowercase=lowercase)

    # Truncate complaint body to avoid exceeding token budget
    if len(cleaned) > max_total_chars:
        logger.debug(
            "Complaint truncated: %d → %d chars", len(cleaned), max_total_chars
        )
        cleaned = cleaned[:max_total_chars].rsplit(" ", 1)[0]  # word-boundary truncate

    # Prepend atomic fact prefix (already clean — produced by build_enriched_prefix)
    final = (enriched_prefix + cleaned).strip() if enriched_prefix else cleaned

    return final


def truncate_to_token_budget(
    text: str,
    max_length: int = 128,
    avg_chars_per_token: float = 4.2,
) -> str:
    """
    Fast heuristic truncation based on character count before calling
    the tokenizer. Avoids slow tokenizer calls in bulk preprocessing.

    Parameters
    ----------
    text              : str   Input text (should already be cleaned).
    max_length        : int   Target max token count.
    avg_chars_per_token: float Empirical ratio for English BERT vocabulary.

    Returns
    -------
    str  Text that is very likely to fit within max_length tokens.
    """
    char_limit = int(max_length * avg_chars_per_token)
    if len(text) <= char_limit:
        return text
    return text[:char_limit].rsplit(" ", 1)[0]