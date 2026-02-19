"""Tests for semantic_memory.database module."""
from __future__ import annotations

import json
import struct
import sqlite3

import pytest

from semantic_memory.database import MemoryDatabase


# ---------------------------------------------------------------------------
# Helpers
# ---------------------------------------------------------------------------


def _make_entry(**overrides) -> dict:
    """Build a minimal valid entry dict, with optional overrides."""
    base = {
        "id": "abc123",
        "name": "Test pattern",
        "description": "A test description",
        "category": "patterns",
        "source": "manual",
        "keywords": json.dumps(["test", "example"]),
        "source_project": "/tmp/project",
        "created_at": "2026-01-01T00:00:00Z",
        "updated_at": "2026-01-01T00:00:00Z",
    }
    base.update(overrides)
    return base


def _make_embedding(dims: int = 768) -> bytes:
    """Create a dummy float32 embedding blob."""
    return struct.pack(f"{dims}f", *([0.1] * dims))


# ---------------------------------------------------------------------------
# Fixture
# ---------------------------------------------------------------------------


@pytest.fixture
def db():
    """Provide an in-memory MemoryDatabase, closed after test."""
    database = MemoryDatabase(":memory:")
    yield database
    database.close()


# ---------------------------------------------------------------------------
# Schema / migration tests
# ---------------------------------------------------------------------------


class TestSchemaCreation:
    def test_creates_entries_table(self, db: MemoryDatabase):
        """The entries table should exist after init."""
        cur = db._conn.execute(
            "SELECT name FROM sqlite_master WHERE type='table' AND name='entries'"
        )
        assert cur.fetchone() is not None

    def test_creates_metadata_table(self, db: MemoryDatabase):
        """The _metadata table should exist after init."""
        cur = db._conn.execute(
            "SELECT name FROM sqlite_master WHERE type='table' AND name='_metadata'"
        )
        assert cur.fetchone() is not None

    def test_schema_version_is_1(self, db: MemoryDatabase):
        assert db.get_schema_version() == 1

    def test_entries_has_16_columns(self, db: MemoryDatabase):
        cur = db._conn.execute("PRAGMA table_info(entries)")
        columns = cur.fetchall()
        assert len(columns) == 16

    def test_entries_column_names(self, db: MemoryDatabase):
        cur = db._conn.execute("PRAGMA table_info(entries)")
        col_names = [row[1] for row in cur.fetchall()]
        expected = [
            "id", "name", "description", "reasoning", "category",
            "keywords", "source", "source_project", "references",
            "observation_count", "confidence", "recall_count",
            "last_recalled_at", "embedding", "created_at", "updated_at",
        ]
        assert col_names == expected


class TestMigrationIdempotency:
    def test_opening_twice_does_not_error(self):
        """Opening two MemoryDatabase instances on same in-memory DB should
        still result in schema_version == 1 (migrations are idempotent)."""
        db1 = MemoryDatabase(":memory:")
        assert db1.get_schema_version() == 1
        db1.close()

    def test_schema_version_persists(self, tmp_path):
        """Schema version survives close and reopen."""
        db_path = str(tmp_path / "test.db")
        db1 = MemoryDatabase(db_path)
        assert db1.get_schema_version() == 1
        db1.close()

        db2 = MemoryDatabase(db_path)
        assert db2.get_schema_version() == 1
        db2.close()


# ---------------------------------------------------------------------------
# PRAGMA tests
# ---------------------------------------------------------------------------


class TestPragmas:
    def test_wal_mode(self, tmp_path):
        """WAL journal mode should be set (only works on file-based DBs)."""
        db_path = str(tmp_path / "test.db")
        database = MemoryDatabase(db_path)
        cur = database._conn.execute("PRAGMA journal_mode")
        assert cur.fetchone()[0] == "wal"
        database.close()

    def test_busy_timeout(self, db: MemoryDatabase):
        cur = db._conn.execute("PRAGMA busy_timeout")
        assert cur.fetchone()[0] == 5000

    def test_cache_size(self, db: MemoryDatabase):
        cur = db._conn.execute("PRAGMA cache_size")
        assert cur.fetchone()[0] == -8000

    def test_synchronous_normal(self, db: MemoryDatabase):
        cur = db._conn.execute("PRAGMA synchronous")
        # 1 = NORMAL
        assert cur.fetchone()[0] == 1


# ---------------------------------------------------------------------------
# Metadata tests
# ---------------------------------------------------------------------------


