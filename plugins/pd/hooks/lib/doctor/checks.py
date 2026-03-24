"""Diagnostic check functions for pd:doctor."""
from __future__ import annotations

import glob
import json
import os
import re
import sqlite3
import time

from doctor.models import CheckResult, Issue

# Expected schema versions
ENTITY_SCHEMA_VERSION = 7
MEMORY_SCHEMA_VERSION = 4


def _build_local_entity_set(artifacts_root: str) -> set[str]:
    """Scan {artifacts_root}/features/*/ directories and return directory names.

    Returns a set of entity_ids (directory basenames like '001-alpha').
    Only includes actual directories, not files.
    """
    features_dir = os.path.join(artifacts_root, "features")
    if not os.path.isdir(features_dir):
        return set()
    return {
        entry
        for entry in os.listdir(features_dir)
        if os.path.isdir(os.path.join(features_dir, entry))
    }


def _test_db_lock(db_path: str, label: str) -> Issue | None:
    """Try BEGIN IMMEDIATE on a dedicated short-lived connection.

    Returns an Issue if the DB is locked, None otherwise.
    Connection is always closed before returning.
    """
    conn = None
    try:
        conn = sqlite3.connect(db_path, timeout=2.0)
        conn.execute("PRAGMA busy_timeout = 2000")
        conn.execute("BEGIN IMMEDIATE")
        conn.execute("ROLLBACK")
        return None
    except sqlite3.OperationalError as exc:
        if "locked" in str(exc).lower() or "busy" in str(exc).lower():
            return Issue(
                check="db_readiness",
                severity="error",
                entity=None,
                message=f"{label} is locked: {exc}",
                fix_hint="Kill the process holding the lock or wait for it to release",
            )
        return Issue(
            check="db_readiness",
            severity="error",
            entity=None,
            message=f"{label} lock test failed: {exc}",
            fix_hint=None,
        )
    finally:
        if conn is not None:
            try:
                conn.close()
            except Exception:
                pass


def _check_schema_version(
    db_path: str, label: str, expected: int
) -> Issue | None:
    """Check schema_version on a separate read-only connection.

    Returns an Issue if version doesn't match, None otherwise.
    """
    conn = None
    try:
        conn = sqlite3.connect(db_path, timeout=2.0)
        conn.execute("PRAGMA busy_timeout = 2000")
        row = conn.execute(
            "SELECT value FROM _metadata WHERE key = 'schema_version'"
        ).fetchone()
        if row is None:
            return Issue(
                check="db_readiness",
                severity="error",
                entity=None,
                message=f"{label} has no schema_version in _metadata",
                fix_hint="Run migrations to initialize the database",
            )
        actual = int(row[0])
        if actual != expected:
            return Issue(
                check="db_readiness",
                severity="error",
                entity=None,
                message=(
                    f"{label} schema_version is {actual}, expected {expected}"
                ),
                fix_hint="Run migrations to update the database schema",
            )
        return None
    except sqlite3.OperationalError as exc:
        return Issue(
            check="db_readiness",
            severity="error",
            entity=None,
            message=f"{label} schema version check failed: {exc}",
            fix_hint=None,
        )
    finally:
        if conn is not None:
            try:
                conn.close()
            except Exception:
                pass


def _check_wal_mode(db_path: str, label: str) -> Issue | None:
    """Check journal_mode is WAL on a separate read-only connection.

    Returns an Issue (warning) if not WAL, None otherwise.
    """
    conn = None
    try:
        conn = sqlite3.connect(db_path, timeout=2.0)
        conn.execute("PRAGMA busy_timeout = 2000")
        row = conn.execute("PRAGMA journal_mode").fetchone()
        if row is None or row[0].lower() != "wal":
            mode = row[0] if row else "unknown"
            return Issue(
                check="db_readiness",
                severity="warning",
                entity=None,
                message=f"{label} journal_mode is '{mode}', expected 'wal'",
                fix_hint="Set PRAGMA journal_mode=WAL on the database",
            )
        return None
    except sqlite3.OperationalError as exc:
        return Issue(
            check="db_readiness",
            severity="warning",
            entity=None,
            message=f"{label} WAL check failed: {exc}",
            fix_hint=None,
        )
    finally:
        if conn is not None:
            try:
                conn.close()
            except Exception:
                pass


