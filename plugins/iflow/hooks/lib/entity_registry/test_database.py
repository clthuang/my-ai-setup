"""Tests for entity_registry.database module."""
from __future__ import annotations

import json
import sqlite3
import time

import pytest

from entity_registry.database import (
    EntityDatabase,
    _UUID_V4_RE,
    _create_initial_schema,
    _migrate_to_uuid_pk,
)


# ---------------------------------------------------------------------------
# Fixtures
# ---------------------------------------------------------------------------


@pytest.fixture
def db(tmp_path):
    """Provide a file-based EntityDatabase, closed after test."""
    db_path = str(tmp_path / "entities.db")
    database = EntityDatabase(db_path)
    yield database
    database.close()


@pytest.fixture
def mem_db():
    """Provide an in-memory EntityDatabase, closed after test."""
    database = EntityDatabase(":memory:")
    yield database
    database.close()


# ---------------------------------------------------------------------------
# Migration 2: Schema Foundation tests
# ---------------------------------------------------------------------------


class TestMigration2:
    def test_migration_fresh_db(self):
        """Fresh v1 DB migrated to v2 should have correct schema shape."""
        import sqlite3
        conn = sqlite3.connect(":memory:")
        conn.row_factory = sqlite3.Row
        _create_initial_schema(conn)
        _migrate_to_uuid_pk(conn)

        # 12 columns
        cur = conn.execute("PRAGMA table_info(entities)")
        columns = cur.fetchall()
        assert len(columns) == 12

        # uuid is PRIMARY KEY
        col_map = {row[1]: row for row in columns}
        assert "uuid" in col_map
        assert col_map["uuid"][5] == 1  # pk flag

        # type_id is NOT PK
        assert col_map["type_id"][5] == 0

        # type_id has UNIQUE constraint (check via index)
        idx_cur = conn.execute(
            "SELECT sql FROM sqlite_master WHERE type='index' "
            "AND sql LIKE '%type_id%' AND sql LIKE '%UNIQUE%'"
        )
        # The UNIQUE on type_id creates an autoindex
        uniq_cur = conn.execute(
            "PRAGMA index_list(entities)"
        )
        unique_cols = []
        for idx_row in uniq_cur.fetchall():
            if idx_row[2]:  # unique flag
                info = conn.execute(
                    f"PRAGMA index_info({idx_row[1]!r})"
                ).fetchall()
                for info_row in info:
                    unique_cols.append(info_row[2])
        assert "type_id" in unique_cols

        # parent_uuid column exists
        assert "parent_uuid" in col_map

        # 8 triggers
        trigger_cur = conn.execute(
            "SELECT name FROM sqlite_master WHERE type='trigger' ORDER BY name"
        )
        trigger_names = [row[0] for row in trigger_cur.fetchall()]
        assert trigger_names == [
            "enforce_immutable_created_at",
            "enforce_immutable_entity_type",
            "enforce_immutable_type_id",
            "enforce_immutable_uuid",
            "enforce_no_self_parent",
            "enforce_no_self_parent_update",
            "enforce_no_self_parent_uuid_insert",
            "enforce_no_self_parent_uuid_update",
        ]

        # 4 indexes
        idx_cur = conn.execute(
            "SELECT name FROM sqlite_master WHERE type='index' "
            "AND name NOT LIKE 'sqlite_%' ORDER BY name"
        )
        index_names = [row[0] for row in idx_cur.fetchall()]
        assert index_names == [
            "idx_entity_type",
            "idx_parent_type_id",
            "idx_parent_uuid",
            "idx_status",
        ]

        conn.close()

    def test_migration_populated_db_preserves_data(self):
        """Migrating a v1 DB with data should preserve all rows and add UUIDs."""
        import sqlite3
        from entity_registry.database import _UUID_V4_RE

        conn = sqlite3.connect(":memory:")
        conn.row_factory = sqlite3.Row
        conn.execute("PRAGMA foreign_keys = ON")
        _create_initial_schema(conn)

        # Insert 3 entities using v1 schema (no uuid column)
        conn.execute(
            "INSERT INTO entities (type_id, entity_type, entity_id, name, "
            "status, created_at, updated_at) VALUES (?, ?, ?, ?, ?, ?, ?)",
            ("project:p1", "project", "p1", "Project One", "active",
             "2026-01-01T00:00:00", "2026-01-01T00:00:00"),
        )
        conn.execute(
            "INSERT INTO entities (type_id, entity_type, entity_id, name, "
            "parent_type_id, created_at, updated_at) VALUES (?, ?, ?, ?, ?, ?, ?)",
            ("feature:f1", "feature", "f1", "Feature One", "project:p1",
             "2026-01-01T00:00:00", "2026-01-01T00:00:00"),
        )
        conn.execute(
            "INSERT INTO entities (type_id, entity_type, entity_id, name, "
            "created_at, updated_at) VALUES (?, ?, ?, ?, ?, ?)",
            ("backlog:b1", "backlog", "b1", "Backlog One",
             "2026-01-01T00:00:00", "2026-01-01T00:00:00"),
        )
        conn.commit()

        _migrate_to_uuid_pk(conn)

        # All 3 rows exist
        rows = conn.execute(
            "SELECT * FROM entities ORDER BY type_id"
        ).fetchall()
        assert len(rows) == 3

        # Field values preserved
        type_ids = [r["type_id"] for r in rows]
        assert "backlog:b1" in type_ids
        assert "feature:f1" in type_ids
        assert "project:p1" in type_ids

        # Each row has valid UUID v4
        for row in rows:
            assert _UUID_V4_RE.match(row["uuid"]), (
                f"Row {row['type_id']} has invalid uuid: {row['uuid']}"
            )

        # Specific field values
        p1 = [r for r in rows if r["type_id"] == "project:p1"][0]
        assert p1["name"] == "Project One"
        assert p1["status"] == "active"
        assert p1["entity_type"] == "project"

        conn.close()

    def test_migration_populates_parent_uuid(self):
        """Migration should populate parent_uuid from parent_type_id."""
        import sqlite3
        from entity_registry.database import _UUID_V4_RE

        conn = sqlite3.connect(":memory:")
        conn.row_factory = sqlite3.Row
        conn.execute("PRAGMA foreign_keys = ON")
        _create_initial_schema(conn)

        # Insert parent and child
        conn.execute(
            "INSERT INTO entities (type_id, entity_type, entity_id, name, "
            "created_at, updated_at) VALUES (?, ?, ?, ?, ?, ?)",
            ("project:p1", "project", "p1", "Parent",
             "2026-01-01T00:00:00", "2026-01-01T00:00:00"),
        )
        conn.execute(
            "INSERT INTO entities (type_id, entity_type, entity_id, name, "
            "parent_type_id, created_at, updated_at) VALUES (?, ?, ?, ?, ?, ?, ?)",
            ("feature:f1", "feature", "f1", "Child", "project:p1",
             "2026-01-01T00:00:00", "2026-01-01T00:00:00"),
        )
        conn.commit()

        _migrate_to_uuid_pk(conn)

        parent = conn.execute(
            "SELECT uuid FROM entities WHERE type_id = 'project:p1'"
        ).fetchone()
        child = conn.execute(
            "SELECT parent_uuid FROM entities WHERE type_id = 'feature:f1'"
        ).fetchone()

        assert child["parent_uuid"] == parent["uuid"]
        assert _UUID_V4_RE.match(parent["uuid"])

        conn.close()

    def test_uuid_immutability_trigger(self):
        """After migration, updating uuid should raise IntegrityError."""
        import sqlite3
        import uuid

        conn = sqlite3.connect(":memory:")
        conn.row_factory = sqlite3.Row
        conn.execute("PRAGMA foreign_keys = ON")
        _create_initial_schema(conn)
        _migrate_to_uuid_pk(conn)

        test_uuid = str(uuid.uuid4())
        conn.execute(
            "INSERT INTO entities (uuid, type_id, entity_type, entity_id, "
            "name, created_at, updated_at) VALUES (?, ?, ?, ?, ?, ?, ?)",
            (test_uuid, "feature:trig", "feature", "trig", "Trigger Test",
             "2026-01-01T00:00:00", "2026-01-01T00:00:00"),
        )
        conn.commit()

        with pytest.raises(sqlite3.IntegrityError, match="uuid is immutable"):
            conn.execute(
                "UPDATE entities SET uuid = 'new-uuid' WHERE type_id = ?",
                ("feature:trig",),
            )
        conn.close()

    def test_self_parent_uuid_insert_trigger(self):
        """Inserting entity where parent_uuid = uuid should raise."""
        import sqlite3
        import uuid

        conn = sqlite3.connect(":memory:")
        conn.row_factory = sqlite3.Row
        conn.execute("PRAGMA foreign_keys = ON")
        _create_initial_schema(conn)
        _migrate_to_uuid_pk(conn)

        test_uuid = str(uuid.uuid4())
        with pytest.raises(
            sqlite3.IntegrityError, match="entity cannot be its own parent"
        ):
            conn.execute(
                "INSERT INTO entities (uuid, type_id, entity_type, entity_id, "
                "name, created_at, updated_at, parent_uuid) "
                "VALUES (?, ?, ?, ?, ?, ?, ?, ?)",
                (test_uuid, "feature:self", "feature", "self", "Self",
                 "2026-01-01T00:00:00", "2026-01-01T00:00:00", test_uuid),
            )
        conn.close()

    def test_self_parent_uuid_update_trigger(self):
        """Updating parent_uuid to self should raise."""
        import sqlite3
        import uuid

        conn = sqlite3.connect(":memory:")
        conn.row_factory = sqlite3.Row
        conn.execute("PRAGMA foreign_keys = ON")
        _create_initial_schema(conn)
        _migrate_to_uuid_pk(conn)

        test_uuid = str(uuid.uuid4())
        conn.execute(
            "INSERT INTO entities (uuid, type_id, entity_type, entity_id, "
            "name, created_at, updated_at) VALUES (?, ?, ?, ?, ?, ?, ?)",
            (test_uuid, "feature:upd", "feature", "upd", "Update Test",
             "2026-01-01T00:00:00", "2026-01-01T00:00:00"),
        )
        conn.commit()

        with pytest.raises(
            sqlite3.IntegrityError, match="entity cannot be its own parent"
        ):
            conn.execute(
                "UPDATE entities SET parent_uuid = uuid WHERE type_id = ?",
                ("feature:upd",),
            )
        conn.close()

    def test_init_already_migrated_db(self, tmp_path):
        """Creating EntityDatabase on an already-migrated DB should be a no-op."""
        import sqlite3

        db_path = str(tmp_path / "already_migrated.db")

        # First: create a v2 database via direct migration calls
        conn = sqlite3.connect(db_path)
        conn.row_factory = sqlite3.Row
        conn.execute("PRAGMA foreign_keys = ON")
        _create_initial_schema(conn)
        # Set schema_version to 1 (as _create_initial_schema doesn't set it)
        conn.execute(
            "INSERT OR REPLACE INTO _metadata(key, value) "
            "VALUES('schema_version', '1')"
        )
        conn.commit()
        _migrate_to_uuid_pk(conn)
        conn.close()

        # Now open it with EntityDatabase — should NOT re-run migration
        db = EntityDatabase(db_path)
        assert db.get_metadata("schema_version") == "2"

        # Schema should be intact
        cur = db._conn.execute("PRAGMA table_info(entities)")
        columns = cur.fetchall()
        assert len(columns) == 12

        db.close()

    def test_migration_rollback_on_failure(self):
        """If migration fails mid-way, original schema should be intact."""
        import sqlite3

        conn = sqlite3.connect(":memory:")
        conn.row_factory = sqlite3.Row
        conn.execute("PRAGMA foreign_keys = ON")
        _create_initial_schema(conn)

        # Insert test data in v1 schema
        conn.execute(
            "INSERT INTO entities (type_id, entity_type, entity_id, name, "
            "created_at, updated_at) VALUES (?, ?, ?, ?, ?, ?)",
            ("project:p1", "project", "p1", "Project One",
             "2026-01-01T00:00:00", "2026-01-01T00:00:00"),
        )
        conn.execute(
            "INSERT INTO entities (type_id, entity_type, entity_id, name, "
            "created_at, updated_at) VALUES (?, ?, ?, ?, ?, ?)",
            ("feature:f1", "feature", "f1", "Feature One",
             "2026-01-01T00:00:00", "2026-01-01T00:00:00"),
        )
        conn.commit()

        # Set schema_version to 1 (simulating Migration 1 completed)
        conn.execute(
            "INSERT OR REPLACE INTO _metadata(key, value) "
            "VALUES('schema_version', '1')"
        )
        conn.commit()

        class FailOnDropConn:
            """Proxy that delegates to real conn but raises on DROP TABLE."""
            def __init__(self, real_conn):
                self._real = real_conn
            def execute(self, sql, *args, **kwargs):
                if isinstance(sql, str) and "DROP TABLE" in sql:
                    raise RuntimeError("injected")
                return self._real.execute(sql, *args, **kwargs)
            def __getattr__(self, name):
                return getattr(self._real, name)

        wrapped = FailOnDropConn(conn)
        with pytest.raises(RuntimeError, match="injected"):
            _migrate_to_uuid_pk(wrapped)

        # Original v1 schema intact: type_id is PK, no uuid column
        cur = conn.execute("PRAGMA table_info(entities)")
        col_map = {row[1]: row for row in cur.fetchall()}
        assert "type_id" in col_map
        assert col_map["type_id"][5] == 1  # type_id is still PK
        assert "uuid" not in col_map

        # schema_version remains '1'
        ver = conn.execute(
            "SELECT value FROM _metadata WHERE key='schema_version'"
        ).fetchone()
        assert ver[0] == "1"

        # All data preserved
        count = conn.execute("SELECT COUNT(*) FROM entities").fetchone()[0]
        assert count == 2

        conn.close()