class TestMetadata:
    def test_get_missing_key_returns_none(self, db: MemoryDatabase):
        assert db.get_metadata("nonexistent") is None

    def test_set_and_get(self, db: MemoryDatabase):
        db.set_metadata("foo", "bar")
        assert db.get_metadata("foo") == "bar"

    def test_set_overwrites(self, db: MemoryDatabase):
        db.set_metadata("foo", "bar")
        db.set_metadata("foo", "baz")
        assert db.get_metadata("foo") == "baz"


# ---------------------------------------------------------------------------
# CRUD tests
# ---------------------------------------------------------------------------


class TestInsert:
    def test_insert_new_entry(self, db: MemoryDatabase):
        entry = _make_entry()
        db.upsert_entry(entry)
        assert db.count_entries() == 1

    def test_get_entry_returns_dict(self, db: MemoryDatabase):
        entry = _make_entry()
        db.upsert_entry(entry)
        result = db.get_entry("abc123")
        assert isinstance(result, dict)
        assert result["id"] == "abc123"
        assert result["name"] == "Test pattern"
        assert result["category"] == "patterns"
        assert result["source"] == "manual"
        assert result["observation_count"] == 1

    def test_get_entry_missing_returns_none(self, db: MemoryDatabase):
        assert db.get_entry("nonexistent") is None

    def test_insert_with_all_fields(self, db: MemoryDatabase):
        emb = _make_embedding()
        entry = _make_entry(
            reasoning="Because tests matter",
            references=json.dumps(["ref1", "ref2"]),
            confidence="high",
            recall_count=5,
            last_recalled_at="2026-02-01T00:00:00Z",
            embedding=emb,
        )
        db.upsert_entry(entry)
        result = db.get_entry("abc123")
        assert result["reasoning"] == "Because tests matter"
        assert result["references"] == json.dumps(["ref1", "ref2"])
        assert result["confidence"] == "high"
        assert result["recall_count"] == 5
        assert result["last_recalled_at"] == "2026-02-01T00:00:00Z"
        assert result["embedding"] == emb

    def test_insert_with_nullable_fields_omitted(self, db: MemoryDatabase):
        """Nullable fields default to None when not provided."""
        entry = _make_entry()
        db.upsert_entry(entry)
        result = db.get_entry("abc123")
        assert result["reasoning"] is None
        assert result["references"] is None
        assert result["last_recalled_at"] is None
        assert result["embedding"] is None


class TestUpsert:
    def test_upsert_increments_observation_count(self, db: MemoryDatabase):
        entry = _make_entry()
        db.upsert_entry(entry)
        db.upsert_entry(entry)
        result = db.get_entry("abc123")
        assert result["observation_count"] == 2

    def test_upsert_three_times(self, db: MemoryDatabase):
        entry = _make_entry()
        db.upsert_entry(entry)
        db.upsert_entry(entry)
        db.upsert_entry(entry)
        result = db.get_entry("abc123")
        assert result["observation_count"] == 3

    def test_upsert_updates_updated_at(self, db: MemoryDatabase):
        entry = _make_entry(updated_at="2026-01-01T00:00:00Z")
        db.upsert_entry(entry)

        entry2 = _make_entry(updated_at="2026-06-15T12:00:00Z")
        db.upsert_entry(entry2)

        result = db.get_entry("abc123")
        assert result["updated_at"] == "2026-06-15T12:00:00Z"

    def test_upsert_preserves_created_at(self, db: MemoryDatabase):
        entry = _make_entry(created_at="2026-01-01T00:00:00Z")
        db.upsert_entry(entry)

        entry2 = _make_entry(created_at="2026-06-15T12:00:00Z")
        db.upsert_entry(entry2)

        result = db.get_entry("abc123")
        assert result["created_at"] == "2026-01-01T00:00:00Z"

    def test_upsert_overwrites_description_if_nonnull(self, db: MemoryDatabase):
        entry = _make_entry(description="original")
        db.upsert_entry(entry)

        entry2 = _make_entry(description="updated")
        db.upsert_entry(entry2)

        result = db.get_entry("abc123")
        assert result["description"] == "updated"

    def test_upsert_keeps_description_if_null(self, db: MemoryDatabase):
        entry = _make_entry(description="original")
        db.upsert_entry(entry)

        entry2 = _make_entry()
        entry2["description"] = None
        db.upsert_entry(entry2)

        result = db.get_entry("abc123")
        assert result["description"] == "original"

    def test_upsert_overwrites_keywords_if_nonnull(self, db: MemoryDatabase):
        entry = _make_entry(keywords=json.dumps(["old"]))
        db.upsert_entry(entry)

        entry2 = _make_entry(keywords=json.dumps(["new1", "new2"]))
        db.upsert_entry(entry2)

        result = db.get_entry("abc123")
        assert json.loads(result["keywords"]) == ["new1", "new2"]

    def test_upsert_keeps_keywords_if_null(self, db: MemoryDatabase):
        entry = _make_entry(keywords=json.dumps(["keep"]))
        db.upsert_entry(entry)

        entry2 = _make_entry()
        entry2["keywords"] = None
        db.upsert_entry(entry2)

        result = db.get_entry("abc123")
        assert json.loads(result["keywords"]) == ["keep"]

    def test_upsert_overwrites_reasoning_if_nonnull(self, db: MemoryDatabase):
        entry = _make_entry(reasoning="old reasoning")
        db.upsert_entry(entry)

        entry2 = _make_entry(reasoning="new reasoning")
        db.upsert_entry(entry2)

        result = db.get_entry("abc123")
        assert result["reasoning"] == "new reasoning"

    def test_upsert_keeps_reasoning_if_null(self, db: MemoryDatabase):
        entry = _make_entry(reasoning="keep this")
        db.upsert_entry(entry)

        entry2 = _make_entry()  # reasoning not in _make_entry by default
        db.upsert_entry(entry2)

        result = db.get_entry("abc123")
        assert result["reasoning"] == "keep this"

    def test_upsert_overwrites_references_if_nonnull(self, db: MemoryDatabase):
        entry = _make_entry(references=json.dumps(["old"]))
        db.upsert_entry(entry)

        entry2 = _make_entry(references=json.dumps(["new"]))
        db.upsert_entry(entry2)

        result = db.get_entry("abc123")
        assert json.loads(result["references"]) == ["new"]

    def test_upsert_keeps_references_if_null(self, db: MemoryDatabase):
        entry = _make_entry(references=json.dumps(["keep"]))
        db.upsert_entry(entry)

        entry2 = _make_entry()  # references not in _make_entry by default
        db.upsert_entry(entry2)

        result = db.get_entry("abc123")
        assert json.loads(result["references"]) == ["keep"]

    def test_upsert_does_not_create_duplicate_rows(self, db: MemoryDatabase):
        entry = _make_entry()
        db.upsert_entry(entry)
        db.upsert_entry(entry)
        assert db.count_entries() == 1