def check_db_readiness(
    entities_db_path: str, memory_db_path: str, **_
) -> CheckResult:
    """Check 8: DB Readiness.

    Tests lock acquisition, schema version, and WAL mode on both databases.
    Each sub-check uses a dedicated short-lived connection.

    Returns extras={"entity_db_ok": bool, "memory_db_ok": bool}.
    """
    start = time.monotonic()
    issues: list[Issue] = []

    entity_db_ok = True
    memory_db_ok = True

    # Lock tests
    entity_lock_issue = _test_db_lock(entities_db_path, "Entity DB")
    if entity_lock_issue is not None:
        issues.append(entity_lock_issue)
        entity_db_ok = False

    memory_lock_issue = _test_db_lock(memory_db_path, "Memory DB")
    if memory_lock_issue is not None:
        issues.append(memory_lock_issue)
        memory_db_ok = False

    # Schema version checks (only if not locked)
    if entity_db_ok:
        schema_issue = _check_schema_version(
            entities_db_path, "Entity DB", ENTITY_SCHEMA_VERSION
        )
        if schema_issue is not None:
            issues.append(schema_issue)

    if memory_db_ok:
        schema_issue = _check_schema_version(
            memory_db_path, "Memory DB", MEMORY_SCHEMA_VERSION
        )
        if schema_issue is not None:
            issues.append(schema_issue)

    # WAL mode checks (only if not locked)
    if entity_db_ok:
        wal_issue = _check_wal_mode(entities_db_path, "Entity DB")
        if wal_issue is not None:
            issues.append(wal_issue)

    if memory_db_ok:
        wal_issue = _check_wal_mode(memory_db_path, "Memory DB")
        if wal_issue is not None:
            issues.append(wal_issue)

    elapsed = int((time.monotonic() - start) * 1000)
    passed = not any(i.severity in ("error", "warning") for i in issues)

    return CheckResult(
        name="db_readiness",
        passed=passed,
        issues=issues,
        elapsed_ms=elapsed,
        extras={"entity_db_ok": entity_db_ok, "memory_db_ok": memory_db_ok},
    )


# ---------------------------------------------------------------------------
# Check 1: Feature Status Consistency
# ---------------------------------------------------------------------------

# Phase sequence values for backward-transition detection (Check 2)
_PHASE_VALUES = [
    "brainstorm", "specify", "design", "create-plan",
    "create-tasks", "implement", "finish",
]


