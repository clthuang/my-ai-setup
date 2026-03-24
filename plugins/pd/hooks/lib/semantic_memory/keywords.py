"""Tiered keyword extraction for semantic memory entries.

Tier 1: Regex/heuristic extraction (zero-cost, no external calls)
Tier 2: Gemini LLM fallback (only when Tier 1 produces < 3 keywords)
"""
from __future__ import annotations

import json
import logging
import os
import re
from typing import Any

logger = logging.getLogger(__name__)

# ---------------------------------------------------------------------------
# Constants
# ---------------------------------------------------------------------------

_KEYWORD_RE = re.compile(r"^[a-z0-9][a-z0-9-]*$")

_STOPWORDS = frozenset([
    "code", "development", "software", "system", "application",
    "implementation", "feature", "project", "function", "method",
    "file", "data", "error", "bug", "fix", "update", "change",
])

KEYWORD_PROMPT = (
    "Extract 3-10 keyword labels from this knowledge bank entry.\n"
    "\n"
    "Title: {name}\n"
    "Content: {description}\n"
    "Reasoning: {reasoning}\n"
    "Category: {category}\n"
    "\n"
    'Return ONLY a JSON array of lowercase keyword strings. '
    'Example: ["fts5", "sqlite", "content-hash", "parser-error"]\n'
    "\n"
    "Rules:\n"
    "- Use specific technical terms (tool names, patterns, file types, techniques)\n"
    "- 1-3 words per keyword, lowercase, hyphenated if multi-word\n"
    "- EXCLUDE generic words: code, development, software, system, application, "
    "implementation, feature, project, function, method, file, data, error, bug, fix, update, change\n"
    "- Minimum 3, maximum 10 keywords"
)

# Pattern for consecutive capitalized words (2+) in original text.
# Requires 2+ lowercase chars after initial capital to skip short words
# like "The", "Our", "An" that happen to be capitalized at sentence start.
_CAPITALIZED_SEQ_RE = re.compile(r"\b([A-Z][a-z]{2,}(?:\s+[A-Z][a-z]{2,})+)\b")

# ---------------------------------------------------------------------------
# Tier 1: Regex/heuristic extraction
# ---------------------------------------------------------------------------


def _tier1_extract(text: str) -> list[str]:
    """Regex/heuristic keyword extraction.

    Tokenize, filter by _KEYWORD_RE, remove stopwords, extract multi-word
    hyphenated terms, and join consecutive capitalized word sequences.
    Returns 0-10 deduplicated lowercase keyword strings.
    """
    keywords: list[str] = []
    seen: set[str] = set()

    def _add(kw: str) -> None:
        if kw not in seen and kw not in _STOPWORDS and _KEYWORD_RE.match(kw):
            seen.add(kw)
            keywords.append(kw)

    lowered = text.lower()

    # Extract hyphenated multi-word terms FIRST (before tokenizer splits them)
    hyphenated = re.findall(r"[a-z0-9]+-[a-z0-9]+(?:-[a-z0-9]+)*", lowered)
    for term in hyphenated:
        _add(term)

    # Join consecutive capitalized word sequences from original text
    for match in _CAPITALIZED_SEQ_RE.finditer(text):
        phrase = match.group(1)
        # Convert "Entity Registry" -> "entity-registry"
        hyphenated_term = "-".join(w.lower() for w in phrase.split())
        _add(hyphenated_term)

    # Tokenize lowercased text -- split on whitespace and non-word chars
    tokens = re.split(r"[\s\W]+", lowered)
    for tok in tokens:
        if tok and _KEYWORD_RE.match(tok) and tok not in _STOPWORDS:
            _add(tok)

    return keywords[:10]


# ---------------------------------------------------------------------------
# Tier 2: LLM-based extraction via Gemini
# ---------------------------------------------------------------------------

# Lazy-initialized Gemini client
_genai_client: Any = None


def _get_genai_client() -> Any:
    """Lazy-initialize and return the google.genai Client."""
    global _genai_client
    if _genai_client is not None:
        return _genai_client

    try:
        from google import genai  # noqa: F811
    except ImportError:
        logger.warning("google-genai not installed; Tier 2 keywords unavailable")
        return None

    api_key = os.environ.get("GEMINI_API_KEY")
    if not api_key:
        logger.warning("GEMINI_API_KEY not set; Tier 2 keywords unavailable")
        return None

    _genai_client = genai.Client(api_key=api_key)
    return _genai_client


def _strip_code_fences(text: str) -> str:
    """Strip markdown code fences (```json ... ```) from LLM response."""
    text = text.strip()
    # Remove opening fence like ```json or ```
    text = re.sub(r"^```(?:json)?\s*\n?", "", text)
    # Remove closing fence
    text = re.sub(r"\n?```\s*$", "", text)
    return text.strip()


def _tier2_extract(
    name: str,
    description: str,
    reasoning: str,
    category: str,
) -> list[str]:
    """LLM-based keyword extraction via Gemini generateContent.

    Returns validated keyword list, or [] on any failure.
    """
    try:
        client = _get_genai_client()
        if client is None:
            return []

        prompt = KEYWORD_PROMPT.format(
            name=name,
            description=description,
            reasoning=reasoning,
            category=category,
        )

        response = client.models.generate_content(
            model="gemini-2.0-flash",
            contents=prompt,
        )

        raw_text = response.text
        cleaned = _strip_code_fences(raw_text)
        parsed = json.loads(cleaned)

        if not isinstance(parsed, list):
            logger.warning("Tier 2: expected JSON array, got %s", type(parsed).__name__)
            return []

        # Validate each keyword
        validated: list[str] = []
        for kw in parsed:
            if not isinstance(kw, str):
                continue
            kw = kw.lower().strip()
            if _KEYWORD_RE.match(kw) and kw not in _STOPWORDS:
                validated.append(kw)

        return validated[:10]

    except Exception:
        logger.debug("Tier 2 keyword extraction failed", exc_info=True)
        return []


# ---------------------------------------------------------------------------
# Public API
# ---------------------------------------------------------------------------


def extract_keywords(
    name: str,
    description: str,
    reasoning: str,
    category: str,
    config: dict | None = None,
) -> list[str]:
    """Extract 3-10 keywords from entry fields using tiered approach.

    Tier 1: Regex/heuristic (zero-cost)
    Tier 2: Gemini LLM (only if Tier 1 < 3 keywords and GEMINI_API_KEY available)

    Returns list of lowercase keyword strings. May return fewer than 3 if both
    tiers fail.
    """
    # Concatenate fields for Tier 1
    combined_text = f"{name} {description} {reasoning}"
    tier1_results = _tier1_extract(combined_text)

    if len(tier1_results) >= 3:
        return tier1_results

    # Tier 1 insufficient -- try Tier 2
    tier2_results = _tier2_extract(name, description, reasoning, category)

    # Combine, deduplicate, limit to 10
    seen = set(tier1_results)
    combined = list(tier1_results)
    for kw in tier2_results:
        if kw not in seen:
            seen.add(kw)
            combined.append(kw)

    return combined[:10]
