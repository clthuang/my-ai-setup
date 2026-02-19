"""SQLite database layer for the semantic memory system."""
from __future__ import annotations

import sqlite3
import sys
from typing import Callable

try:
    import numpy as np
    _numpy_available = True
except ImportError:  # pragma: no cover
    _numpy_available = False


def _create_initial_schema(
    conn: sqlite3.Connection,
    *,
    fts5_available: bool = False,
    **_kwargs: object,
) -> None:
    """Migration 1: create entries and _metadata tables.

    When *fts5_available* is True, also creates the ``entries_fts``
    virtual table and three triggers (INSERT/DELETE/UPDATE) to keep
    it in sync.
    """
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

    if fts5_available:
        _create_fts5_objects(conn)


# JSON-stripping REPLACE chain used in FTS5 triggers.
# Converts '["a","b"]' -> 'a b' for better tokenisation.
_KEYWORDS_STRIP = (
    "REPLACE(REPLACE(REPLACE(REPLACE("
    "COALESCE(new.keywords, ''), "
    "'[\"', ''), '\"]', ''), '\",\"', ' '), '\"', '')"
)
_KEYWORDS_STRIP_OLD = (
    "REPLACE(REPLACE(REPLACE(REPLACE("
    "COALESCE(old.keywords, ''), "
    "'[\"', ''), '\"]', ''), '\",\"', ' '), '\"', '')"
)


