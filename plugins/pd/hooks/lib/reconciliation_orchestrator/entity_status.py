"""Entity status sync: reads .meta.json files, compares with entity registry, updates on drift."""
import json
import os
import re

# Backlog row parsing constants
BACKLOG_ROW_RE = re.compile(r'^\|\s*(\d{5})\s*\|[^|]*\|(.+)\|')
CLOSED_RE = re.compile(r'\((?:closed|already implemented)[:\s\u2014]')
PROMOTED_RE = re.compile(r'\(promoted\s*(?:\u2192|->)')
FIXED_RE = re.compile(r'\(fixed:')
JUNK_ID_RE = re.compile(r'^[0-9]{5}$')
NAME_STRIP_RE = re.compile(r'\s*\((?:closed|promoted|fixed|already implemented)[^)]*\)\s*')


def sync_entity_statuses(db, full_artifacts_path, project_id="__unknown__"):
    """Scan .meta.json files for features and projects and sync status to entity registry.

    Args:
        db: EntityDatabase instance
        full_artifacts_path: absolute path to the artifacts root (e.g., /project/docs)

    Returns:
        {"updated": int, "skipped": int, "archived": int, "warnings": list[str]}
    """
    STATUS_MAP = {"active", "completed", "abandoned", "planned", "promoted"}
    results = {"updated": 0, "skipped": 0, "archived": 0, "warnings": []}

    for entity_type, subdir in [("feature", "features"), ("project", "projects")]:
        scan_dir = os.path.join(full_artifacts_path, subdir)
        if not os.path.isdir(scan_dir):
            continue

        for folder in os.listdir(scan_dir):
            meta_path = os.path.join(scan_dir, folder, ".meta.json")
            type_id = f"{entity_type}:{folder}"

            if not os.path.isfile(meta_path):
                # .meta.json deleted — archive entity if it exists
                try:
                    db.update_entity(type_id, status="archived", project_id=project_id)
                    results["archived"] += 1
                except ValueError:
                    pass  # entity not in registry, skip
                continue

            try:
                with open(meta_path) as f:
                    meta = json.load(f)
            except (json.JSONDecodeError, OSError) as e:
                results["warnings"].append(f"Failed to read {meta_path}: {e}")
                continue

            meta_status = meta.get("status")

            if meta_status not in STATUS_MAP:
                results["warnings"].append(f"Unknown status '{meta_status}' for {type_id}")
                continue

            entity = db.get_entity(type_id)  # returns None if not found
            if entity is None:
                results["skipped"] += 1  # entity not in registry
                continue

            if entity["status"] != meta_status:
                db.update_entity(type_id, status=meta_status, project_id=project_id)
                results["updated"] += 1
            else:
                results["skipped"] += 1

    return results


def _sync_brainstorm_entities(
    db, full_artifacts_path, artifacts_root, project_root, project_id="__unknown__"
):
    """Scan brainstorms/ for .prd.md files; register new ones; archive missing ones.

    Part 1: Register unregistered .prd.md files as brainstorm entities.
    Part 2: Archive non-terminal brainstorm entities whose artifact file no longer exists (AC-9).

    Args:
        db: EntityDatabase instance.
        full_artifacts_path: Absolute path to artifacts root (e.g., /project/docs).
        artifacts_root: Relative artifacts sub-path for stored artifact_path (e.g., "docs").
        project_root: Absolute project root for resolving artifact_path to absolute.
        project_id: Project identifier for entity registration.

    Returns:
        {"registered": int, "archived": int, "skipped": int}
    """
    TERMINAL_STATUSES = {"promoted", "abandoned", "archived"}
    results = {"registered": 0, "archived": 0, "skipped": 0}
    brainstorms_dir = os.path.join(full_artifacts_path, "brainstorms")

    if not os.path.isdir(brainstorms_dir):
        return results

    # Part 1: scan filesystem for .prd.md files, register new entities
    seen_on_disk = set()  # entity_ids with files present on disk
    for filename in os.listdir(brainstorms_dir):
        if filename == ".gitkeep" or not filename.endswith(".prd.md"):
            continue

        stem = filename[: -len(".prd.md")]
        seen_on_disk.add(stem)
        type_id = f"brainstorm:{stem}"

        existing = db.get_entity(type_id)
        if existing is not None:
            results["skipped"] += 1
            continue

        artifact_path = os.path.join(artifacts_root, "brainstorms", filename)
        db.register_entity(
            entity_type="brainstorm",
            entity_id=stem,
            name=stem,
            artifact_path=artifact_path,
            status="active",
            project_id=project_id,
        )
        results["registered"] += 1

    # Part 2: detect missing files for non-terminal brainstorm entities (AC-9)
    entities = db.list_entities(entity_type="brainstorm", project_id=project_id)
    for entity in entities:
        if entity["entity_id"] in seen_on_disk:
            continue  # file exists on disk, skip

        status = entity.get("status", "")
        if status in TERMINAL_STATUSES:
            continue

        rel_path = entity.get("artifact_path", "")
        if not rel_path:
            continue

        abs_path = os.path.join(project_root, rel_path)
        if not os.path.isfile(abs_path):
            type_id = f"brainstorm:{entity['entity_id']}"
            db.update_entity(type_id, status="archived", project_id=project_id)
            results["archived"] += 1

    return results


