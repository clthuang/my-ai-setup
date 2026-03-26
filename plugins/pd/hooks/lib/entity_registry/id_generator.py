"""Central entity ID generator.

Generates standardised ``{seq}-{slug}`` entity IDs with per-type sequential
counters stored in the ``sequences`` table.
"""
from __future__ import annotations

import re
from typing import TYPE_CHECKING

if TYPE_CHECKING:
    from entity_registry.database import EntityDatabase


def _slugify(name: str, *, max_length: int = 30) -> str:
    """Convert *name* to a lowercase, hyphen-separated slug.

    Rules:
      - Lowercase the entire string
      - Replace non-alphanumeric characters with hyphens
      - Collapse consecutive hyphens
      - Strip leading/trailing hyphens
      - Truncate to *max_length* characters (on a hyphen boundary when possible)
    """
    slug = name.lower()
    slug = re.sub(r"[^a-z0-9]+", "-", slug)
    slug = re.sub(r"-{2,}", "-", slug)
    slug = slug.strip("-")

    if len(slug) <= max_length:
        return slug

    # Truncate on a hyphen boundary to avoid cutting mid-word
    truncated = slug[:max_length]
    last_hyphen = truncated.rfind("-")
    if last_hyphen > 0:
        truncated = truncated[:last_hyphen]
    return truncated.rstrip("-")


def generate_entity_id(
    db: "EntityDatabase", entity_type: str, name: str, project_id: str
) -> str:
    """Generate a standardised ``{seq}-{slug}`` entity ID.

    Parameters
    ----------
    db:
        EntityDatabase instance (used for sequence counter persistence).
    entity_type:
        The entity type (e.g. ``"feature"``, ``"task"``).
    name:
        Human-readable name from which the slug is derived.
    project_id:
        The project scope for the sequence counter.

    Returns
    -------
    str
        Entity ID in ``{seq:03d}-{slug}`` format.
    """
    seq = db.next_sequence_value(project_id, entity_type)
    slug = _slugify(name)

    if not slug:
        slug = "unnamed"

    return f"{seq:03d}-{slug}"
