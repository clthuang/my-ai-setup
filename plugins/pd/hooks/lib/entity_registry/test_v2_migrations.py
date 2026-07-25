"""Feature 134 NFR-4 — v2 forward-only migration chain + #060 regression pin.

The v2-generation lineage (post-cutover) never replays the v1 MIGRATIONS
chain; V2_MIGRATIONS is its own chain. Migration 2 widens the
phase_events.event_type CHECK to admit 'mini_spec' via copy-rename.
"""
from __future__ import annotations

import sqlite3

import pytest

from entity_registry import schema_v2
from entity_registry.database import EntityDatabase, _upsert_metadata
from entity_registry.server_helpers import _process_register_entity


def _make_v2_version1_file(path: str) -> None:
    """Build the cutover-shaped fixture: 9-value CHECK + v2 stamp at 1.

    Mirrors what rebuild_tool's staging produced at the live cutover.
    EntityDatabase now runs v1 migration 20 (which widens the CHECK), so
    the fixture rebuilds phase_events back to the pre-migration 9-value
    shape explicitly — the pre-migration rejection test stays non-vacuous
    no matter how either chain grows.
    """
    db = EntityDatabase(path)
    conn = db._conn
    index_sql = [
        r[0] for r in conn.execute(
            "SELECT sql FROM sqlite_master WHERE type='index' "
            "AND tbl_name='phase_events' AND sql IS NOT NULL"
        )
    ]
    conn.execute("DROP TABLE phase_events")
    conn.execute("""
        CREATE TABLE "phase_events" (
            id              INTEGER PRIMARY KEY AUTOINCREMENT,
            type_id         TEXT NOT NULL,
            project_id      TEXT NOT NULL,
            phase           TEXT,
            event_type      TEXT NOT NULL CHECK(event_type IN (
                'started', 'completed', 'skipped', 'backward',
                'entity_created', 'entity_status_changed',
                'entity_promoted', 'spawned_child', 'cascade_ready'
            )),
            timestamp       TEXT NOT NULL,
            iterations      INTEGER,
            reviewer_notes  TEXT,
            backward_reason TEXT,
            backward_target TEXT,
            source          TEXT NOT NULL DEFAULT 'live' CHECK(
                source IN ('live', 'backfill')
            ),
            created_at      TEXT NOT NULL,
            metadata        TEXT
        )
    """)
    for sql in index_sql:
        conn.execute(sql)
    _upsert_metadata(conn, "schema_generation", "v2")
    _upsert_metadata(conn, "schema_version", "1")
    conn.commit()
    db.close()


class TestV2Migration2MiniSpec:
    def test_pre_migration_check_rejects_mini_spec(self, tmp_path):
        """Non-vacuity anchor: the 9-value CHECK really rejects mini_spec
        before migration 2 runs (proves the migration is load-bearing)."""
        p = str(tmp_path / "v2v1.db")
        _make_v2_version1_file(p)
        conn = sqlite3.connect(p)
        with pytest.raises(sqlite3.IntegrityError, match="CHECK|constraint"):
            conn.execute(
                "INSERT INTO phase_events "
                "(type_id, project_id, phase, event_type, timestamp, "
                " source, created_at) "
                "VALUES ('feature:x', 'p', NULL, 'mini_spec', "
                " '2026-07-25T00:00:00Z', 'live', '2026-07-25T00:00:00Z')"
            )
        conn.close()

    def test_open_migrates_v2_file_to_version_2(self, tmp_path):
        p = str(tmp_path / "v2v1.db")
        _make_v2_version1_file(p)

        db = EntityDatabase(p)  # _migrate_v2 runs here
        version = db._conn.execute(
            "SELECT value FROM _metadata WHERE key='schema_version'"
        ).fetchone()[0]
        sql = db._conn.execute(
            "SELECT sql FROM sqlite_master WHERE name='phase_events'"
        ).fetchone()[0]
        idx = sorted(
            r[0] for r in db._conn.execute(
                "SELECT name FROM sqlite_master WHERE type='index' "
                "AND tbl_name='phase_events' AND sql IS NOT NULL"
            )
        )
        assert version == "2"
        assert version == str(schema_v2.V2_SCHEMA_VERSION)
        assert "'mini_spec'" in sql
        assert idx == [
            "idx_pe_lookup", "idx_pe_project", "idx_pe_timestamp",
            "phase_events_backfill_dedup",
        ]
        db.close()

    def test_mini_spec_append_succeeds_post_migration(self, tmp_path):
        p = str(tmp_path / "v2v1.db")
        _make_v2_version1_file(p)
        db = EntityDatabase(p)
        db.append_phase_event(
            type_id="feature:134-x",
            project_id="__unknown__",
            event_type="mini_spec",
            timestamp="2026-07-25T00:00:00Z",
            metadata={"text": "express mini-spec body"},
        )
        row = db._conn.execute(
            "SELECT metadata FROM phase_events WHERE event_type='mini_spec'"
        ).fetchone()
        assert row is not None and "express mini-spec body" in row[0]
        db.close()

    def test_reopen_is_idempotent(self, tmp_path):
        p = str(tmp_path / "v2v1.db")
        _make_v2_version1_file(p)
        db1 = EntityDatabase(p)
        n1 = db1._conn.execute("SELECT COUNT(*) FROM phase_events").fetchone()[0]
        db1.close()
        db2 = EntityDatabase(p)
        version = db2._conn.execute(
            "SELECT value FROM _metadata WHERE key='schema_version'"
        ).fetchone()[0]
        n2 = db2._conn.execute("SELECT COUNT(*) FROM phase_events").fetchone()[0]
        assert version == "2"
        assert n1 == n2
        db2.close()


class TestBacklogRegisterRegression060:
    """Backlog #060 pin: register success must mean a DURABLE row.

    The 2026-07-11 loss ("Registered: backlog:057..." returned, no row on
    ANY connection) predates the 121/132 rewrites of this path; this test
    pins the exact scenario so a regression cannot return silently.
    """

    def test_backlog_register_visible_to_separate_connection(self, tmp_path):
        p = str(tmp_path / "entities.db")
        db = EntityDatabase(p)
        ws_uuid = "00000000-0000-4000-8000-000000000060"
        now = db._now_iso()
        db._conn.execute(
            "INSERT INTO workspaces "
            "(uuid, project_id_legacy, project_root, created_at, updated_at) "
            "VALUES (?, ?, ?, ?, ?)",
            (ws_uuid, "P-060", str(tmp_path), now, now),
        )
        db._conn.commit()

        result = _process_register_entity(
            db, "backlog", "060-regression-pin", "Regression pin",
            None, None, None, None,
            project_id="__unknown__", workspace_uuid=ws_uuid,
        )
        assert "060-regression-pin" in result and "rror" not in result, result

        # THE #060 assertion: a completely separate connection to the same
        # file sees the committed row (success-before-commit would fail here).
        other = sqlite3.connect(p)
        row = other.execute(
            "SELECT type_id FROM entities WHERE type_id = ?",
            ("backlog:060-regression-pin",),
        ).fetchone()
        other.close()
        db.close()
        assert row is not None, (
            "#060 regression: register_entity reported success but the row "
            "is invisible to a separate connection"
        )