def check_feature_status(
    entities_conn: sqlite3.Connection, artifacts_root: str, **kwargs
) -> CheckResult:
    """Check 1: Feature Status Consistency.

    Compare .meta.json status against entity DB entities.status for all features.
    """
    start = time.monotonic()
    issues: list[Issue] = []
    local_entity_ids = kwargs.get("local_entity_ids", set())

    # Collect features from .meta.json files
    features_dir = os.path.join(artifacts_root, "features")
    meta_statuses: dict[str, str] = {}  # slug -> status
    meta_data: dict[str, dict] = {}  # slug -> full parsed meta

    if os.path.isdir(features_dir):
        for entry in os.listdir(features_dir):
            feature_dir = os.path.join(features_dir, entry)
            if not os.path.isdir(feature_dir):
                continue
            meta_path = os.path.join(feature_dir, ".meta.json")
            if not os.path.isfile(meta_path):
                # Feature directory exists but no .meta.json
                if entry in local_entity_ids or not local_entity_ids:
                    issues.append(Issue(
                        check="feature_status",
                        severity="warning",
                        entity=f"feature:{entry}",
                        message=f"Feature directory '{entry}' has no .meta.json",
                        fix_hint="Create .meta.json or remove empty directory",
                    ))
                continue
            try:
                with open(meta_path) as f:
                    meta = json.loads(f.read())
                meta_statuses[entry] = meta.get("status", "")
                meta_data[entry] = meta
            except (json.JSONDecodeError, ValueError) as exc:
                issues.append(Issue(
                    check="feature_status",
                    severity="error",
                    entity=f"feature:{entry}",
                    message=f"Malformed .meta.json: {exc}",
                    fix_hint="Fix JSON syntax in .meta.json",
                ))

    # Query DB for all feature entities
    db_statuses: dict[str, str] = {}  # slug -> status
    try:
        cursor = entities_conn.execute(
            "SELECT entity_id, status FROM entities WHERE entity_type = 'feature'"
        )
        for row in cursor:
            db_statuses[row[0]] = row[1] or ""
    except sqlite3.Error:
        pass

    # Compare: features in .meta.json
    for slug, meta_status in meta_statuses.items():
        if slug in db_statuses:
            db_status = db_statuses[slug]
            if meta_status != db_status:
                issues.append(Issue(
                    check="feature_status",
                    severity="error",
                    entity=f"feature:{slug}",
                    message=(
                        f".meta.json status '{meta_status}' != "
                        f"entity DB status '{db_status}'"
                    ),
                    fix_hint=f"Update .meta.json status to '{db_status}'",
                ))
        else:
            # In .meta.json but not in DB — local feature
            if slug in local_entity_ids or not local_entity_ids:
                issues.append(Issue(
                    check="feature_status",
                    severity="warning",
                    entity=f"feature:{slug}",
                    message=f"Feature '{slug}' exists on disk but not in entity DB",
                    fix_hint="Register entity or remove stale feature directory",
                ))

    # Compare: features in DB but not in .meta.json (only local)
    for slug, db_status in db_statuses.items():
        if slug not in meta_statuses:
            if slug in local_entity_ids or not local_entity_ids:
                # Only warn for local features (those with dirs)
                feature_dir = os.path.join(features_dir, slug)
                if os.path.isdir(feature_dir):
                    issues.append(Issue(
                        check="feature_status",
                        severity="warning",
                        entity=f"feature:{slug}",
                        message=f"Feature '{slug}' in DB but .meta.json missing",
                        fix_hint="Create .meta.json or deregister entity",
                    ))
            # Cross-project: skip if not in local_entity_ids

    # Hardening: null lastCompletedPhase with completed phase timestamps
    for slug, meta in meta_data.items():
        phases = meta.get("phases", {})
        has_completed = any(
            isinstance(v, dict) and "completed" in v
            for v in phases.values()
        ) if isinstance(phases, dict) else False
        lcp = meta.get("lastCompletedPhase")
        if has_completed and lcp is None:
            issues.append(Issue(
                check="feature_status",
                severity="warning",
                entity=f"feature:{slug}",
                message=(
                    f"Feature '{slug}' has completed phases but "
                    "lastCompletedPhase is null"
                ),
                fix_hint="Set lastCompletedPhase to the latest completed phase",
            ))

    elapsed = int((time.monotonic() - start) * 1000)
    passed = not any(i.severity in ("error", "warning") for i in issues)
    return CheckResult(
        name="feature_status",
        passed=passed,
        issues=issues,
        elapsed_ms=elapsed,
    )


# ---------------------------------------------------------------------------
# Check 2: Workflow Phase Consistency
# ---------------------------------------------------------------------------


