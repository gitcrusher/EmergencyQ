"""
Atomic Fact Decomposer  —  Novelty ①
======================================
Extracts four semantic dimensions from a raw complaint text using
spaCy NER + rule-based keyword scanning.

decompose(text) → dict with keys:
    location      — "near Gate 3", "Station Road", …
    victim_count  — "one person", "a family", …
    hazard_type   — "fire smoke", "trapped", …
    environment   — "inside building", "road", …

The extracted facts are used to:
  1. Enrich the DistilBERT input prefix
  2. Return structured metadata in the API response
"""

from __future__ import annotations

import logging
import functools

import spacy

logger = logging.getLogger(__name__)

# ── Keyword lists ─────────────────────────────────────────────────────────────

HAZARD_KEYWORDS = {
    "fire", "smoke", "flood", "flooding", "water", "bleeding", "unconscious",
    "trapped", "collapsed", "explosion", "crash", "crash", "collision",
    "chemical", "gas", "electrocution", "drowning", "choking", "burn",
    "burns", "injured", "injury", "dead", "death", "critical", "falling",
    "fell", "accident",
}

LOCATION_PREPOSITIONS = {
    "near", "at", "inside", "outside", "along", "on", "beside",
    "behind", "under", "over", "adjacent", "between",
}

ENVIRONMENT_NOUNS = {
    "road", "highway", "bridge", "building", "house", "hospital",
    "school", "station", "airport", "market", "mall", "river",
    "canal", "drain", "area", "zone", "public", "field", "construction",
    "site", "factory", "office", "flat", "floor", "basement", "terrace",
}


@functools.lru_cache(maxsize=1)
def _load_nlp():
    """Load spaCy model once; cached for the process lifetime."""
    try:
        return spacy.load("en_core_web_sm")
    except OSError:
        logger.warning(
            "spaCy model 'en_core_web_sm' not found. "
            "Run: python -m spacy download en_core_web_sm"
        )
        # Return blank English model as fallback (no NER, rule-based only)
        return spacy.blank("en")


def decompose(text: str) -> dict[str, str]:
    """
    Decompose *text* into four atomic emergency facts.

    Parameters
    ----------
    text : str  Raw complaint text (any case).

    Returns
    -------
    dict with keys: location, victim_count, hazard_type, environment.
    Values are strings (empty string if not found).
    """
    nlp = _load_nlp()
    doc = nlp(text.lower())

    facts: dict[str, list[str]] = {
        "location":     [],
        "victim_count": [],
        "hazard_type":  [],
        "environment":  [],
    }

    # ── Named Entity pass ────────────────────────────────────────────────────
    for ent in doc.ents:
        if ent.label_ in ("GPE", "LOC", "FAC"):
            facts["location"].append(ent.text)
        elif ent.label_ == "CARDINAL":
            facts["victim_count"].append(ent.text)
        elif ent.label_ == "PERSON":
            facts["victim_count"].append(ent.text)

    # ── Token keyword pass ───────────────────────────────────────────────────
    for token in doc:
        lemma = token.lemma_
        text_tok = token.text

        if text_tok in HAZARD_KEYWORDS or lemma in HAZARD_KEYWORDS:
            facts["hazard_type"].append(text_tok)

        if text_tok in LOCATION_PREPOSITIONS:
            # Grab the noun phrase that follows the preposition
            chunk_text = _next_noun_phrase(token)
            if chunk_text:
                facts["location"].append(chunk_text)

        if text_tok in ENVIRONMENT_NOUNS or lemma in ENVIRONMENT_NOUNS:
            facts["environment"].append(text_tok)

    # ── Deduplicate and join ─────────────────────────────────────────────────
    result = {k: " ".join(dict.fromkeys(v)).strip() for k, v in facts.items()}

    logger.debug("atomic facts: %s", result)
    return result


def _next_noun_phrase(token) -> str:
    """
    Return the text of the first noun chunk that starts right after *token*.
    Falls back to the raw head noun of the token's subtree.
    """
    for chunk in token.doc.noun_chunks:
        if chunk.start > token.i:
            return chunk.text
    # Fallback: just take the next token if it's a noun
    if token.i + 1 < len(token.doc):
        nxt = token.doc[token.i + 1]
        if nxt.pos_ in ("NOUN", "PROPN"):
            return nxt.text
    return ""


def build_enriched_prefix(facts: dict[str, str]) -> str:
    """
    Build a natural-language prefix from atomic facts to prepend to the
    DistilBERT input, improving classification on ambiguous complaints.

    Example output:
        "Location: station road. Hazard: flood water. Victims: one child. "
    """
    parts = []
    if facts.get("location"):
        parts.append(f"Location: {facts['location']}.")
    if facts.get("hazard_type"):
        parts.append(f"Hazard: {facts['hazard_type']}.")
    if facts.get("victim_count"):
        parts.append(f"Victims: {facts['victim_count']}.")
    if facts.get("environment"):
        parts.append(f"Environment: {facts['environment']}.")
    return " ".join(parts) + " " if parts else ""