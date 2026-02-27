"""SQLite database layer for the entity registry system."""
from __future__ import annotations

import json
import sqlite3
from collections.abc import Callable
from datetime import datetime, timezone


def _create_initial_schema(conn: sqlite3.Connection) -> None:
    """Migration 1: create entities and _metadata tables, triggers, indexes."""
    conn.executescript("""
        CREATE TABLE IF NOT EXISTS entities (
            type_id        TEXT PRIMARY KEY,
            entity_type    TEXT NOT NULL CHECK(entity_type IN ('backlog','brainstorm','project','feature')),
            entity_id      TEXT NOT NULL,
            name           TEXT NOT NULL,
            status         TEXT,
            parent_type_id TEXT REFERENCES entities(type_id),
            artifact_path  TEXT,
            created_at     TEXT NOT NULL,
            updated_at     TEXT NOT NULL,
            metadata       TEXT
        );

        CREATE TABLE IF NOT EXISTS _metadata (
            key   TEXT PRIMARY KEY,
            value TEXT NOT NULL
        );

        -- Immutability triggers
        CREATE TRIGGER IF NOT EXISTS enforce_immutable_type_id
        BEFORE UPDATE OF type_id ON entities
        BEGIN
            SELECT RAISE(ABORT, 'type_id is immutable');
        END;

        CREATE TRIGGER IF NOT EXISTS enforce_immutable_entity_type
        BEFORE UPDATE OF entity_type ON entities
        BEGIN
            SELECT RAISE(ABORT, 'entity_type is immutable');
        END;

        CREATE TRIGGER IF NOT EXISTS enforce_immutable_created_at
        BEFORE UPDATE OF created_at ON entities
        BEGIN
            SELECT RAISE(ABORT, 'created_at is immutable');
        END;

        -- Self-parent prevention triggers
        CREATE TRIGGER IF NOT EXISTS enforce_no_self_parent
        BEFORE INSERT ON entities
        WHEN NEW.parent_type_id = NEW.type_id
        BEGIN
            SELECT RAISE(ABORT, 'entity cannot be its own parent');
        END;

        CREATE TRIGGER IF NOT EXISTS enforce_no_self_parent_update
        BEFORE UPDATE OF parent_type_id ON entities
        WHEN NEW.parent_type_id = NEW.type_id
        BEGIN
            SELECT RAISE(ABORT, 'entity cannot be its own parent');
        END;

        -- Indexes
        CREATE INDEX IF NOT EXISTS idx_entity_type ON entities(entity_type);
        CREATE INDEX IF NOT EXISTS idx_parent_type_id ON entities(parent_type_id);
        CREATE INDEX IF NOT EXISTS idx_status ON entities(status);
    """)


# Ordered mapping of version -> migration function.
MIGRATIONS: dict[int, Callable[[sqlite3.Connection], None]] = {
    1: _create_initial_schema,
}


