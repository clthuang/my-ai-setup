"""SQLite database layer for the semantic memory system."""
from __future__ import annotations

import sqlite3
from typing import Callable


def _create_initial_schema(conn: sqlite3.Connection) -> None:
    """Migration 1: create entries and _metadata tables."""
    conn.executescript("""
        CREATE TABLE IF NOT EXISTS entries (
            id                TEXT PRIMARY KEY,
            name              TEXT NOT NULL,
            description       TEXT NOT NULL,
            reasoning         TEXT,
            category          TEXT NOT NULL CHECK(category IN ('anti-patterns', 'patterns', 'heuristics')),
            keywords          TEXT,
            source            TEXT NOT NULL CHECK(source IN ('retro', 'session-capture', 'manual', 'import')),
            source_project    TEXT,
            "references"      TEXT,
            observation_count INTEGER DEFAULT 1,
            confidence        TEXT DEFAULT 'medium' CHECK(confidence IN ('high', 'medium', 'low')),
            recall_count      INTEGER DEFAULT 0,
            last_recalled_at  TEXT,
            embedding         BLOB,
            created_at        TEXT NOT NULL,
            updated_at        TEXT NOT NULL
        );

        CREATE TABLE IF NOT EXISTS _metadata (
            key   TEXT PRIMARY KEY,
            value TEXT NOT NULL
        );
    """)


# Ordered mapping of version -> migration function.
# Each migration brings the schema from (version - 1) to version.
MIGRATIONS: dict[int, Callable[[sqlite3.Connection], None]] = {
    1: _create_initial_schema,
}

# All 16 column names in insertion order.
_COLUMNS = [
    "id", "name", "description", "reasoning", "category",
    "keywords", "source", "source_project", '"references"',
    "observation_count", "confidence", "recall_count",
    "last_recalled_at", "embedding", "created_at", "updated_at",
]

# Columns that use "overwrite if non-null, keep existing if null" on conflict.
_CONDITIONAL_UPDATE_COLS = ["description", "reasoning", "keywords", '"references"']


class MemoryDatabase:
    """SQLite-backed storage for semantic memory entries.

    Parameters
    ----------
    db_path:
        Path to the SQLite database file, or ``":memory:"`` for an
        in-memory database.
    """

    def __init__(self, db_path: str) -> None:
        self._conn = sqlite3.connect(db_path)
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
    # Entry CRUD
    # ------------------------------------------------------------------

    def upsert_entry(self, entry: dict) -> None:
        """Insert a new entry or update an existing one.

        On conflict (same ``id``):
        - ``observation_count`` is incremented by 1.
        - ``updated_at`` is set to the incoming value.
        - ``description``, ``reasoning``, ``keywords``, ``"references"``
          are overwritten only if the incoming value is not None;
          otherwise the existing value is kept.
        - ``created_at`` is preserved (never overwritten).

        Uses a check-then-act pattern within a transaction to correctly
        handle NOT NULL columns that may be None on update (meaning
        "keep existing") without triggering constraint violations.
        """
        entry_id = entry.get("id")
        cur = self._conn.execute(
            "SELECT 1 FROM entries WHERE id = ?", (entry_id,)
        )
        exists = cur.fetchone() is not None

        if not exists:
            self._insert_new(entry)
        else:
            self._update_existing(entry)

        self._conn.commit()

    def _insert_new(self, entry: dict) -> None:
        """Insert a brand-new entry row.

        Only includes columns present in *entry* so that SQLite column
        DEFAULTs (e.g. observation_count=1, confidence='medium',
        recall_count=0) apply when the caller omits them.
        """
        cols: list[str] = []
        vals: list = []
        for col in _COLUMNS:
            key = col.strip('"')
            if key in entry:
                cols.append(col)
                vals.append(entry[key])

        col_list = ", ".join(cols)
        placeholders = ", ".join(["?"] * len(cols))
        sql = f"INSERT INTO entries ({col_list}) VALUES ({placeholders})"
        self._conn.execute(sql, vals)

    def _update_existing(self, entry: dict) -> None:
        """Update an existing entry: increment observation_count, conditionally
        overwrite description/reasoning/keywords/references, always update
        updated_at."""
        set_parts = [
            "observation_count = observation_count + 1",
            "updated_at = ?",
        ]
        params: list = [entry.get("updated_at")]

        for col in _CONDITIONAL_UPDATE_COLS:
            key = col.strip('"')
            value = entry.get(key)
            if value is not None:
                set_parts.append(f"{col} = ?")
                params.append(value)

        params.append(entry.get("id"))
        sql = f"UPDATE entries SET {', '.join(set_parts)} WHERE id = ?"
        self._conn.execute(sql, params)

    def get_entry(self, entry_id: str) -> dict | None:
        """Retrieve a single entry by id, or ``None`` if not found."""
        cur = self._conn.execute("SELECT * FROM entries WHERE id = ?", (entry_id,))
        row = cur.fetchone()
        if row is None:
            return None
        return dict(row)

    def get_all_entries(self) -> list[dict]:
        """Return all entries as a list of dicts."""
        cur = self._conn.execute("SELECT * FROM entries")
        return [dict(row) for row in cur.fetchall()]

    def count_entries(self) -> int:
        """Return the number of entries in the database."""
        cur = self._conn.execute("SELECT COUNT(*) FROM entries")
        return cur.fetchone()[0]

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
    # Internal
    # ------------------------------------------------------------------

    def _set_pragmas(self) -> None:
        """Set connection-level PRAGMAs for performance and safety."""
        self._conn.execute("PRAGMA journal_mode = WAL")
        self._conn.execute("PRAGMA synchronous = NORMAL")
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
        target = max(MIGRATIONS) if MIGRATIONS else 0

        for version in range(current + 1, target + 1):
            migration_fn = MIGRATIONS[version]
            migration_fn(self._conn)
            self._conn.execute(
                "INSERT INTO _metadata (key, value) VALUES (?, ?) "
                "ON CONFLICT(key) DO UPDATE SET value = excluded.value",
                ("schema_version", str(version)),
            )
            self._conn.commit()