def _create_fts5_objects(conn: sqlite3.Connection) -> None:
    """Create the FTS5 virtual table and sync triggers."""
    conn.execute("""
        CREATE VIRTUAL TABLE IF NOT EXISTS entries_fts USING fts5(
            name, description, keywords, reasoning,
            content='entries',
            content_rowid='rowid'
        )
    """)

    conn.executescript(f"""
        CREATE TRIGGER IF NOT EXISTS entries_ai AFTER INSERT ON entries BEGIN
            INSERT INTO entries_fts(rowid, name, description, keywords, reasoning)
            VALUES (new.rowid, new.name, new.description,
                    {_KEYWORDS_STRIP},
                    new.reasoning);
        END;

        CREATE TRIGGER IF NOT EXISTS entries_ad AFTER DELETE ON entries BEGIN
            INSERT INTO entries_fts(entries_fts, rowid, name, description, keywords, reasoning)
            VALUES ('delete', old.rowid, old.name, old.description,
                    {_KEYWORDS_STRIP_OLD},
                    old.reasoning);
        END;

        CREATE TRIGGER IF NOT EXISTS entries_au AFTER UPDATE ON entries BEGIN
            INSERT INTO entries_fts(entries_fts, rowid, name, description, keywords, reasoning)
            VALUES ('delete', old.rowid, old.name, old.description,
                    {_KEYWORDS_STRIP_OLD},
                    old.reasoning);
            INSERT INTO entries_fts(rowid, name, description, keywords, reasoning)
            VALUES (new.rowid, new.name, new.description,
                    {_KEYWORDS_STRIP},
                    new.reasoning);
        END;
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
        self._conn = sqlite3.connect(db_path, timeout=5.0)
        self._conn.row_factory = sqlite3.Row
        self._set_pragmas()
        self._fts5_available = self._detect_fts5()
        self._migrate()

    # ------------------------------------------------------------------
    # Lifecycle
    # ------------------------------------------------------------------

    @property
    def fts5_available(self) -> bool:
        """Whether FTS5 full-text search is available."""
        return self._fts5_available

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

        Uses BEGIN IMMEDIATE to acquire a write lock before the
        existence check, preventing TOCTOU races under concurrent access.
        """
        self._conn.execute("BEGIN IMMEDIATE")
        try:
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
        except Exception:
            self._conn.rollback()
            raise

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

    # Columns returned by get_all_entries (everything except the embedding BLOB).
    _ALL_ENTRY_COLS = ", ".join(c for c in _COLUMNS if c != "embedding")

    def get_all_entries(self) -> list[dict]:
        """Return all entries as a list of dicts (excludes embedding BLOBs)."""
        cur = self._conn.execute(f"SELECT {self._ALL_ENTRY_COLS} FROM entries")
        return [dict(row) for row in cur.fetchall()]

    def count_entries(self) -> int:
        """Return the number of entries in the database."""
        cur = self._conn.execute("SELECT COUNT(*) FROM entries")
        return cur.fetchone()[0]

    # ------------------------------------------------------------------
    # FTS5 full-text search
    # ------------------------------------------------------------------

    def fts5_search(
        self, query: str, limit: int = 100
    ) -> list[tuple[str, float]]:
        """Search entries using FTS5 full-text search.

        Returns a list of ``(entry_id, score)`` tuples ordered by
        relevance (highest score first).  BM25 scores are negated so
        that higher values mean more relevant.

        Returns an empty list when FTS5 is unavailable or the query
        matches nothing.
        """
        if not self._fts5_available:
            return []

        try:
            cur = self._conn.execute(
                "SELECT e.id, -rank AS score "
                "FROM entries_fts f "
                "JOIN entries e ON e.rowid = f.rowid "
                "WHERE entries_fts MATCH ? "
                "ORDER BY score DESC "
                "LIMIT ?",
                (query, limit),
            )
            return [(row[0], float(row[1])) for row in cur.fetchall()]
        except sqlite3.OperationalError:
            # FTS5 MATCH syntax error from special characters in query
            return []

    # ------------------------------------------------------------------
    # Embedding helpers
    # ------------------------------------------------------------------

    def get_all_embeddings(
        self, expected_dims: int = 768
    ) -> tuple[list[str], object] | None:
        """Return all valid embeddings as ``(ids, matrix)`` or ``None``.

        *matrix* is a ``numpy.ndarray`` of shape ``(n, expected_dims)``
        with dtype ``float32``.  Entries whose BLOB length does not
        equal ``expected_dims * 4`` are silently skipped (with a
        warning on stderr).

        Returns ``None`` when there are no valid embeddings.
        """
        if not _numpy_available:  # pragma: no cover
            print(
                "semantic_memory: numpy not available, cannot load embeddings",
                file=sys.stderr,
            )
            return None

        cur = self._conn.execute(
            "SELECT id, embedding FROM entries WHERE embedding IS NOT NULL"
        )

        ids: list[str] = []
        vectors: list[object] = []
        expected_bytes = expected_dims * 4

        for row in cur.fetchall():
            blob = row[1]
            if len(blob) != expected_bytes:
                print(
                    f"semantic_memory: skipping entry {row[0]!r} — "
                    f"embedding BLOB is {len(blob)} bytes, "
                    f"expected {expected_bytes}",
                    file=sys.stderr,
                )
                continue
            ids.append(row[0])
            vectors.append(np.frombuffer(blob, dtype=np.float32))

        if not ids:
            return None

        matrix = np.stack(vectors)
        return ids, matrix

    def update_embedding(self, entry_id: str, embedding: bytes) -> None:
        """Set the embedding BLOB for a single entry."""
        self._conn.execute(
            "UPDATE entries SET embedding = ? WHERE id = ?",
            (embedding, entry_id),
        )
        self._conn.commit()

    def clear_all_embeddings(self) -> None:
        """Set the embedding column to NULL for every entry."""
        self._conn.execute("UPDATE entries SET embedding = NULL")
        self._conn.commit()

    def get_entries_without_embedding(
        self, limit: int = 50
    ) -> list[dict]:
        """Return entries that have no embedding yet.

        Returns a list of dicts with the fields needed for embedding
        generation (id, name, description, keywords, reasoning).
        """
        cur = self._conn.execute(
            "SELECT id, name, description, keywords, reasoning "
            "FROM entries "
            "WHERE embedding IS NULL "
            "LIMIT ?",
            (limit,),
        )
        return [dict(row) for row in cur.fetchall()]

    def count_entries_without_embedding(self) -> int:
        """Return the number of entries that have no embedding yet."""
        cur = self._conn.execute(
            "SELECT COUNT(*) FROM entries WHERE embedding IS NULL"
        )
        return cur.fetchone()[0]

    def update_keywords(self, entry_id: str, keywords_json: str) -> None:
        """Update the keywords for an existing entry.

        Parameters
        ----------
        entry_id:
            The entry ID to update.
        keywords_json:
            JSON-encoded keyword list.
        """
        self._conn.execute(
            "UPDATE entries SET keywords = ? WHERE id = ?",
            (keywords_json, entry_id),
        )
        self._conn.commit()

    def update_recall(
        self, entry_ids: list[str], timestamp: str
    ) -> None:
        """Increment recall_count and set last_recalled_at for entries.

        Parameters
        ----------
        entry_ids:
            List of entry IDs to update.
        timestamp:
            ISO-8601 timestamp to set as ``last_recalled_at``.
        """
        if not entry_ids:
            return

        placeholders = ", ".join(["?"] * len(entry_ids))
        self._conn.execute(
            f"UPDATE entries "
            f"SET recall_count = recall_count + 1, "
            f"    last_recalled_at = ? "
            f"WHERE id IN ({placeholders})",
            [timestamp, *entry_ids],
        )
        self._conn.commit()

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

    def _detect_fts5(self) -> bool:
        """Probe whether the SQLite build supports FTS5.

        Creates and immediately drops a throwaway virtual table.
        Returns ``True`` if successful, ``False`` otherwise (with a
        warning on stderr).
        """
        try:
            self._conn.execute(
                "CREATE VIRTUAL TABLE IF NOT EXISTS _fts5_test USING fts5(x)"
            )
            self._conn.execute("DROP TABLE IF EXISTS _fts5_test")
            return True
        except Exception:
            print(
                "semantic_memory: FTS5 is not available in this SQLite build; "
                "full-text search will be disabled",
                file=sys.stderr,
            )
            return False

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
            # Pass fts5_available to migrations that accept it.
            migration_fn(self._conn, fts5_available=self._fts5_available)
            self._conn.execute(
                "INSERT INTO _metadata (key, value) VALUES (?, ?) "
                "ON CONFLICT(key) DO UPDATE SET value = excluded.value",
                ("schema_version", str(version)),
            )
            self._conn.commit()