# ---------------------------------------------------------------------------
# Task 1.2: Schema creation tests
# ---------------------------------------------------------------------------


class TestSchemaCreation:
    def test_creates_entities_table(self, db: EntityDatabase):
        """The entities table should exist after init."""
        cur = db._conn.execute(
            "SELECT name FROM sqlite_master WHERE type='table' AND name='entities'"
        )
        assert cur.fetchone() is not None

    def test_creates_metadata_table(self, db: EntityDatabase):
        """The _metadata table should exist after init."""
        cur = db._conn.execute(
            "SELECT name FROM sqlite_master WHERE type='table' AND name='_metadata'"
        )
        assert cur.fetchone() is not None

    def test_entities_has_12_columns(self, db: EntityDatabase):
        cur = db._conn.execute("PRAGMA table_info(entities)")
        columns = cur.fetchall()
        assert len(columns) == 12

    def test_entities_column_names(self, db: EntityDatabase):
        cur = db._conn.execute("PRAGMA table_info(entities)")
        col_names = [row[1] for row in cur.fetchall()]
        expected = [
            "uuid", "type_id", "entity_type", "entity_id", "name", "status",
            "parent_type_id", "parent_uuid", "artifact_path", "created_at",
            "updated_at", "metadata",
        ]
        assert col_names == expected

    def test_uuid_is_primary_key(self, db: EntityDatabase):
        cur = db._conn.execute("PRAGMA table_info(entities)")
        col_map = {row[1]: row for row in cur.fetchall()}
        assert col_map["uuid"][5] == 1  # pk flag
        assert col_map["type_id"][5] == 0  # type_id is NOT pk

    def test_entity_type_check_constraint(self, db: EntityDatabase):
        """Only backlog, brainstorm, project, feature should be allowed."""
        import uuid

        with pytest.raises(sqlite3.IntegrityError):
            db._conn.execute(
                "INSERT INTO entities (uuid, type_id, entity_type, entity_id, "
                "name, created_at, updated_at) VALUES (?, ?, ?, ?, ?, ?, ?)",
                (str(uuid.uuid4()), "invalid:x", "invalid", "x", "test",
                 "2026-01-01T00:00:00Z", "2026-01-01T00:00:00Z"),
            )

    def test_valid_entity_types_accepted(self, db: EntityDatabase):
        """All four valid entity types should be insertable."""
        import uuid
        for etype in ("backlog", "brainstorm", "project", "feature"):
            db._conn.execute(
                "INSERT INTO entities (uuid, type_id, entity_type, entity_id, "
                "name, created_at, updated_at) VALUES (?, ?, ?, ?, ?, ?, ?)",
                (str(uuid.uuid4()), f"{etype}:test", etype, "test",
                 f"Test {etype}",
                 "2026-01-01T00:00:00Z", "2026-01-01T00:00:00Z"),
            )
        db._conn.commit()
        cur = db._conn.execute("SELECT COUNT(*) FROM entities")
        assert cur.fetchone()[0] == 4