def _cleanup_junk_backlogs(db, project_id):
    """Delete backlog entities whose entity_id is not a valid 5-digit ID.

    Returns:
        (deleted_count, warnings_list)
    """
    deleted = 0
    warnings = []
    entities = db.list_entities(entity_type="backlog", project_id=project_id)
    for entity in entities:
        entity_id = entity["type_id"].split(":", 1)[1]
        if not JUNK_ID_RE.match(entity_id):
            try:
                db.delete_entity(entity["type_id"], project_id=project_id)
                deleted += 1
            except ValueError as e:
                warnings.append(f"Cannot delete backlog:{entity_id}: {e}")
    return deleted, warnings


def _dedup_backlogs(db, project_id):
    """Remove duplicate backlog entities sharing the same (entity_id, project_id).

    For duplicates, keeps the entity with a non-null status and deletes the other.

    Returns:
        Count of entities deleted.
    """
    entities = db.list_entities(entity_type="backlog", project_id=project_id)
    # Group by entity_id
    groups = {}
    for entity in entities:
        entity_id = entity["type_id"].split(":", 1)[1]
        groups.setdefault(entity_id, []).append(entity)

    deleted = 0
    for entity_id, group in groups.items():
        if len(group) <= 1:
            continue
        # Sort: entities with non-null status first (keep those)
        group.sort(key=lambda e: (e.get("status") is None, e["uuid"]))
        # Keep first, delete rest
        for dup in group[1:]:
            try:
                db.delete_entity(dup["uuid"])
                deleted += 1
            except ValueError:
                pass
    return deleted


def _sync_backlog_entities(db, full_artifacts_path, artifacts_root, project_id):
    """Parse backlog.md and sync backlog entities to the entity registry.

    Execution order: (1) cleanup junk IDs, (2) dedup, (3) parse and sync.

    Args:
        db: EntityDatabase instance
        full_artifacts_path: absolute path to the artifacts root directory
        artifacts_root: relative artifacts root (e.g., "docs")
        project_id: project identifier

    Returns:
        {"updated": int, "skipped": int, "registered": int, "deleted": int, "warnings": list[str]}
    """
    results = {"updated": 0, "skipped": 0, "registered": 0, "deleted": 0, "warnings": []}

    # Step 1: cleanup junk backlog IDs
    junk_deleted, junk_warnings = _cleanup_junk_backlogs(db, project_id)
    results["deleted"] += junk_deleted
    results["warnings"].extend(junk_warnings)

    # Step 2: dedup
    dedup_deleted = _dedup_backlogs(db, project_id)
    results["deleted"] += dedup_deleted

    # Step 3: parse backlog.md and sync
    backlog_path = os.path.join(full_artifacts_path, "backlog.md")
    if not os.path.isfile(backlog_path):
        return results

    with open(backlog_path) as f:
        lines = f.readlines()

    for line in lines:
        m = BACKLOG_ROW_RE.match(line)
        if not m:
            continue

        entity_id = m.group(1)
        description = m.group(2).strip()

        # Detect status from markers
        if CLOSED_RE.search(description):
            status = "dropped"
        elif PROMOTED_RE.search(description):
            status = "promoted"
        elif FIXED_RE.search(description):
            status = "dropped"
        else:
            status = "open"

        # Strip status markers from name
        name = NAME_STRIP_RE.sub("", description).strip()
        name = name[:200]

        type_id = f"backlog:{entity_id}"
        existing = db.get_entity(type_id)

        if existing is None:
            db.register_entity(
                entity_type="backlog",
                entity_id=entity_id,
                name=name,
                artifact_path=os.path.join(artifacts_root, "backlog.md"),
                status=status,
                project_id=project_id,
            )
            results["registered"] += 1
        elif existing["status"] != status:
            db.update_entity(type_id, status=status, project_id=project_id)
            results["updated"] += 1
        else:
            results["skipped"] += 1

    return results