def check_workflow_phase(
    entities_db_path: str, artifacts_root: str, **kwargs
) -> CheckResult:
    """Check 2: Workflow Phase Consistency.

    Uses check_workflow_drift() from workflow_engine.reconciliation to detect
    drift between .meta.json and workflow DB.
    """
    start = time.monotonic()
    issues: list[Issue] = []
    local_entity_ids = kwargs.get("local_entity_ids", set())

    db = None
    try:
        # Lazy imports to avoid pulling heavy deps unless needed
        from entity_registry.database import EntityDatabase
        from workflow_engine.engine import WorkflowStateEngine
        from workflow_engine.reconciliation import check_workflow_drift

        db = EntityDatabase(entities_db_path)
        engine = WorkflowStateEngine(db, artifacts_root)

        drift_result = check_workflow_drift(engine, db, artifacts_root)

        for report in drift_result.features:
            type_id = report.feature_type_id
            slug = type_id.split(":", 1)[1] if ":" in type_id else type_id

            if report.status == "in_sync":
                # Check for kanban-only drift in mismatches
                for mm in report.mismatches:
                    if mm.field == "kanban_column":
                        issues.append(Issue(
                            check="workflow_phase",
                            severity="warning",
                            entity=type_id,
                            message=(
                                f"Kanban column drift: meta_json='{mm.meta_json_value}' "
                                f"vs db='{mm.db_value}'"
                            ),
                            fix_hint="Run reconcile_apply to sync kanban column",
                        ))

            elif report.status == "meta_json_ahead":
                issues.append(Issue(
                    check="workflow_phase",
                    severity="error",
                    entity=type_id,
                    message=(
                        f"Workflow drift ({report.status}): "
                        f".meta.json is ahead of DB"
                    ),
                    fix_hint="Run reconcile_apply to sync DB from .meta.json",
                ))

            elif report.status == "db_ahead":
                issues.append(Issue(
                    check="workflow_phase",
                    severity="error",
                    entity=type_id,
                    message=(
                        f"Workflow drift ({report.status}): "
                        f"DB has newer state than .meta.json"
                    ),
                    fix_hint="Update .meta.json from DB state",
                ))

            elif report.status == "meta_json_only":
                issues.append(Issue(
                    check="workflow_phase",
                    severity="warning",
                    entity=type_id,
                    message=f"Feature exists in .meta.json but not in workflow DB",
                    fix_hint="Run reconcile_apply to create DB entry",
                ))

            elif report.status == "db_only":
                # Cross-project: skip if not local
                if local_entity_ids and slug not in local_entity_ids:
                    continue
                issues.append(Issue(
                    check="workflow_phase",
                    severity="warning",
                    entity=type_id,
                    message=f"Feature exists in workflow DB but not in .meta.json",
                    fix_hint="Create .meta.json or remove stale DB entry",
                ))

            elif report.status == "error":
                issues.append(Issue(
                    check="workflow_phase",
                    severity="error",
                    entity=type_id,
                    message=f"Workflow check error: {report.message}",
                    fix_hint=None,
                ))

        # Backward transition awareness: check for rework state
        try:
            conn = db._conn
            cursor = conn.execute(
                "SELECT type_id, workflow_phase, last_completed_phase "
                "FROM workflow_phases"
            )
            for row in cursor:
                wp_type_id = row[0]
                wp = row[1]
                lcp = row[2]
                if wp and lcp:
                    wp_idx = (
                        _PHASE_VALUES.index(wp) if wp in _PHASE_VALUES else -1
                    )
                    lcp_idx = (
                        _PHASE_VALUES.index(lcp) if lcp in _PHASE_VALUES else -1
                    )
                    if wp_idx >= 0 and lcp_idx >= 0 and wp_idx < lcp_idx:
                        issues.append(Issue(
                            check="workflow_phase",
                            severity="info",
                            entity=wp_type_id,
                            message=(
                                f"Feature in rework state: workflow_phase='{wp}' "
                                f"is before last_completed_phase='{lcp}'"
                            ),
                            fix_hint=None,
                        ))
        except sqlite3.Error:
            pass

    except sqlite3.OperationalError as exc:
        issues.append(Issue(
            check="workflow_phase",
            severity="error",
            entity=None,
            message=f"Cannot access workflow DB: {exc}",
            fix_hint="Check if entity DB is locked or corrupted",
        ))
    finally:
        if db is not None:
            try:
                db.close()
            except Exception:
                pass

    elapsed = int((time.monotonic() - start) * 1000)
    passed = not any(i.severity in ("error", "warning") for i in issues)
    return CheckResult(
        name="workflow_phase",
        passed=passed,
        issues=issues,
        elapsed_ms=elapsed,
    )


# ---------------------------------------------------------------------------
# Check 3: Brainstorm Status Consistency
# ---------------------------------------------------------------------------