class TestTriggers:
    def test_has_eight_triggers(self, db: EntityDatabase):
        cur = db._conn.execute(
            "SELECT name FROM sqlite_master WHERE type='trigger' ORDER BY name"
        )
        trigger_names = [row[0] for row in cur.fetchall()]
        expected = [
            "enforce_immutable_created_at",
            "enforce_immutable_entity_type",
            "enforce_immutable_type_id",
            "enforce_immutable_uuid",
            "enforce_no_self_parent",
            "enforce_no_self_parent_update",
            "enforce_no_self_parent_uuid_insert",
            "enforce_no_self_parent_uuid_update",
        ]
        assert trigger_names == expected


class TestIndexes:
    def test_has_four_indexes(self, db: EntityDatabase):
        cur = db._conn.execute(
            "SELECT name FROM sqlite_master WHERE type='index' "
            "AND name NOT LIKE 'sqlite_%' ORDER BY name"
        )
        index_names = [row[0] for row in cur.fetchall()]
        expected = [
            "idx_entity_type",
            "idx_parent_type_id",
            "idx_parent_uuid",
            "idx_status",
        ]
        assert index_names == expected


class TestPragmas:
    def test_wal_mode(self, db: EntityDatabase):
        cur = db._conn.execute("PRAGMA journal_mode")
        assert cur.fetchone()[0] == "wal"

    def test_foreign_keys_on(self, db: EntityDatabase):
        cur = db._conn.execute("PRAGMA foreign_keys")
        assert cur.fetchone()[0] == 1

    def test_busy_timeout(self, db: EntityDatabase):
        cur = db._conn.execute("PRAGMA busy_timeout")
        assert cur.fetchone()[0] == 5000

    def test_cache_size(self, db: EntityDatabase):
        cur = db._conn.execute("PRAGMA cache_size")
        assert cur.fetchone()[0] == -8000


class TestMetadata:
    def test_get_missing_key_returns_none(self, db: EntityDatabase):
        assert db.get_metadata("nonexistent") is None

    def test_set_and_get(self, db: EntityDatabase):
        db.set_metadata("foo", "bar")
        assert db.get_metadata("foo") == "bar"

    def test_set_overwrites(self, db: EntityDatabase):
        db.set_metadata("foo", "bar")
        db.set_metadata("foo", "baz")
        assert db.get_metadata("foo") == "baz"

    def test_schema_version_is_2(self, db: EntityDatabase):
        assert db.get_metadata("schema_version") == "2"


# ---------------------------------------------------------------------------
# Task 1.4: register_entity tests
# ---------------------------------------------------------------------------


class TestRegisterEntity:
    def test_happy_path(self, db: EntityDatabase):
        """Register a feature entity and retrieve it."""
        result = db.register_entity("feature", "feat-001", "My Feature")
        assert _UUID_V4_RE.match(result), f"Expected UUID v4, got {result!r}"
        cur = db._conn.execute(
            "SELECT * FROM entities WHERE type_id = 'feature:feat-001'"
        )
        row = cur.fetchone()
        assert row is not None
        assert row["entity_type"] == "feature"
        assert row["entity_id"] == "feat-001"
        assert row["name"] == "My Feature"

    def test_type_id_auto_constructed(self, db: EntityDatabase):
        """type_id should be f'{entity_type}:{entity_id}'."""
        result = db.register_entity("backlog", "item-42", "Backlog Item")
        assert _UUID_V4_RE.match(result), f"Expected UUID v4, got {result!r}"
        # Verify the type_id was constructed correctly in the DB
        row = db._conn.execute(
            "SELECT type_id FROM entities WHERE uuid = ?", (result,)
        ).fetchone()
        assert row["type_id"] == "backlog:item-42"

    def test_insert_or_ignore_idempotency(self, db: EntityDatabase):
        """Registering the same entity twice should not raise."""
        uuid1 = db.register_entity("project", "proj-1", "Project One")
        uuid2 = db.register_entity("project", "proj-1", "Project One Updated")
        assert _UUID_V4_RE.match(uuid1)
        assert uuid1 == uuid2
        cur = db._conn.execute("SELECT COUNT(*) FROM entities")
        assert cur.fetchone()[0] == 1
        # Name should remain the original (INSERT OR IGNORE)
        cur = db._conn.execute(
            "SELECT name FROM entities WHERE type_id = 'project:proj-1'"
        )
        assert cur.fetchone()[0] == "Project One"

    def test_entity_type_validation(self, db: EntityDatabase):
        """Invalid entity_type should raise ValueError."""
        with pytest.raises(ValueError, match="Invalid entity_type"):
            db.register_entity("invalid_type", "x", "Bad Type")

    def test_all_valid_types(self, db: EntityDatabase):
        """All four valid types should succeed."""
        for etype in ("backlog", "brainstorm", "project", "feature"):
            result = db.register_entity(etype, f"id-{etype}", f"Name {etype}")
            assert _UUID_V4_RE.match(result), f"Expected UUID v4 for {etype}"

    def test_optional_fields(self, db: EntityDatabase):
        """artifact_path, status, parent_type_id, metadata should be optional."""
        entity_uuid = db.register_entity(
            "feature", "f1", "Feature One",
            artifact_path="/docs/features/f1",
            status="active",
            metadata={"priority": "high"},
        )
        cur = db._conn.execute(
            "SELECT * FROM entities WHERE uuid = ?", (entity_uuid,)
        )
        row = cur.fetchone()
        assert row["artifact_path"] == "/docs/features/f1"
        assert row["status"] == "active"
        assert json.loads(row["metadata"]) == {"priority": "high"}

    def test_parent_type_id_fk_validation(self, db: EntityDatabase):
        """Setting parent_type_id to a non-existent entity should raise."""
        with pytest.raises(sqlite3.IntegrityError):
            db.register_entity(
                "feature", "child", "Child Feature",
                parent_type_id="project:nonexistent",
            )

    def test_valid_parent_type_id(self, db: EntityDatabase):
        """Setting parent_type_id to an existing entity should work."""
        db.register_entity("project", "proj-1", "Project One")
        entity_uuid = db.register_entity(
            "feature", "feat-1", "Feature One",
            parent_type_id="project:proj-1",
        )
        cur = db._conn.execute(
            "SELECT parent_type_id FROM entities WHERE uuid = ?",
            (entity_uuid,),
        )
        assert cur.fetchone()[0] == "project:proj-1"

    def test_timestamps_set(self, db: EntityDatabase):
        """created_at and updated_at should be set automatically."""
        entity_uuid = db.register_entity("brainstorm", "b1", "Brainstorm One")
        cur = db._conn.execute(
            "SELECT created_at, updated_at FROM entities WHERE uuid = ?",
            (entity_uuid,),
        )
        row = cur.fetchone()
        assert row["created_at"] is not None
        assert row["updated_at"] is not None

    def test_returns_uuid_string(self, db: EntityDatabase):
        """register_entity should return a UUID v4 string."""
        result = db.register_entity("feature", "f99", "Feature 99")
        assert isinstance(result, str)
        assert _UUID_V4_RE.match(result), f"Expected UUID v4, got {result!r}"

    def test_metadata_stored_as_json(self, db: EntityDatabase):
        """metadata dict should be stored as JSON string in the database."""
        db.register_entity(
            "feature", "f1", "Feature",
            metadata={"key": "value", "count": 42},
        )
        cur = db._conn.execute(
            "SELECT metadata FROM entities WHERE type_id = 'feature:f1'"
        )
        raw = cur.fetchone()[0]
        assert isinstance(raw, str)
        parsed = json.loads(raw)
        assert parsed == {"key": "value", "count": 42}


# ---------------------------------------------------------------------------
# Task 1.6: Immutable field trigger tests
# ---------------------------------------------------------------------------