class EntityDatabase:
    """SQLite-backed storage for entity registry.

    Parameters
    ----------
    db_path:
        Path to the SQLite database file, or ``":memory:"`` for an
        in-memory database.
    """

    VALID_ENTITY_TYPES = ("backlog", "brainstorm", "project", "feature")

    def __init__(self, db_path: str) -> None:
        self._conn = sqlite3.connect(db_path, timeout=5.0)
        self._conn.row_factory = sqlite3.Row
        self._set_pragmas()
        self._migrate()

    # ------------------------------------------------------------------
    # Lifecycle
    # ------------------------------------------------------------------

    def close(self) -> None:
        """Close the database connection."""
        self._conn.close()

    # ------------------------------------------------------------------
    # Entity CRUD
    # ------------------------------------------------------------------

    def register_entity(
        self,
        entity_type: str,
        entity_id: str,
        name: str,
        artifact_path: str | None = None,
        status: str | None = None,
        parent_type_id: str | None = None,
        metadata: dict | None = None,
    ) -> str:
        """Register an entity with INSERT OR IGNORE semantics.

        Parameters
        ----------
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
            Optional type_id of the parent entity (must exist).
        metadata:
            Optional dict stored as JSON TEXT.

        Returns
        -------
        str
            The constructed type_id (``f"{entity_type}:{entity_id}"``).
        """
        self._validate_entity_type(entity_type)
        type_id = f"{entity_type}:{entity_id}"
        now = self._now_iso()
        metadata_json = json.dumps(metadata) if metadata is not None else None

        self._conn.execute(
            "INSERT OR IGNORE INTO entities "
            "(type_id, entity_type, entity_id, name, status, parent_type_id, "
            "artifact_path, created_at, updated_at, metadata) "
            "VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?)",
            (type_id, entity_type, entity_id, name, status, parent_type_id,
             artifact_path, now, now, metadata_json),
        )
        self._conn.commit()
        return type_id

    def set_parent(self, type_id: str, parent_type_id: str) -> str:
        """Set or change the parent of an entity.

        Parameters
        ----------
        type_id:
            The entity to update.
        parent_type_id:
            The new parent entity (must exist).

        Returns
        -------
        str
            The type_id of the updated entity.

        Raises
        ------
        ValueError
            If either entity is not found, or if the assignment would
            create a circular reference.
        """
        # Validate both entities exist
        cur = self._conn.execute(
            "SELECT 1 FROM entities WHERE type_id = ?", (type_id,)
        )
        if cur.fetchone() is None:
            raise ValueError(f"Entity not found: {type_id!r}")

        cur = self._conn.execute(
            "SELECT 1 FROM entities WHERE type_id = ?", (parent_type_id,)
        )
        if cur.fetchone() is None:
            raise ValueError(f"Parent entity not found: {parent_type_id!r}")

        # Self-parent check (also enforced by trigger, but give a clear ValueError)
        if type_id == parent_type_id:
            raise ValueError(
                f"Circular reference: entity cannot be its own parent ({type_id!r})"
            )

        # Circular reference detection: walk up from proposed parent,
        # check if we ever reach the child entity.
        cur = self._conn.execute(
            """
            WITH RECURSIVE ancestors(tid) AS (
                SELECT parent_type_id FROM entities WHERE type_id = ?
                UNION ALL
                SELECT e.parent_type_id
                FROM entities e
                JOIN ancestors a ON e.type_id = a.tid
                WHERE e.parent_type_id IS NOT NULL
            )
            SELECT 1 FROM ancestors WHERE tid = ?
            """,
            (parent_type_id, type_id),
        )
        if cur.fetchone() is not None:
            raise ValueError(
                f"Circular reference detected: setting {parent_type_id!r} "
                f"as parent of {type_id!r} would create a cycle"
            )

        self._conn.execute(
            "UPDATE entities SET parent_type_id = ?, updated_at = ? "
            "WHERE type_id = ?",
            (parent_type_id, self._now_iso(), type_id),
        )
        self._conn.commit()
        return type_id

    def get_entity(self, type_id: str) -> dict | None:
        """Retrieve a single entity by type_id, or ``None`` if not found."""
        cur = self._conn.execute(
            "SELECT * FROM entities WHERE type_id = ?", (type_id,)
        )
        row = cur.fetchone()
        if row is None:
            return None
        return dict(row)

    def get_lineage(
        self,
        type_id: str,
        direction: str = "up",
        max_depth: int = 10,
    ) -> list[dict]:
        """Traverse the entity hierarchy.

        Parameters
        ----------
        type_id:
            Starting entity.
        direction:
            ``"up"`` walks toward the root (result is root-first).
            ``"down"`` walks toward leaves (BFS order).
        max_depth:
            Maximum levels to traverse (default 10).

        Returns
        -------
        list[dict]
            Ordered list of entity dicts. Empty if type_id not found.
        """
        # Check entity exists
        cur = self._conn.execute(
            "SELECT 1 FROM entities WHERE type_id = ?", (type_id,)
        )
        if cur.fetchone() is None:
            return []

        if direction == "up":
            return self._lineage_up(type_id, max_depth)
        else:
            return self._lineage_down(type_id, max_depth)

    def _lineage_up(self, type_id: str, max_depth: int) -> list[dict]:
        """Walk up the tree from type_id to root, return root-first."""
        cur = self._conn.execute(
            """
            WITH RECURSIVE ancestors(tid, depth) AS (
                SELECT ?, 0
                UNION ALL
                SELECT e.parent_type_id, a.depth + 1
                FROM entities e
                JOIN ancestors a ON e.type_id = a.tid
                WHERE e.parent_type_id IS NOT NULL
                  AND a.depth < ?
            )
            SELECT e.* FROM ancestors a
            JOIN entities e ON e.type_id = a.tid
            ORDER BY a.depth DESC
            """,
            (type_id, max_depth),
        )
        return [dict(row) for row in cur.fetchall()]

    def _lineage_down(self, type_id: str, max_depth: int) -> list[dict]:
        """Walk down the tree from type_id to leaves, BFS order."""
        cur = self._conn.execute(
            """
            WITH RECURSIVE descendants(tid, depth) AS (
                SELECT ?, 0
                UNION ALL
                SELECT e.type_id, d.depth + 1
                FROM entities e
                JOIN descendants d ON e.parent_type_id = d.tid
                WHERE d.depth < ?
            )
            SELECT e.* FROM descendants d
            JOIN entities e ON e.type_id = d.tid
            ORDER BY d.depth ASC
            """,
            (type_id, max_depth),
        )
        return [dict(row) for row in cur.fetchall()]

    def update_entity(
        self,
        type_id: str,
        name: str | None = None,
        status: str | None = None,
        artifact_path: str | None = None,
        metadata: dict | None = None,
    ) -> None:
        """Update mutable fields of an existing entity.

        Parameters
        ----------
        type_id:
            The entity to update.
        name:
            New name (if provided).
        status:
            New status (if provided).
        artifact_path:
            New artifact_path (if provided).
        metadata:
            If provided, shallow-merges with existing metadata.
            An empty dict ``{}`` clears metadata to None.

        Raises
        ------
        ValueError
            If the entity does not exist.
        """
        # Validate entity exists
        existing = self.get_entity(type_id)
        if existing is None:
            raise ValueError(f"Entity not found: {type_id!r}")

        set_parts: list[str] = ["updated_at = ?"]
        params: list = [self._now_iso()]

        if name is not None:
            set_parts.append("name = ?")
            params.append(name)

        if status is not None:
            set_parts.append("status = ?")
            params.append(status)

        if artifact_path is not None:
            set_parts.append("artifact_path = ?")
            params.append(artifact_path)

        if metadata is not None:
            if len(metadata) == 0:
                # Empty dict clears metadata
                set_parts.append("metadata = ?")
                params.append(None)
            else:
                # Shallow merge with existing
                existing_meta = {}
                if existing["metadata"] is not None:
                    existing_meta = json.loads(existing["metadata"])
                existing_meta.update(metadata)
                set_parts.append("metadata = ?")
                params.append(json.dumps(existing_meta))

        params.append(type_id)
        sql = f"UPDATE entities SET {', '.join(set_parts)} WHERE type_id = ?"
        self._conn.execute(sql, params)
        self._conn.commit()

    # ------------------------------------------------------------------
    # Export
    # ------------------------------------------------------------------

    def export_lineage_markdown(
        self, type_id: str | None = None
    ) -> str:
        """Export entity lineage as a markdown tree.

        Parameters
        ----------
        type_id:
            If provided, export only the tree rooted at this entity.
            If None, export all trees (all root entities).

        Returns
        -------
        str
            Markdown-formatted tree.
        """
        if type_id is not None:
            return self._export_tree(type_id)

        # Find all root entities (no parent)
        cur = self._conn.execute(
            "SELECT type_id FROM entities WHERE parent_type_id IS NULL "
            "ORDER BY entity_type, name"
        )
        roots = [row[0] for row in cur.fetchall()]

        if not roots:
            return ""

        parts: list[str] = []
        for root_id in roots:
            parts.append(self._export_tree(root_id))
        return "\n".join(parts)

    def _export_tree(self, type_id: str, max_depth: int = 50) -> str:
        """Export a single entity and its descendants as markdown.

        Uses a single recursive CTE to fetch all descendants with their
        depth level, avoiding N+1 queries.

        Parameters
        ----------
        type_id:
            Root entity for the tree.
        max_depth:
            Maximum tree depth to traverse (default 50).
            When exceeded, a depth-limit indicator is appended.
        """
        cur = self._conn.execute(
            """
            WITH RECURSIVE tree(tid, depth) AS (
                SELECT ?, 0
                UNION ALL
                SELECT e.type_id, t.depth + 1
                FROM entities e
                JOIN tree t ON e.parent_type_id = t.tid
                WHERE t.depth < ?
            )
            SELECT e.*, t.depth FROM tree t
            JOIN entities e ON e.type_id = t.tid
            ORDER BY t.depth ASC, e.entity_type, e.name
            """,
            (type_id, max_depth),
        )
        rows = [dict(row) for row in cur.fetchall()]

        if not rows:
            return ""

        # Check if any children were truncated at max_depth
        has_truncated = False
        deepest = max(r["depth"] for r in rows)
        if deepest >= max_depth:
            # Check if there are children beyond the limit
            leaf_ids = [r["type_id"] for r in rows if r["depth"] == deepest]
            for lid in leaf_ids:
                check = self._conn.execute(
                    "SELECT 1 FROM entities WHERE parent_type_id = ? LIMIT 1",
                    (lid,),
                )
                if check.fetchone() is not None:
                    has_truncated = True
                    break

        lines: list[str] = []
        for row in rows:
            depth = row["depth"]
            indent = "  " * depth
            status_str = f" [{row['status']}]" if row["status"] else ""
            line = (
                f"{indent}- **{row['name']}** "
                f"({row['entity_type']}:{row['entity_id']}){status_str}"
            )
            lines.append(line)

        if has_truncated:
            indent = "  " * (deepest + 1)
            lines.append(f"{indent}- ... (depth limit reached)")

        return "\n".join(lines)

    # ------------------------------------------------------------------
    # Metadata helpers
    # ------------------------------------------------------------------

    def get_metadata(self, key: str) -> str | None:
        """Read a metadata value by key, or ``None`` if missing."""
        cur = self._conn.execute(
            "SELECT value FROM _metadata WHERE key = ?", (key,)
        )
        row = cur.fetchone()
        return row[0] if row is not None else None

    def set_metadata(self, key: str, value: str) -> None:
        """Write a metadata key/value pair (upserts)."""
        self._conn.execute(
            "INSERT INTO _metadata (key, value) VALUES (?, ?) "
            "ON CONFLICT(key) DO UPDATE SET value = excluded.value",
            (key, value),
        )
        self._conn.commit()

    def get_schema_version(self) -> int:
        """Return the current schema version (0 if not yet migrated)."""
        return int(self.get_metadata("schema_version") or 0)

    # ------------------------------------------------------------------
    # Internal helpers
    # ------------------------------------------------------------------

    @staticmethod
    def _now_iso() -> str:
        """Return current UTC time as ISO-8601 string."""
        return datetime.now(timezone.utc).isoformat()

    @classmethod
    def _validate_entity_type(cls, entity_type: str) -> None:
        """Raise ValueError if entity_type is not in the allowed set."""
        if entity_type not in cls.VALID_ENTITY_TYPES:
            raise ValueError(
                f"Invalid entity_type {entity_type!r}. "
                f"Must be one of {cls.VALID_ENTITY_TYPES}"
            )

    # ------------------------------------------------------------------
    # Internal: pragmas and migrations
    # ------------------------------------------------------------------

    def _set_pragmas(self) -> None:
        """Set connection-level PRAGMAs for performance and safety."""
        self._conn.execute("PRAGMA journal_mode = WAL")
        self._conn.execute("PRAGMA foreign_keys = ON")
        self._conn.execute("PRAGMA busy_timeout = 5000")
        self._conn.execute("PRAGMA cache_size = -8000")

    def _migrate(self) -> None:
        """Apply any pending schema migrations."""
        # Bootstrap: ensure _metadata table exists so we can read schema_version.
        self._conn.execute(
            "CREATE TABLE IF NOT EXISTS _metadata "
            "(key TEXT PRIMARY KEY, value TEXT NOT NULL)"
        )
        self._conn.commit()

        current = self.get_schema_version()
        target = max(MIGRATIONS)

        for version in range(current + 1, target + 1):
            migration_fn = MIGRATIONS[version]
            migration_fn(self._conn)
            self._conn.execute(
                "INSERT INTO _metadata (key, value) VALUES (?, ?) "
                "ON CONFLICT(key) DO UPDATE SET value = excluded.value",
                ("schema_version", str(version)),
            )
            self._conn.commit()