def check_brainstorm_status(
    entities_conn: sqlite3.Connection, artifacts_root: str, **_
) -> CheckResult:
    """Check 3: Brainstorm Status Consistency.

    For each brainstorm entity with status != 'promoted', check if a completed
    feature references it via brainstorm_source.
    """
    start = time.monotonic()
    issues: list[Issue] = []

    # Get brainstorm entities that are not promoted
    brainstorms: list[tuple[str, str, str]] = []  # (type_id, entity_id, status)
    try:
        cursor = entities_conn.execute(
            "SELECT type_id, entity_id, status FROM entities "
            "WHERE entity_type = 'brainstorm' "
            "AND (status IS NULL OR status != 'promoted')"
        )
        brainstorms = [(row[0], row[1], row[2] or "") for row in cursor]
    except sqlite3.Error:
        pass

    if not brainstorms:
        elapsed = int((time.monotonic() - start) * 1000)
        return CheckResult(
            name="brainstorm_status",
            passed=True,
            issues=issues,
            elapsed_ms=elapsed,
        )

    # Scan feature .meta.json files for brainstorm_source references
    features_dir = os.path.join(artifacts_root, "features")
    brainstorm_refs: dict[str, list[str]] = {}  # brainstorm_entity_id -> [feature_slugs]

    if os.path.isdir(features_dir):
        for entry in os.listdir(features_dir):
            meta_path = os.path.join(features_dir, entry, ".meta.json")
            if not os.path.isfile(meta_path):
                continue
            try:
                with open(meta_path) as f:
                    meta = json.loads(f.read())
                bs_source = meta.get("brainstorm_source")
                if bs_source:
                    # Verify the brainstorm source file exists
                    bs_path = os.path.join(artifacts_root, "brainstorms", bs_source)
                    if not os.path.exists(bs_path):
                        # Also try as just the entity_id (brainstorm_source might be filename or id)
                        bs_dir = os.path.join(artifacts_root, "brainstorms")
                        # Check if any file matching exists
                        found = False
                        if os.path.isdir(bs_dir):
                            for bs_entry in os.listdir(bs_dir):
                                if bs_source in bs_entry:
                                    found = True
                                    break
                        if not found:
                            issues.append(Issue(
                                check="brainstorm_status",
                                severity="warning",
                                entity=f"feature:{entry}",
                                message=(
                                    f"brainstorm_source '{bs_source}' referenced "
                                    f"in feature '{entry}' does not exist"
                                ),
                                fix_hint="Update brainstorm_source or create the brainstorm file",
                            ))

                    feature_status = meta.get("status", "")
                    if feature_status in ("completed", "finished"):
                        brainstorm_refs.setdefault(bs_source, []).append(entry)
            except (json.JSONDecodeError, ValueError):
                continue

    # Check each brainstorm: should it be promoted?
    for type_id, entity_id, status in brainstorms:
        # Direct: check if a completed feature references this brainstorm
        if entity_id in brainstorm_refs:
            features = brainstorm_refs[entity_id]
            issues.append(Issue(
                check="brainstorm_status",
                severity="warning",
                entity=type_id,
                message=(
                    f"Brainstorm '{entity_id}' should be promoted: "
                    f"completed feature(s) {features} reference it"
                ),
                fix_hint="Update brainstorm entity status to 'promoted'",
            ))
            continue

        # Fallback: check entity_dependencies for brainstorm->feature edges
        try:
            # Get brainstorm UUID
            bs_row = entities_conn.execute(
                "SELECT uuid FROM entities WHERE type_id = ?", (type_id,)
            ).fetchone()
            if bs_row:
                bs_uuid = bs_row[0]
                dep_cursor = entities_conn.execute(
                    "SELECT target_uuid FROM entity_dependencies "
                    "WHERE source_uuid = ?",
                    (bs_uuid,),
                )
                for dep_row in dep_cursor:
                    target_uuid = dep_row[0]
                    # Check if target is a completed feature
                    feat_row = entities_conn.execute(
                        "SELECT type_id, status FROM entities "
                        "WHERE uuid = ? AND entity_type = 'feature'",
                        (target_uuid,),
                    ).fetchone()
                    if feat_row and feat_row[1] in ("completed", "finished"):
                        issues.append(Issue(
                            check="brainstorm_status",
                            severity="warning",
                            entity=type_id,
                            message=(
                                f"Brainstorm '{entity_id}' should be promoted: "
                                f"dependency edge to completed feature '{feat_row[0]}'"
                            ),
                            fix_hint="Update brainstorm entity status to 'promoted'",
                        ))
                        break
        except sqlite3.Error:
            pass

    elapsed = int((time.monotonic() - start) * 1000)
    passed = not any(i.severity in ("error", "warning") for i in issues)
    return CheckResult(
        name="brainstorm_status",
        passed=passed,
        issues=issues,
        elapsed_ms=elapsed,
    )