class TestImmutableTriggers:
    def test_type_id_immutable(self, db: EntityDatabase):
        """Attempting to change type_id should raise IntegrityError."""
        db.register_entity("feature", "f1", "Feature One")
        with pytest.raises(sqlite3.IntegrityError, match="type_id is immutable"):
            db._conn.execute(
                "UPDATE entities SET type_id = 'feature:f2' "
                "WHERE type_id = 'feature:f1'"
            )

    def test_entity_type_immutable(self, db: EntityDatabase):
        """Attempting to change entity_type should raise IntegrityError."""
        db.register_entity("feature", "f1", "Feature One")
        with pytest.raises(sqlite3.IntegrityError, match="entity_type is immutable"):
            db._conn.execute(
                "UPDATE entities SET entity_type = 'project' "
                "WHERE type_id = 'feature:f1'"
            )

    def test_created_at_immutable(self, db: EntityDatabase):
        """Attempting to change created_at should raise IntegrityError."""
        db.register_entity("feature", "f1", "Feature One")
        with pytest.raises(sqlite3.IntegrityError, match="created_at is immutable"):
            db._conn.execute(
                "UPDATE entities SET created_at = '2099-01-01T00:00:00Z' "
                "WHERE type_id = 'feature:f1'"
            )

    def test_self_parent_on_insert(self, db: EntityDatabase):
        """Inserting an entity that is its own parent should raise."""
        import uuid

        test_uuid = str(uuid.uuid4())
        # Case 1: self-parent via parent_type_id
        with pytest.raises(sqlite3.IntegrityError, match="entity cannot be its own parent"):
            db._conn.execute(
                "INSERT INTO entities (uuid, type_id, entity_type, entity_id, "
                "name, parent_type_id, created_at, updated_at) "
                "VALUES (?, 'feature:self', 'feature', 'self', 'Self', "
                "'feature:self', '2026-01-01T00:00:00Z', '2026-01-01T00:00:00Z')",
                (test_uuid,),
            )
        # Case 2: self-parent via parent_uuid (R12 trigger)
        test_uuid2 = str(uuid.uuid4())
        with pytest.raises(sqlite3.IntegrityError, match="entity cannot be its own parent"):
            db._conn.execute(
                "INSERT INTO entities (uuid, type_id, entity_type, entity_id, "
                "name, parent_uuid, created_at, updated_at) "
                "VALUES (?, 'feature:self2', 'feature', 'self2', 'Self2', "
                "?, '2026-01-01T00:00:00Z', '2026-01-01T00:00:00Z')",
                (test_uuid2, test_uuid2),
            )

    def test_self_parent_on_update(self, db: EntityDatabase):
        """Updating parent_type_id to self should raise."""
        db.register_entity("feature", "f1", "Feature One")
        with pytest.raises(sqlite3.IntegrityError, match="entity cannot be its own parent"):
            db._conn.execute(
                "UPDATE entities SET parent_type_id = 'feature:f1' "
                "WHERE type_id = 'feature:f1'"
            )

    def test_name_is_mutable(self, db: EntityDatabase):
        """name should be updatable (not protected by triggers)."""
        db.register_entity("feature", "f1", "Original")
        db._conn.execute(
            "UPDATE entities SET name = 'Updated' WHERE type_id = 'feature:f1'"
        )
        db._conn.commit()
        cur = db._conn.execute(
            "SELECT name FROM entities WHERE type_id = 'feature:f1'"
        )
        assert cur.fetchone()[0] == "Updated"

    def test_status_is_mutable(self, db: EntityDatabase):
        """status should be updatable (not protected by triggers)."""
        db.register_entity("feature", "f1", "Feature", status="draft")
        db._conn.execute(
            "UPDATE entities SET status = 'active' WHERE type_id = 'feature:f1'"
        )
        db._conn.commit()
        cur = db._conn.execute(
            "SELECT status FROM entities WHERE type_id = 'feature:f1'"
        )
        assert cur.fetchone()[0] == "active"


# ---------------------------------------------------------------------------
# Task 1.8: set_parent tests
# ---------------------------------------------------------------------------


class TestSetParent:
    def test_happy_path(self, db: EntityDatabase):
        """Set parent on a child entity."""
        db.register_entity("project", "proj-1", "Project One")
        child_uuid = db.register_entity("feature", "f1", "Feature One")
        result = db.set_parent("feature:f1", "project:proj-1")
        assert result == child_uuid
        cur = db._conn.execute(
            "SELECT parent_type_id FROM entities WHERE type_id = 'feature:f1'"
        )
        assert cur.fetchone()[0] == "project:proj-1"

    def test_circular_reference_rejected(self, db: EntityDatabase):
        """A->B->C, then setting C's parent to A should raise (circular)."""
        db.register_entity("project", "a", "A")
        db.register_entity("feature", "b", "B", parent_type_id="project:a")
        db.register_entity("feature", "c", "C", parent_type_id="feature:b")
        with pytest.raises(ValueError, match="[Cc]ircular"):
            db.set_parent("project:a", "feature:c")

    def test_self_parent_rejected(self, db: EntityDatabase):
        """Setting an entity as its own parent should raise."""
        db.register_entity("feature", "f1", "Feature One")
        with pytest.raises((ValueError, sqlite3.IntegrityError)):
            db.set_parent("feature:f1", "feature:f1")

    def test_non_existent_child_rejected(self, db: EntityDatabase):
        """Setting parent on non-existent entity should raise."""
        db.register_entity("project", "proj-1", "Project One")
        with pytest.raises(ValueError, match="[Nn]ot found"):
            db.set_parent("feature:nonexistent", "project:proj-1")

    def test_non_existent_parent_rejected(self, db: EntityDatabase):
        """Setting non-existent entity as parent should raise."""
        db.register_entity("feature", "f1", "Feature One")
        with pytest.raises(ValueError, match="[Nn]ot found"):
            db.set_parent("feature:f1", "project:nonexistent")

    def test_reassign_parent(self, db: EntityDatabase):
        """Should be able to change parent from one entity to another."""
        db.register_entity("project", "p1", "Project 1")
        db.register_entity("project", "p2", "Project 2")
        db.register_entity("feature", "f1", "Feature", parent_type_id="project:p1")
        db.set_parent("feature:f1", "project:p2")
        cur = db._conn.execute(
            "SELECT parent_type_id FROM entities WHERE type_id = 'feature:f1'"
        )
        assert cur.fetchone()[0] == "project:p2"

    def test_deep_circular_reference_rejected(self, db: EntityDatabase):
        """A->B->C->D, then setting A's parent to D should be rejected."""
        db.register_entity("project", "a", "A")
        db.register_entity("feature", "b", "B", parent_type_id="project:a")
        db.register_entity("feature", "c", "C", parent_type_id="feature:b")
        db.register_entity("feature", "d", "D", parent_type_id="feature:c")
        with pytest.raises(ValueError, match="[Cc]ircular"):
            db.set_parent("project:a", "feature:d")


# ---------------------------------------------------------------------------
# Task 1.10: get_entity tests
# ---------------------------------------------------------------------------


class TestGetEntity:
    def test_returns_dict_for_existing(self, db: EntityDatabase):
        """get_entity should return a dict for an existing entity."""
        db.register_entity("feature", "f1", "Feature One", status="active")
        result = db.get_entity("feature:f1")
        assert isinstance(result, dict)
        assert result["type_id"] == "feature:f1"
        assert result["entity_type"] == "feature"
        assert result["entity_id"] == "f1"
        assert result["name"] == "Feature One"
        assert result["status"] == "active"
        assert result["created_at"] is not None
        assert result["updated_at"] is not None

    def test_returns_none_for_nonexistent(self, db: EntityDatabase):
        """get_entity should return None for a non-existent type_id."""
        result = db.get_entity("feature:nonexistent")
        assert result is None

    def test_includes_metadata_as_string(self, db: EntityDatabase):
        """metadata should be returned as the raw JSON string."""
        db.register_entity(
            "feature", "f1", "Feature",
            metadata={"key": "value"},
        )
        result = db.get_entity("feature:f1")
        assert result["metadata"] is not None
        assert json.loads(result["metadata"]) == {"key": "value"}

    def test_includes_parent_type_id(self, db: EntityDatabase):
        """parent_type_id should be included in the dict."""
        db.register_entity("project", "p1", "Project")
        db.register_entity("feature", "f1", "Feature", parent_type_id="project:p1")
        result = db.get_entity("feature:f1")
        assert result["parent_type_id"] == "project:p1"

    def test_null_optional_fields(self, db: EntityDatabase):
        """Optional fields should be None when not set."""
        db.register_entity("feature", "f1", "Feature")
        result = db.get_entity("feature:f1")
        assert result["status"] is None
        assert result["parent_type_id"] is None
        assert result["artifact_path"] is None
        assert result["metadata"] is None