class TestGetAllAndCount:
    def test_empty_db(self, db: MemoryDatabase):
        assert db.get_all_entries() == []
        assert db.count_entries() == 0

    def test_multiple_entries(self, db: MemoryDatabase):
        db.upsert_entry(_make_entry(id="aaa", name="first"))
        db.upsert_entry(_make_entry(id="bbb", name="second"))
        db.upsert_entry(_make_entry(id="ccc", name="third"))

        entries = db.get_all_entries()
        assert len(entries) == 3
        assert db.count_entries() == 3

    def test_get_all_returns_dicts(self, db: MemoryDatabase):
        db.upsert_entry(_make_entry())
        entries = db.get_all_entries()
        assert all(isinstance(e, dict) for e in entries)


# ---------------------------------------------------------------------------
# Constraint / validation tests
# ---------------------------------------------------------------------------


class TestConstraints:
    def test_invalid_category_rejected(self, db: MemoryDatabase):
        entry = _make_entry(category="invalid")
        with pytest.raises(sqlite3.IntegrityError):
            db.upsert_entry(entry)

    def test_invalid_source_rejected(self, db: MemoryDatabase):
        entry = _make_entry(source="invalid")
        with pytest.raises(sqlite3.IntegrityError):
            db.upsert_entry(entry)

    def test_invalid_confidence_rejected(self, db: MemoryDatabase):
        entry = _make_entry(confidence="invalid")
        with pytest.raises(sqlite3.IntegrityError):
            db.upsert_entry(entry)

    def test_valid_categories(self, db: MemoryDatabase):
        for i, cat in enumerate(["anti-patterns", "patterns", "heuristics"]):
            db.upsert_entry(_make_entry(id=f"id_{i}", category=cat))
        assert db.count_entries() == 3

    def test_valid_sources(self, db: MemoryDatabase):
        for i, src in enumerate(["retro", "session-capture", "manual", "import"]):
            db.upsert_entry(_make_entry(id=f"id_{i}", source=src))
        assert db.count_entries() == 4

    def test_valid_confidence_levels(self, db: MemoryDatabase):
        for i, conf in enumerate(["high", "medium", "low"]):
            db.upsert_entry(_make_entry(id=f"id_{i}", confidence=conf))
        assert db.count_entries() == 3


# ---------------------------------------------------------------------------
# Close test
# ---------------------------------------------------------------------------


class TestClose:
    def test_close_prevents_further_operations(self):
        database = MemoryDatabase(":memory:")
        database.close()
        with pytest.raises(Exception):
            database.count_entries()
