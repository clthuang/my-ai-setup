"""Read, write, validate, and build YAML frontmatter headers for markdown files."""
from __future__ import annotations

import logging
import os
import re
import tempfile
from datetime import datetime

logger = logging.getLogger("entity_registry.frontmatter")

# Field ordering for serialization (R5, TD-2)
FIELD_ORDER = (
    "entity_uuid",
    "entity_type_id",
    "artifact_type",
    "created_at",
    "feature_id",
    "feature_slug",
    "project_id",
    "phase",
    "updated_at",
)

# Required fields (R3)
REQUIRED_FIELDS = frozenset({
    "entity_uuid",
    "entity_type_id",
    "artifact_type",
    "created_at",
})

# Optional fields (R4)
OPTIONAL_FIELDS = frozenset({
    "feature_id",
    "feature_slug",
    "project_id",
    "phase",
    "updated_at",
})

# All allowed fields
ALLOWED_FIELDS = REQUIRED_FIELDS | OPTIONAL_FIELDS

# Allowed artifact types (R3)
ALLOWED_ARTIFACT_TYPES = frozenset({"spec", "design", "plan", "tasks", "retro", "prd"})

# UUID v4 regex — NO re.IGNORECASE; callers must .lower() before matching
_UUID_V4_RE = re.compile(
    r'^[0-9a-f]{8}-[0-9a-f]{4}-4[0-9a-f]{3}-[89ab][0-9a-f]{3}-[0-9a-f]{12}$'
)


# ---------------------------------------------------------------------------
# Internal helpers
# ---------------------------------------------------------------------------


def _parse_block(lines: list[str]) -> dict:
    """Parse lines between frontmatter delimiters into a key-value dict.

    Each line is split on the first ': ' (colon-space). The portion before
    must match ``[a-z_]+`` to be accepted as a key. Lines that don't match
    are silently ignored.
    """
    result: dict[str, str] = {}
    for line in lines:
        key, sep, value = line.partition(": ")
        if sep and re.fullmatch(r"[a-z_]+", key):
            result[key] = value
    return result


def _serialize_header(header: dict) -> str:
    """Serialize a header dict to a YAML frontmatter string with --- delimiters.

    Fields in FIELD_ORDER come first (in that order), then any remaining keys.
    """
    parts = ["---\n"]
    field_order_set = set(FIELD_ORDER)
    for field in FIELD_ORDER:
        if field in header:
            parts.append(f"{field}: {header[field]}\n")
    for key in header:
        if key not in field_order_set:
            parts.append(f"{key}: {header[key]}\n")
    parts.append("---\n")
    return "".join(parts)


# ---------------------------------------------------------------------------
# Public API
# ---------------------------------------------------------------------------


def validate_header(header: dict) -> list[str]:
    """Validate a header dict against the schema.

    Returns a list of validation error strings (empty list = valid).
    Does not short-circuit -- all errors are collected.
    """
    errors: list[str] = []

    # 1. Required fields present
    for field in REQUIRED_FIELDS:
        if field not in header:
            errors.append(f"Missing required field: {field}")

    # 2. UUID format (case-insensitive -- .lower() before matching)
    if "entity_uuid" in header:
        if not _UUID_V4_RE.match(header["entity_uuid"].lower()):
            errors.append(
                f"Invalid entity_uuid format: {header['entity_uuid']!r}"
            )

    # 3. Artifact type set membership
    if "artifact_type" in header:
        if header["artifact_type"] not in ALLOWED_ARTIFACT_TYPES:
            errors.append(
                f"Invalid artifact_type: {header['artifact_type']!r} "
                f"(allowed: {sorted(ALLOWED_ARTIFACT_TYPES)})"
            )

    # 4. created_at ISO 8601
    if "created_at" in header:
        try:
            datetime.fromisoformat(header["created_at"])
        except (ValueError, TypeError):
            errors.append(
                f"Invalid created_at (not ISO 8601): {header['created_at']!r}"
            )

    # 5. Unknown fields
    for key in header:
        if key not in ALLOWED_FIELDS:
            errors.append(f"Unknown field: {key!r}")

    return errors


def build_header(
    entity_uuid: str,
    entity_type_id: str,
    artifact_type: str,
    created_at: str,
    **optional_fields,
) -> dict:
    """Construct a validated header dict from required and optional fields.

    Raises ``ValueError`` if any input is invalid (including unknown kwargs).
    """
    header = {
        "entity_uuid": entity_uuid,
        "entity_type_id": entity_type_id,
        "artifact_type": artifact_type,
        "created_at": created_at,
    }
    header.update(optional_fields)

    errors = validate_header(header)
    if errors:
        raise ValueError(
            f"Invalid header: {'; '.join(errors)}"
        )

    return header


def read_frontmatter(filepath: str) -> dict | None:
    """Parse YAML frontmatter from a markdown file.

    Returns a dict of header fields, or ``None`` if no valid frontmatter
    block is found. Never raises exceptions -- errors are logged as warnings.
    """
    # Binary content guard: check for null bytes in first 8192 bytes
    try:
        with open(filepath, "rb") as bf:
            chunk = bf.read(8192)
            if b"\x00" in chunk:
                logger.warning("Binary content detected, skipping: %s", filepath)
                return None
    except FileNotFoundError:
        logger.warning("File not found: %s", filepath)
        return None

    # Text-mode line-by-line parsing
    with open(filepath, "r", encoding="utf-8") as f:
        first_line = f.readline()
        if not first_line:
            # Empty file
            return None

        if first_line.rstrip("\n") != "---":
            return None

        # Accumulate lines between opening and closing ---
        block_lines: list[str] = []
        for line in f:
            stripped = line.rstrip("\n")
            if stripped == "---":
                # Found closing delimiter -- parse what we have
                return _parse_block(block_lines)
            block_lines.append(stripped)

        # EOF without closing delimiter -- malformed
        logger.warning("Malformed frontmatter (no closing ---): %s", filepath)
        return None