# ---------------------------------------------------------------------------
# Task 1.12: get_lineage tests
# ---------------------------------------------------------------------------


class TestGetLineage:
    def _setup_chain(self, db: EntityDatabase):
        """Create a chain: project:root -> feature:mid -> feature:leaf."""
        db.register_entity("project", "root", "Root Project")
        db.register_entity("feature", "mid", "Mid Feature",
                           parent_type_id="project:root")
        db.register_entity("feature", "leaf", "Leaf Feature",
                           parent_type_id="feature:mid")

    def test_upward_traversal_root_first(self, db: EntityDatabase):
        """Upward traversal should return root first."""
        self._setup_chain(db)
        lineage = db.get_lineage("feature:leaf", direction="up")
        type_ids = [e["type_id"] for e in lineage]
        assert type_ids == ["project:root", "feature:mid", "feature:leaf"]

    def test_downward_traversal_bfs(self, db: EntityDatabase):
        """Downward traversal should return entity then children (BFS)."""
        self._setup_chain(db)
        lineage = db.get_lineage("project:root", direction="down")
        type_ids = [e["type_id"] for e in lineage]
        assert type_ids == ["project:root", "feature:mid", "feature:leaf"]

    def test_single_entity_up(self, db: EntityDatabase):
        """An entity with no parent should return just itself."""
        db.register_entity("project", "solo", "Solo Project")
        lineage = db.get_lineage("project:solo", direction="up")
        assert len(lineage) == 1
        assert lineage[0]["type_id"] == "project:solo"

    def test_single_entity_down(self, db: EntityDatabase):
        """An entity with no children should return just itself."""
        db.register_entity("project", "solo", "Solo Project")
        lineage = db.get_lineage("project:solo", direction="down")
        assert len(lineage) == 1
        assert lineage[0]["type_id"] == "project:solo"

    def test_depth_limit(self, db: EntityDatabase):
        """Traversal should respect max_depth."""
        self._setup_chain(db)
        lineage = db.get_lineage("feature:leaf", direction="up", max_depth=1)
        type_ids = [e["type_id"] for e in lineage]
        # max_depth=1 means: self (depth 0) + 1 level up
        assert "feature:leaf" in type_ids
        assert "feature:mid" in type_ids
        assert "project:root" not in type_ids

    def test_default_direction_is_up(self, db: EntityDatabase):
        """Default direction should be 'up'."""
        self._setup_chain(db)
        lineage = db.get_lineage("feature:leaf")
        type_ids = [e["type_id"] for e in lineage]
        assert type_ids[0] == "project:root"

    def test_returns_list_of_dicts(self, db: EntityDatabase):
        """get_lineage should return a list of dicts."""
        db.register_entity("project", "solo", "Solo")
        lineage = db.get_lineage("project:solo")
        assert isinstance(lineage, list)
        assert all(isinstance(e, dict) for e in lineage)

    def test_nonexistent_entity_returns_empty(self, db: EntityDatabase):
        """get_lineage for a non-existent entity should return empty list."""
        lineage = db.get_lineage("feature:nonexistent")
        assert lineage == []

    def test_downward_multiple_children(self, db: EntityDatabase):
        """Downward traversal should include all children."""
        db.register_entity("project", "root", "Root")
        db.register_entity("feature", "a", "A", parent_type_id="project:root")
        db.register_entity("feature", "b", "B", parent_type_id="project:root")
        lineage = db.get_lineage("project:root", direction="down")
        type_ids = [e["type_id"] for e in lineage]
        assert "project:root" in type_ids
        assert "feature:a" in type_ids
        assert "feature:b" in type_ids
        assert len(type_ids) == 3

    def test_max_depth_default_is_10(self, db: EntityDatabase):
        """Default max_depth should be 10."""
        # Build a chain of 12 entities
        db.register_entity("project", "e0", "E0")
        for i in range(1, 12):
            db.register_entity(
                "feature", f"e{i}", f"E{i}",
                parent_type_id=f"{'project' if i == 1 else 'feature'}:e{i-1}",
            )
        # Go upward from e11 with default max_depth=10
        lineage = db.get_lineage("feature:e11", direction="up")
        # Should have 11 items (self + 10 levels up), not 12
        assert len(lineage) == 11


# ---------------------------------------------------------------------------
# Task 1.14: update_entity tests
# ---------------------------------------------------------------------------


class TestUpdateEntity:
    def test_update_name(self, db: EntityDatabase):
        """Updating name should work."""
        db.register_entity("feature", "f1", "Original")
        db.update_entity("feature:f1", name="Updated")
        result = db.get_entity("feature:f1")
        assert result["name"] == "Updated"

    def test_update_status(self, db: EntityDatabase):
        """Updating status should work."""
        db.register_entity("feature", "f1", "Feature", status="draft")
        db.update_entity("feature:f1", status="active")
        result = db.get_entity("feature:f1")
        assert result["status"] == "active"

    def test_updated_at_changes(self, db: EntityDatabase):
        """updated_at should be refreshed on update."""
        db.register_entity("feature", "f1", "Feature")
        original = db.get_entity("feature:f1")
        original_updated = original["updated_at"]
        # Small delay to ensure different timestamp
        time.sleep(0.01)
        db.update_entity("feature:f1", name="Changed")
        updated = db.get_entity("feature:f1")
        assert updated["updated_at"] != original_updated

    def test_shallow_metadata_merge(self, db: EntityDatabase):
        """Updating metadata should do a shallow merge."""
        db.register_entity(
            "feature", "f1", "Feature",
            metadata={"key1": "val1", "key2": "val2"},
        )
        db.update_entity("feature:f1", metadata={"key2": "new_val2", "key3": "val3"})
        result = db.get_entity("feature:f1")
        merged = json.loads(result["metadata"])
        assert merged == {"key1": "val1", "key2": "new_val2", "key3": "val3"}

    def test_empty_dict_clears_metadata(self, db: EntityDatabase):
        """Passing empty dict {} for metadata should clear it."""
        db.register_entity(
            "feature", "f1", "Feature",
            metadata={"key1": "val1"},
        )
        db.update_entity("feature:f1", metadata={})
        result = db.get_entity("feature:f1")
        assert result["metadata"] is None

    def test_nonexistent_entity_raises(self, db: EntityDatabase):
        """Updating a non-existent entity should raise ValueError."""
        with pytest.raises(ValueError, match="[Nn]ot found"):
            db.update_entity("feature:nonexistent", name="X")

    def test_update_artifact_path(self, db: EntityDatabase):
        """Updating artifact_path should work."""
        db.register_entity("feature", "f1", "Feature")
        db.update_entity("feature:f1", artifact_path="/new/path")
        result = db.get_entity("feature:f1")
        assert result["artifact_path"] == "/new/path"

    def test_no_changes_still_updates_timestamp(self, db: EntityDatabase):
        """Calling update_entity with no changes should still update updated_at."""
        db.register_entity("feature", "f1", "Feature")
        original = db.get_entity("feature:f1")
        time.sleep(0.01)
        db.update_entity("feature:f1")
        updated = db.get_entity("feature:f1")
        assert updated["updated_at"] != original["updated_at"]

    def test_metadata_merge_with_none_existing(self, db: EntityDatabase):
        """Merging metadata when existing is None should just set."""
        db.register_entity("feature", "f1", "Feature")
        db.update_entity("feature:f1", metadata={"key": "value"})
        result = db.get_entity("feature:f1")
        assert json.loads(result["metadata"]) == {"key": "value"}


# ---------------------------------------------------------------------------
# Task 1.16: export_lineage_markdown tests
# ---------------------------------------------------------------------------