# ---------------------------------------------------------------------------
# Check 4: Backlog Status Consistency
# ---------------------------------------------------------------------------


def check_backlog_status(
    entities_conn: sqlite3.Connection, artifacts_root: str, **_
) -> CheckResult:
    """Check 4: Backlog Status Consistency.

    Parse backlog.md for (promoted -> ...) annotations and cross-ref entity DB.
    """
    start = time.monotonic()
    issues: list[Issue] = []

    backlog_path = os.path.join(artifacts_root, "backlog.md")
    if not os.path.isfile(backlog_path):
        elapsed = int((time.monotonic() - start) * 1000)
        return CheckResult(
            name="backlog_status",
            passed=True,
            issues=issues,
            elapsed_ms=elapsed,
        )

    # Parse backlog.md for promoted annotations
    annotated_ids: set[str] = set()
    content = ""
    try:
        with open(backlog_path) as f:
            content = f.read()

        # Match lines with (promoted -> ...) or (promoted-> ...)
        # Pattern: look for (promoted → or (promoted -> or (promoted->
        promoted_pattern = re.compile(
            r"\(promoted\s*(?:→|->)\s*([^)]*)\)", re.IGNORECASE
        )
        # Also try to extract backlog ID from the line
        # Backlog lines typically have an ID like BL-001 or a number
        id_pattern = re.compile(r"(?:BL-?)?(\d+)", re.IGNORECASE)

        for line in content.splitlines():
            match = promoted_pattern.search(line)
            if match:
                # Try to extract a backlog ID from the line
                id_match = id_pattern.search(line)
                if id_match:
                    backlog_id = id_match.group(0)
                    annotated_ids.add(backlog_id)
    except (OSError, IOError):
        pass

    if not annotated_ids and not content.strip():
        # Empty backlog — passes
        elapsed = int((time.monotonic() - start) * 1000)
        return CheckResult(
            name="backlog_status",
            passed=True,
            issues=issues,
            elapsed_ms=elapsed,
        )

    # Cross-ref annotated IDs with entity DB
    for backlog_id in annotated_ids:
        type_id = f"backlog:{backlog_id}"
        try:
            row = entities_conn.execute(
                "SELECT status FROM entities WHERE type_id = ?", (type_id,)
            ).fetchone()
            if row:
                db_status = row[0] or ""
                if db_status != "promoted":
                    issues.append(Issue(
                        check="backlog_status",
                        severity="warning",
                        entity=type_id,
                        message=(
                            f"Backlog '{backlog_id}' annotated as promoted in "
                            f"backlog.md but entity status is '{db_status}'"
                        ),
                        fix_hint="Update entity status to 'promoted'",
                    ))
            else:
                issues.append(Issue(
                    check="backlog_status",
                    severity="warning",
                    entity=type_id,
                    message=(
                        f"Backlog '{backlog_id}' annotated as promoted in "
                        "backlog.md but entity not found in DB"
                    ),
                    fix_hint="Register backlog entity or remove annotation",
                ))
        except sqlite3.Error:
            pass

    # Check reverse: entities promoted but not annotated in backlog.md
    try:
        cursor = entities_conn.execute(
            "SELECT entity_id, status FROM entities "
            "WHERE entity_type = 'backlog' AND status = 'promoted'"
        )
        for row in cursor:
            entity_id = row[0]
            if entity_id not in annotated_ids:
                issues.append(Issue(
                    check="backlog_status",
                    severity="info",
                    entity=f"backlog:{entity_id}",
                    message=(
                        f"Backlog '{entity_id}' is promoted in DB but "
                        "not annotated in backlog.md"
                    ),
                    fix_hint="Add (promoted -> feature) annotation to backlog.md",
                ))
    except sqlite3.Error:
        pass

    elapsed = int((time.monotonic() - start) * 1000)
    passed = not any(i.severity in ("error", "warning") for i in issues)
    return CheckResult(
        name="backlog_status",
        passed=passed,
        issues=issues,
        elapsed_ms=elapsed,
    )
