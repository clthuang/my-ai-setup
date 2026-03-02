"""Bidirectional sync between frontmatter headers and entity DB.

Provides drift detection, DB-to-file stamping, file-to-DB ingestion,
bulk backfill, and bulk scan operations.
"""
from __future__ import annotations

import json
import logging
import os
from dataclasses import dataclass

from entity_registry.database import EntityDatabase
from entity_registry.frontmatter import (
    FrontmatterUUIDMismatch,
    build_header,
    read_frontmatter,
    validate_header,
    write_frontmatter,
)
from entity_registry.frontmatter_inject import (
    ARTIFACT_BASENAME_MAP,
    ARTIFACT_PHASE_MAP,
    _parse_feature_type_id,
)

logger = logging.getLogger("entity_registry.frontmatter_sync")

# ---------------------------------------------------------------------------
# Constants
# ---------------------------------------------------------------------------

# Maps file frontmatter field names to DB column names for drift comparison.
# Only these fields are compared; all others are informational (spec R6).
COMPARABLE_FIELD_MAP: dict[str, str] = {
    "entity_uuid": "uuid",
    "entity_type_id": "type_id",
}

# ---------------------------------------------------------------------------
# Dataclasses
# ---------------------------------------------------------------------------


@dataclass
class FieldMismatch:
    """Single-field comparison result between file and DB."""

    field: str
    file_value: str | None
    db_value: str | None


@dataclass
class DriftReport:
    """Full drift assessment for a single file."""

    filepath: str
    type_id: str | None
    status: str  # "in_sync" | "file_only" | "db_only" | "diverged" | "no_header" | "error"
    file_fields: dict | None
    db_fields: dict | None
    mismatches: list[FieldMismatch]


@dataclass
class StampResult:
    """Outcome of a DB-to-file stamp operation."""

    filepath: str
    action: str  # "created" | "updated" | "skipped" | "error"
    message: str


@dataclass
class IngestResult:
    """Outcome of a file-to-DB ingest operation."""

    filepath: str
    action: str  # "updated" | "skipped" | "error"
    message: str


# ---------------------------------------------------------------------------
# Internal helpers
# ---------------------------------------------------------------------------


def _derive_optional_fields(entity: dict, artifact_type: str) -> dict:
    """Derive optional frontmatter fields from an entity record.

    Extracts feature_id/feature_slug (feature entities only), project_id
    (from metadata JSON or parent_type_id fallback), and phase (from
    artifact_type mapping).

    Parameters
    ----------
    entity:
        Entity dict as returned by ``EntityDatabase.get_entity()``.
    artifact_type:
        The artifact type string (e.g. "spec", "design").

    Returns
    -------
    dict
        Optional kwargs suitable for ``build_header(**kwargs)``.
    """
    kwargs: dict[str, str] = {}
    entity_type, _, _ = entity["type_id"].partition(":")

    # feature_id + feature_slug (feature entities only)
    if entity_type == "feature":
        feat_id, feat_slug = _parse_feature_type_id(entity["type_id"])
        if feat_id:
            kwargs["feature_id"] = feat_id
        if feat_slug is not None:
            kwargs["feature_slug"] = feat_slug

    # project_id: metadata JSON first, then parent_type_id fallback
    project_id = None
    if entity.get("metadata"):
        try:
            meta = json.loads(entity["metadata"])
            project_id = meta.get("project_id") or None
        except (json.JSONDecodeError, TypeError):
            pass
    if project_id is None and entity.get("parent_type_id"):
        p_type, _, p_id = entity["parent_type_id"].partition(":")
        if p_type == "project":
            project_id = p_id
    if project_id:
        kwargs["project_id"] = project_id

    # phase: from artifact_type mapping
    phase = ARTIFACT_PHASE_MAP.get(artifact_type)
    if phase:
        kwargs["phase"] = phase

    return kwargs


def _derive_feature_directory(entity: dict, artifacts_root: str) -> str | None:
    """Derive the feature directory for an entity using a 4-step fallback.

    Fallback chain (spec R20 step 2):
      (a) artifact_path is a directory -> return it
      (b) artifact_path is a file -> return dirname
      (c) construct from entity_id: {artifacts_root}/features/{entity_id}/
      (d) if constructed path doesn't exist -> return None (skip)

    Parameters
    ----------
    entity:
        Entity dict as returned by ``EntityDatabase.get_entity()``.
    artifacts_root:
        Root directory for artifact files (e.g. "docs").

    Returns
    -------
    str | None
        Resolved directory path, or None if no directory can be derived.
    """
    ap = entity.get("artifact_path")
    if ap:
        if os.path.isdir(ap):
            return ap
        if os.path.isfile(ap):
            return os.path.dirname(ap)
    # Construct from entity_id (fallback step c)
    candidate = os.path.join(artifacts_root, "features", entity["entity_id"])
    if os.path.isdir(candidate):
        return candidate
    return None