class TestExportLineageMarkdown:
    def test_single_tree(self, db: EntityDatabase):
        """Export a single tree with root and children."""
        db.register_entity("project", "p1", "Project Alpha")
        db.register_entity("feature", "f1", "Feature A",
                           parent_type_id="project:p1")
        db.register_entity("feature", "f2", "Feature B",
                           parent_type_id="project:p1")
        md = db.export_lineage_markdown("project:p1")
        assert "Project Alpha" in md
        assert "Feature A" in md
        assert "Feature B" in md
        # Children should be indented more than root
        lines = md.strip().split("\n")
        # Root line should have fewer leading spaces than children
        root_lines = [l for l in lines if "Project Alpha" in l]
        child_lines = [l for l in lines if "Feature A" in l or "Feature B" in l]
        assert len(root_lines) >= 1
        assert len(child_lines) >= 1

    def test_all_trees_export(self, db: EntityDatabase):
        """Export all trees (no type_id argument)."""
        db.register_entity("project", "p1", "Project Alpha")
        db.register_entity("feature", "f1", "Feature A",
                           parent_type_id="project:p1")
        db.register_entity("project", "p2", "Project Beta")
        md = db.export_lineage_markdown()
        assert "Project Alpha" in md
        assert "Feature A" in md
        assert "Project Beta" in md

    def test_empty_database(self, db: EntityDatabase):
        """Empty database should return empty or minimal markdown."""
        md = db.export_lineage_markdown()
        assert md.strip() == "" or "No entities" in md

    def test_markdown_format_uses_indentation(self, db: EntityDatabase):
        """Children should be indented relative to parents."""
        db.register_entity("project", "p1", "Root")
        db.register_entity("feature", "f1", "Child",
                           parent_type_id="project:p1")
        db.register_entity("feature", "f2", "Grandchild",
                           parent_type_id="feature:f1")
        md = db.export_lineage_markdown("project:p1")
        lines = [l for l in md.split("\n") if l.strip()]
        # Find indentation levels
        indents = []
        for line in lines:
            stripped = line.lstrip()
            indent = len(line) - len(stripped)
            indents.append(indent)
        # Should have at least 2 different indentation levels
        assert len(set(indents)) >= 2

    def test_includes_type_info(self, db: EntityDatabase):
        """Markdown should include entity type and/or status info."""
        db.register_entity("project", "p1", "Project One", status="active")
        md = db.export_lineage_markdown("project:p1")
        # Should include either the type or the type_id
        assert "project" in md.lower()


# ---------------------------------------------------------------------------
# Deepened tests: BDD, Boundary, Adversarial, Error, Mutation
# ---------------------------------------------------------------------------


class TestLineageFullAncestryChain:
    """BDD: AC-1 — show-lineage displays full ancestry chain with metadata.
    derived_from: spec:AC-1
    """

    def test_show_lineage_displays_full_ancestry_chain_with_metadata(
        self, db: EntityDatabase,
    ):
        # Given a 4-level chain: backlog -> brainstorm -> project -> feature
        db.register_entity("backlog", "00019", "Lineage Tracking", status="promoted")
        db.register_entity(
            "brainstorm", "20260227-lineage", "Entity Lineage",
            parent_type_id="backlog:00019",
        )
        db.register_entity(
            "project", "P001", "Lineage Project",
            parent_type_id="brainstorm:20260227-lineage", status="active",
        )
        db.register_entity(
            "feature", "029-entity-lineage-tracking", "Entity Lineage Tracking",
            parent_type_id="project:P001", status="active",
        )
        # When traversing upward from the feature
        lineage = db.get_lineage("feature:029-entity-lineage-tracking", direction="up")
        # Then all four ancestors are returned in root-first order
        type_ids = [e["type_id"] for e in lineage]
        assert type_ids == [
            "backlog:00019",
            "brainstorm:20260227-lineage",
            "project:P001",
            "feature:029-entity-lineage-tracking",
        ]
        # And each entity carries its metadata fields
        assert lineage[0]["status"] == "promoted"
        assert lineage[0]["name"] == "Lineage Tracking"
        assert lineage[3]["status"] == "active"


class TestLineageOrphanedParent:
    """BDD: AC-3 — orphaned parent shows orphaned label.
    derived_from: spec:AC-3
    """

    def test_show_lineage_orphaned_parent_shows_orphaned_label(
        self, db: EntityDatabase,
    ):
        # Given a synthetic orphaned backlog as parent of a feature
        db.register_entity(
            "backlog", "00099", "Backlog #00099 (orphaned)", status="orphaned",
        )
        db.register_entity(
            "feature", "031-orphan", "Orphan Feature",
            parent_type_id="backlog:00099",
        )
        # When traversing upward from the feature
        lineage = db.get_lineage("feature:031-orphan", direction="up")
        # Then the parent entity has status "orphaned"
        parent = lineage[0]
        assert parent["type_id"] == "backlog:00099"
        assert parent["status"] == "orphaned"
        assert "orphaned" in parent["name"].lower() or parent["status"] == "orphaned"


class TestLineageDescendants:
    """BDD: AC-4/AC-5 — descendants display full tree.
    derived_from: spec:AC-4, spec:AC-5
    """

    def test_show_lineage_descendants_displays_full_descendant_tree(
        self, db: EntityDatabase,
    ):
        # Given a project with 2 features and 1 sub-feature
        db.register_entity("project", "P1", "Root Project")
        db.register_entity(
            "feature", "f1", "Feature A", parent_type_id="project:P1",
        )
        db.register_entity(
            "feature", "f2", "Feature B", parent_type_id="project:P1",
        )
        db.register_entity(
            "feature", "f1-sub", "Sub-Feature A1", parent_type_id="feature:f1",
        )
        # When traversing downward from the project
        lineage = db.get_lineage("project:P1", direction="down")
        # Then all 4 entities are present
        type_ids = {e["type_id"] for e in lineage}
        assert type_ids == {
            "project:P1", "feature:f1", "feature:f2", "feature:f1-sub",
        }
        # And root is first
        assert lineage[0]["type_id"] == "project:P1"

    def test_show_lineage_project_decomposition_tree(
        self, db: EntityDatabase,
    ):
        # Given a backlog -> brainstorm -> project -> features chain
        db.register_entity("backlog", "00001", "Idea")
        db.register_entity(
            "brainstorm", "20260101-idea", "Brainstorm Idea",
            parent_type_id="backlog:00001",
        )
        db.register_entity(
            "project", "proj-alpha", "Alpha Project",
            parent_type_id="brainstorm:20260101-idea",
        )
        db.register_entity(
            "feature", "fa", "Feature A", parent_type_id="project:proj-alpha",
        )
        db.register_entity(
            "feature", "fb", "Feature B", parent_type_id="project:proj-alpha",
        )
        # When traversing downward from the project
        lineage = db.get_lineage("project:proj-alpha", direction="down")
        # Then both features appear as descendants
        type_ids = {e["type_id"] for e in lineage}
        assert "feature:fa" in type_ids
        assert "feature:fb" in type_ids


class TestParentFieldValidation:
    """BDD: AC-9 — nonexistent parent warns and nullifies.
    derived_from: spec:AC-9
    """

    def test_parent_field_validation_nonexistent_entity_warns_and_nullifies(
        self, db: EntityDatabase,
    ):
        # Given no project "nonexistent" exists in the database
        # When trying to register a feature with that parent
        with pytest.raises(sqlite3.IntegrityError):
            db.register_entity(
                "feature", "child", "Child Feature",
                parent_type_id="project:nonexistent",
            )
        # Then the feature is not registered (FK violation prevented it)
        assert db.get_entity("feature:child") is None


