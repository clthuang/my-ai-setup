"""Helper functions for the MCP entity server layer.

These wrap EntityDatabase calls with formatting, error handling,
and output suitable for MCP tool responses.
"""
from __future__ import annotations

import json
import os
from collections import defaultdict


def render_tree(entities: list[dict], root_type_id: str) -> str:
    """Render a flat list of entity dicts as a Unicode box-drawing tree.

    Parameters
    ----------
    entities:
        Flat list of entity dicts. Each must have keys: type_id, name,
        entity_type, status, parent_type_id, created_at.
    root_type_id:
        The type_id of the root node for this tree.

    Returns
    -------
    str
        Formatted tree string with Unicode box-drawing characters.
        Empty string if entities is empty or root_type_id not found.
    """
    if not entities:
        return ""

    # Build lookup and children map
    by_id: dict[str, dict] = {}
    children: dict[str, list[str]] = defaultdict(list)

    for entity in entities:
        tid = entity["type_id"]
        by_id[tid] = entity
        parent = entity.get("parent_type_id")
        if parent is not None and parent in {e["type_id"] for e in entities}:
            children[parent].append(tid)

    if root_type_id not in by_id:
        return ""

    lines: list[str] = []
    _render_node(by_id, children, root_type_id, "", True, True, lines)
    return "\n".join(lines)


def _format_entity_label(entity: dict) -> str:
    """Format a single entity as: type_id -- "name" (status, date)."""
    date_part = entity["created_at"][:10]
    status = entity.get("status")
    if status:
        paren = f"({status}, {date_part})"
    else:
        paren = f"({date_part})"
    return f'{entity["type_id"]} \u2014 "{entity["name"]}" {paren}'


def _render_node(
    by_id: dict[str, dict],
    children: dict[str, list[str]],
    type_id: str,
    prefix: str,
    is_last: bool,
    is_root: bool,
    lines: list[str],
) -> None:
    """Recursively render a node and its children."""
    entity = by_id[type_id]
    label = _format_entity_label(entity)

    if is_root:
        lines.append(label)
        child_prefix = "  "
    else:
        connector = "\u2514\u2500" if is_last else "\u251c\u2500"
        lines.append(f"{prefix}{connector} {label}")
        # For children of this node, continuation indent depends on
        # whether this node was last among its siblings.
        child_prefix = prefix + ("   " if is_last else "\u2502  ")

    kids = children.get(type_id, [])
    for i, kid_id in enumerate(kids):
        kid_is_last = (i == len(kids) - 1)
        _render_node(by_id, children, kid_id, child_prefix, kid_is_last, False, lines)


def parse_metadata(metadata_str: str | None) -> dict | None:
    """Parse a JSON metadata string into a dict.

    Parameters
    ----------
    metadata_str:
        JSON string to parse, or None.

    Returns
    -------
    dict | None
        Parsed dict on success, None if input is None,
        or ``{"error": "<message>"}`` if JSON is invalid.
    """
    if metadata_str is None:
        return None
    try:
        return json.loads(metadata_str)
    except (json.JSONDecodeError, ValueError) as exc:
        return {"error": f"Invalid JSON: {exc}"}


def resolve_output_path(
    output_path: str | None, artifacts_root: str
) -> str | None:
    """Resolve an output path against an artifacts root directory.

    Parameters
    ----------
    output_path:
        Path to resolve. If absolute, returned as-is.
        If relative, joined with artifacts_root.
        If None, returns None.
    artifacts_root:
        Base directory for relative path resolution.

    Returns
    -------
    str | None
        Resolved absolute path, or None if output_path is None.
    """
    if output_path is None:
        return None
    if os.path.isabs(output_path):
        return output_path
    return os.path.join(artifacts_root, output_path)


def _process_register_entity(
    db,
    entity_type: str,
    entity_id: str,
    name: str,
    artifact_path: str | None,
    status: str | None,
    parent_type_id: str | None,
    metadata: dict | None,
) -> str:
    """Register an entity via EntityDatabase with error handling.

    Parameters
    ----------
    db:
        An EntityDatabase instance.
    entity_type:
        One of: backlog, brainstorm, project, feature.
    entity_id:
        Unique identifier within the entity_type namespace.
    name:
        Human-readable name.
    artifact_path:
        Optional filesystem path to the entity's artifact.
    status:
        Optional status string.
    parent_type_id:
        Optional type_id of the parent entity.
    metadata:
        Optional dict stored as JSON.

    Returns
    -------
    str
        Success message containing the type_id, or error message.
        Never raises exceptions.
    """
    try:
        type_id = db.register_entity(
            entity_type=entity_type,
            entity_id=entity_id,
            name=name,
            artifact_path=artifact_path,
            status=status,
            parent_type_id=parent_type_id,
            metadata=metadata,
        )
        return f"Registered entity: {type_id}"
    except Exception as exc:
        return f"Error registering entity: {exc}"


def _process_get_lineage(
    db,
    type_id: str,
    direction: str,
    max_depth: int,
) -> str:
    """Get entity lineage via EntityDatabase with tree rendering.

    Parameters
    ----------
    db:
        An EntityDatabase instance.
    type_id:
        Starting entity for lineage traversal.
    direction:
        ``"up"`` walks toward root, ``"down"`` walks toward leaves.
    max_depth:
        Maximum levels to traverse.

    Returns
    -------
    str
        Formatted tree string, or error/not-found message.
        Never raises exceptions.
    """
    try:
        entities = db.get_lineage(type_id, direction=direction, max_depth=max_depth)
        if not entities:
            return f"Entity not found: {type_id}"

        # Determine the root of the rendered tree.
        # For "up" direction, lineage is root-first, so root is first element.
        # For "down" direction, the starting entity is the root.
        root_type_id = entities[0]["type_id"]

        return render_tree(entities, root_type_id)
    except Exception as exc:
        return f"Error retrieving lineage: {exc}"