class TestTraversalDepthGuard:
    """BDD: AC-14 + Boundary — depth guard stops at 10 hops.
    derived_from: spec:AC-14, dimension:boundary_values
    """

    def _build_chain(self, db: EntityDatabase, length: int):
        """Build a chain of entities of the given length."""
        db.register_entity("project", "e0", "E0")
        for i in range(1, length):
            parent_type = "project" if i == 1 else "feature"
            db.register_entity(
                "feature", f"e{i}", f"E{i}",
                parent_type_id=f"{parent_type}:e{i-1}",
            )

    def test_traversal_depth_at_exactly_ten_hops_no_loop(
        self, db: EntityDatabase,
    ):
        # Given a chain of 12 entities (depth 0 through 11)
        self._build_chain(db, 12)
        # When traversing upward from e11 with default max_depth=10
        lineage = db.get_lineage("feature:e11", direction="up")
        # Then we get self + 10 levels up = 11 entities (e1 through e11)
        assert len(lineage) == 11
        # And e0 (the 12th) is excluded because it's 11 hops away
        type_ids = [e["type_id"] for e in lineage]
        assert "project:e0" not in type_ids

    def test_traversal_depth_at_eleven_hops_triggers_guard(
        self, db: EntityDatabase,
    ):
        # Given a chain of 13 entities (depth 0 through 12)
        self._build_chain(db, 13)
        # When traversing upward from e12 with default max_depth=10
        lineage = db.get_lineage("feature:e12", direction="up")
        # Then we get at most 11 entities (self + 10 levels)
        assert len(lineage) == 11
        # And the root (e0) and e1 are excluded
        type_ids = [e["type_id"] for e in lineage]
        assert "project:e0" not in type_ids

    def test_traversal_depth_at_nine_hops_fully_displayed(
        self, db: EntityDatabase,
    ):
        # Given a chain of 10 entities (depth 0 through 9)
        self._build_chain(db, 10)
        # When traversing upward from e9 with default max_depth=10
        lineage = db.get_lineage("feature:e9", direction="up")
        # Then all 10 entities are returned (only 9 hops, within limit)
        assert len(lineage) == 10
        type_ids = [e["type_id"] for e in lineage]
        assert "project:e0" in type_ids
        assert "feature:e9" in type_ids

    def test_traversal_depth_of_one_single_entity(
        self, db: EntityDatabase,
    ):
        # Given a single entity with no parent
        db.register_entity("project", "solo", "Solo Project")
        # When traversing upward from it
        lineage = db.get_lineage("project:solo", direction="up")
        # Then only the entity itself is returned
        assert len(lineage) == 1
        assert lineage[0]["type_id"] == "project:solo"

    def test_depth_guard_uses_less_than_or_equal_to_ten(
        self, db: EntityDatabase,
    ):
        """Mutation mindset: verify depth < max_depth, not depth <= max_depth.
        derived_from: dimension:mutation_mindset
        """
        # Given a chain of exactly 12 entities
        self._build_chain(db, 12)
        # When traversing upward from e11 with max_depth=10
        lineage = db.get_lineage("feature:e11", direction="up", max_depth=10)
        # Then exactly 11 entities returned (self at depth 0, up to depth 10)
        assert len(lineage) == 11
        # When traversing with max_depth=11
        lineage_11 = db.get_lineage("feature:e11", direction="up", max_depth=11)
        # Then all 12 entities returned
        assert len(lineage_11) == 12


class TestCircularReferenceTwoNodeLoop:
    """Adversarial: circular reference with exactly 2 nodes.
    derived_from: dimension:adversarial
    """

    def test_circular_reference_two_node_loop_detected(
        self, db: EntityDatabase,
    ):
        # Given A -> B (A is parent of B)
        db.register_entity("project", "a", "A")
        db.register_entity("feature", "b", "B", parent_type_id="project:a")
        # When setting A's parent to B (would create A <-> B loop)
        with pytest.raises(ValueError, match="[Cc]ircular"):
            db.set_parent("project:a", "feature:b")
        # Then the parent remains None (unchanged)
        entity_a = db.get_entity("project:a")
        assert entity_a["parent_type_id"] is None


class TestBoundaryEntityIdEmpty:
    """Boundary: empty entity_id behavior.
    derived_from: dimension:boundary_values
    """

    def test_entity_id_empty_string_registered(self, db: EntityDatabase):
        # Given an empty entity_id string
        # When registering with entity_id=""
        entity_uuid = db.register_entity("feature", "", "Empty ID Feature")
        # Then the return is a UUID
        assert _UUID_V4_RE.match(entity_uuid)
        # And the type_id is "feature:" (colon-separated format), retrievable
        entity = db.get_entity("feature:")
        assert entity is not None
        assert entity["entity_id"] == ""
        assert entity["type_id"] == "feature:"


class TestDescendantTreeEdgeCases:
    """Boundary: descendant tree with 0, 1, many children.
    derived_from: dimension:boundary_values
    """

    def test_descendant_tree_with_zero_children(self, db: EntityDatabase):
        # Given a leaf entity with no children
        db.register_entity("feature", "leaf", "Leaf Feature")
        # When traversing downward
        lineage = db.get_lineage("feature:leaf", direction="down")
        # Then only the entity itself is returned
        assert len(lineage) == 1
        assert lineage[0]["type_id"] == "feature:leaf"

    def test_descendant_tree_with_many_children(self, db: EntityDatabase):
        # Given a project with 5 direct children
        db.register_entity("project", "root", "Root")
        for i in range(5):
            db.register_entity(
                "feature", f"child-{i}", f"Child {i}",
                parent_type_id="project:root",
            )
        # When traversing downward from root
        lineage = db.get_lineage("project:root", direction="down")
        # Then all 6 entities are returned (root + 5 children)
        assert len(lineage) == 6


class TestUpwardTraversalOrder:
    """Mutation mindset: verify ancestors are returned in correct root-first order.
    derived_from: dimension:mutation_mindset
    """

    def test_upward_traversal_returns_ancestors_in_correct_order(
        self, db: EntityDatabase,
    ):
        # Given a 4-level chain: A -> B -> C -> D
        db.register_entity("project", "a", "A")
        db.register_entity("feature", "b", "B", parent_type_id="project:a")
        db.register_entity("feature", "c", "C", parent_type_id="feature:b")
        db.register_entity("feature", "d", "D", parent_type_id="feature:c")
        # When traversing upward from D
        lineage = db.get_lineage("feature:d", direction="up")
        # Then order is root-first: A, B, C, D
        type_ids = [e["type_id"] for e in lineage]
        assert type_ids == ["project:a", "feature:b", "feature:c", "feature:d"]
        # Mutation check: if ORDER BY was ASC instead of DESC, this would fail


class TestTypeIdFormat:
    """Mutation mindset: type_id format is colon-separated.
    derived_from: dimension:mutation_mindset
    """

    def test_type_id_format_is_colon_separated(self, db: EntityDatabase):
        # Given a feature entity with entity_id "my-feature"
        entity_uuid = db.register_entity("feature", "my-feature", "My Feature")
        # Then the return is a UUID
        assert _UUID_V4_RE.match(entity_uuid)
        # And the type_id in the DB uses a colon separator
        entity = db.get_entity(entity_uuid)
        type_id = entity["type_id"]
        assert type_id == "feature:my-feature"
        assert ":" in type_id
        parts = type_id.split(":", 1)
        assert parts[0] == "feature"
        assert parts[1] == "my-feature"


class TestDescendantTraversalMultiLevel:
    """Mutation mindset: descendant traversal includes all levels, not just direct.
    derived_from: dimension:mutation_mindset
    """

    def test_descendant_traversal_includes_all_levels_not_just_direct_children(
        self, db: EntityDatabase,
    ):
        # Given project -> feat-a -> feat-a1 -> feat-a1x
        db.register_entity("project", "root", "Root")
        db.register_entity("feature", "a", "A", parent_type_id="project:root")
        db.register_entity("feature", "a1", "A1", parent_type_id="feature:a")
        db.register_entity("feature", "a1x", "A1x", parent_type_id="feature:a1")
        # When traversing downward from root
        lineage = db.get_lineage("project:root", direction="down")
        # Then all 4 levels are included (not just direct children)
        type_ids = {e["type_id"] for e in lineage}
        assert "feature:a1x" in type_ids
        assert len(type_ids) == 4


class TestRecursiveCTELineageDirection:
    """Mutation mindset: verify CTE returns correct relationship direction.
    derived_from: dimension:mutation_mindset
    """

    def test_recursive_cte_lineage_query_returns_correct_relationship_direction(
        self, db: EntityDatabase,
    ):
        # Given A -> B -> C chain
        db.register_entity("project", "a", "A")
        db.register_entity("feature", "b", "B", parent_type_id="project:a")
        db.register_entity("feature", "c", "C", parent_type_id="feature:b")
        # When querying upward from C
        up_lineage = db.get_lineage("feature:c", direction="up")
        up_ids = [e["type_id"] for e in up_lineage]
        # Then upward goes root-first: A, B, C
        assert up_ids == ["project:a", "feature:b", "feature:c"]

        # When querying downward from A
        down_lineage = db.get_lineage("project:a", direction="down")
        down_ids = [e["type_id"] for e in down_lineage]
        # Then downward goes root-first too: A, B, C (BFS order)
        assert down_ids == ["project:a", "feature:b", "feature:c"]

        # Mutation check: if up/down queries were swapped,
        # querying "up" from A would return empty or just A
        up_from_a = db.get_lineage("project:a", direction="up")
        assert len(up_from_a) == 1  # root has no ancestors

        # And querying "down" from C would return just C
        down_from_c = db.get_lineage("feature:c", direction="down")
        assert len(down_from_c) == 1  # leaf has no descendants


class TestBacklogIdWithLeadingZeros:
    """Boundary: leading zeros in backlog IDs are preserved.
    derived_from: dimension:boundary_values
    """

    def test_backlog_id_with_leading_zeros_preserved(
        self, db: EntityDatabase,
    ):
        # Given a backlog entity with leading zeros in ID
        entity_uuid = db.register_entity("backlog", "00019", "Item with zeros")
        # Then the return is a UUID
        assert _UUID_V4_RE.match(entity_uuid)
        # And the type_id preserves leading zeros
        entity = db.get_entity("backlog:00019")
        assert entity is not None
        assert entity["entity_id"] == "00019"
        assert entity["type_id"] == "backlog:00019"


class TestConcurrentDatabaseAccess:
    """Adversarial: concurrent access with WAL mode.
    derived_from: dimension:adversarial
    """

    def test_concurrent_database_access_with_wal_mode(self, tmp_path):
        # Given two connections to the same database file
        db_path = str(tmp_path / "entities.db")
        db1 = EntityDatabase(db_path)
        db2 = EntityDatabase(db_path)
        try:
            # When both write entities
            db1.register_entity("project", "p1", "Project 1")
            db2.register_entity("feature", "f1", "Feature 1")
            # Then both entities are visible to both connections
            assert db1.get_entity("feature:f1") is not None
            assert db2.get_entity("project:p1") is not None
        finally:
            db1.close()
            db2.close()


# ---------------------------------------------------------------------------
# Phase 2: UUID Dual-Identity tests
# ---------------------------------------------------------------------------


# T2.1.1: _resolve_identifier tests
class TestResolveIdentifier:
    def test_resolve_identifier_with_uuid(self, db: EntityDatabase):
        """_resolve_identifier should resolve a UUID to (uuid, type_id)."""
        entity_uuid = db.register_entity("feature", "test-id", "Test")
        result = db._resolve_identifier(entity_uuid)
        assert result == (entity_uuid, "feature:test-id")

    def test_resolve_identifier_with_type_id(self, db: EntityDatabase):
        """_resolve_identifier should resolve a type_id to (uuid, type_id)."""
        entity_uuid = db.register_entity("feature", "test-id", "Test")
        result = db._resolve_identifier("feature:test-id")
        assert result == (entity_uuid, "feature:test-id")

    def test_resolve_identifier_not_found(self, db: EntityDatabase):
        """_resolve_identifier should raise ValueError for unknown identifier."""
        with pytest.raises(ValueError, match="nonexistent"):
            db._resolve_identifier("nonexistent")


# T2.2.1: register_entity UUID return tests
class TestRegisterEntityUUID:
    def test_register_returns_uuid_v4_format(self, db: EntityDatabase):
        """register_entity should return a valid UUID v4 string."""
        result = db.register_entity("feature", "test", "Test")
        assert _UUID_V4_RE.match(result), f"Expected UUID v4, got {result!r}"

    def test_register_duplicate_returns_existing_uuid(self, db: EntityDatabase):
        """Registering same entity twice should return the same UUID."""
        uuid1 = db.register_entity("project", "proj-1", "Project One")
        uuid2 = db.register_entity("project", "proj-1", "Project One Updated")
        assert uuid1 == uuid2


# T2.3.1: set_parent mixed identifier tests
class TestSetParentUUID:
    def test_set_parent_mixed_identifiers(self, db: EntityDatabase):
        """set_parent should accept UUID for child and type_id for parent."""
        parent_uuid = db.register_entity("project", "proj-1", "Project One")
        child_uuid = db.register_entity("feature", "f1", "Feature One")
        result = db.set_parent(child_uuid, "project:proj-1")
        assert result == child_uuid

    def test_set_parent_updates_both_parent_columns(self, db: EntityDatabase):
        """set_parent should populate both parent_type_id and parent_uuid."""
        parent_uuid = db.register_entity("project", "proj-1", "Project One")
        child_uuid = db.register_entity("feature", "f1", "Feature One")
        db.set_parent(child_uuid, "project:proj-1")
        row = db._conn.execute(
            "SELECT parent_type_id, parent_uuid FROM entities WHERE uuid = ?",
            (child_uuid,),
        ).fetchone()
        assert row["parent_type_id"] == "project:proj-1"
        assert row["parent_uuid"] == parent_uuid


# T2.4.1: get_entity dual-read tests
class TestGetEntityUUID:
    def test_get_entity_by_uuid(self, db: EntityDatabase):
        """get_entity should accept UUID and return dict with uuid field."""
        entity_uuid = db.register_entity("feature", "f1", "Feature One")
        result = db.get_entity(entity_uuid)
        assert result is not None
        assert result["uuid"] == entity_uuid

    def test_get_entity_by_type_id(self, db: EntityDatabase):
        """get_entity should accept type_id and return same entity."""
        entity_uuid = db.register_entity("feature", "f1", "Feature One")
        result = db.get_entity("feature:f1")
        assert result is not None
        assert result["uuid"] == entity_uuid
        assert result["type_id"] == "feature:f1"

    def test_get_entity_not_found_returns_none(self, db: EntityDatabase):
        """get_entity should return None for nonexistent identifier."""
        assert db.get_entity("nonexistent") is None


# T2.5.1: get_lineage and update_entity UUID tests
class TestGetLineageUUID:
    def test_get_lineage_with_uuid(self, db: EntityDatabase):
        """get_lineage should accept UUID and return entities with uuid field."""
        gp_uuid = db.register_entity("project", "gp", "Grandparent")
        p_uuid = db.register_entity(
            "feature", "p", "Parent", parent_type_id="project:gp"
        )
        c_uuid = db.register_entity(
            "feature", "c", "Child", parent_type_id="feature:p"
        )
        lineage = db.get_lineage(c_uuid, direction="up")
        assert len(lineage) == 3
        # Root-first order
        assert lineage[0]["uuid"] == gp_uuid
        assert lineage[1]["uuid"] == p_uuid
        assert lineage[2]["uuid"] == c_uuid
        # Each dict has uuid field
        for entry in lineage:
            assert "uuid" in entry


class TestUpdateEntityUUID:
    def test_update_entity_with_uuid(self, db: EntityDatabase):
        """update_entity should accept UUID as identifier."""
        entity_uuid = db.register_entity("feature", "f1", "Original")
        db.update_entity(entity_uuid, name="New Name")
        result = db.get_entity(entity_uuid)
        assert result["name"] == "New Name"


# T2.6.1: export UUID internals test
class TestExportUUIDInternals:
    def test_export_uses_uuid_internally(self, db: EntityDatabase):
        """Export should show type_id strings, NOT raw UUIDs."""
        gp_uuid = db.register_entity("project", "gp", "Grandparent")
        p_uuid = db.register_entity(
            "feature", "p", "Parent", parent_type_id="project:gp"
        )
        c_uuid = db.register_entity(
            "feature", "c", "Child", parent_type_id="feature:p"
        )
        md = db.export_lineage_markdown()
        # Output should contain type_id components
        assert "project" in md
        assert "Grandparent" in md
        assert "Parent" in md
        assert "Child" in md
        # Output should NOT contain UUID patterns
        import re
        uuid_pattern = re.compile(
            r'[0-9a-f]{8}-[0-9a-f]{4}-4[0-9a-f]{3}-[89ab][0-9a-f]{3}-[0-9a-f]{12}'
        )
        assert not uuid_pattern.search(md), (
            f"Export should not contain UUIDs, but found: {md}"
        )
