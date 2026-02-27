"""Tests for entity_registry.backfill module."""
from __future__ import annotations

import json
import os

import pytest

from entity_registry.database import EntityDatabase


# ---------------------------------------------------------------------------
# Fixtures
# ---------------------------------------------------------------------------


@pytest.fixture
def artifacts(tmp_path):
    """Build mock artifact directories and return (artifacts_root, db) tuple.

    Directory layout:
        features/029-entity-lineage-tracking/.meta.json
        brainstorms/20260227-lineage.prd.md
        projects/  (empty)
        backlog.md
    """
    # --- features ---
    feat_dir = tmp_path / "features" / "029-entity-lineage-tracking"
    feat_dir.mkdir(parents=True)
    meta = {
        "id": "029",
        "slug": "entity-lineage-tracking",
        "brainstorm_source": "docs/brainstorms/20260227-lineage.prd.md",
        "backlog_source": "00019",
    }
    (feat_dir / ".meta.json").write_text(json.dumps(meta))

    # --- brainstorms ---
    bs_dir = tmp_path / "brainstorms"
    bs_dir.mkdir()
    (bs_dir / "20260227-lineage.prd.md").write_text(
        "# Brainstorm\n\n*Source: Backlog #00019*\n\nSome content.\n"
    )

    # --- projects (empty) ---
    (tmp_path / "projects").mkdir()

    # --- backlog.md ---
    backlog_md = (
        "# Backlog\n\n"
        "| ID | Timestamp | Description |\n"
        "|----|-----------|-------------|\n"
        "| 00019 | 2026-02-27T05:00:00Z | Entity lineage tracking |\n"
    )
    (tmp_path / "backlog.md").write_text(backlog_md)

    # --- database ---
    db = EntityDatabase(str(tmp_path / "test.db"))
    yield tmp_path, db
    db.close()


# ---------------------------------------------------------------------------
# Task 3.1: Smoke test for fixtures
# ---------------------------------------------------------------------------


def test_fixtures_smoke(artifacts):
    """Verify the test fixture builds the expected directory structure."""
    root, db = artifacts

    meta_path = root / "features" / "029-entity-lineage-tracking" / ".meta.json"
    assert meta_path.exists()

    meta = json.loads(meta_path.read_text())
    assert "brainstorm_source" in meta
    assert meta["id"] == "029"
    assert meta["slug"] == "entity-lineage-tracking"


# ---------------------------------------------------------------------------
# Task 3.2: Topological ordering tests
# ---------------------------------------------------------------------------


class TestScanOrder:
    def test_backlog_registered_before_brainstorms(self, artifacts):
        """Backlog items should exist in DB before brainstorms that reference them."""
        root, db = artifacts
        from entity_registry.backfill import run_backfill

        run_backfill(db, str(root))

        # Backlog entity should exist
        backlog = db.get_entity("backlog:00019")
        assert backlog is not None

        # Brainstorm that references backlog should have parent link
        brainstorm = db.get_entity("brainstorm:20260227-lineage")
        assert brainstorm is not None

    def test_all_entity_types_registered(self, artifacts):
        """After backfill, entities of all scanned types should be present."""
        root, db = artifacts
        from entity_registry.backfill import run_backfill

        run_backfill(db, str(root))

        assert db.get_entity("backlog:00019") is not None
        assert db.get_entity("brainstorm:20260227-lineage") is not None
        assert db.get_entity("feature:029-entity-lineage-tracking") is not None

    def test_scan_order_constant(self):
        """ENTITY_SCAN_ORDER should be backlog, brainstorm, project, feature."""
        from entity_registry.backfill import ENTITY_SCAN_ORDER

        assert ENTITY_SCAN_ORDER == ["backlog", "brainstorm", "project", "feature"]


# ---------------------------------------------------------------------------
# Task 3.4: Parent derivation tests
# ---------------------------------------------------------------------------


class TestParentDerivation:
    def test_feature_to_brainstorm_via_meta(self, artifacts):
        """Feature with brainstorm_source should link to brainstorm parent."""
        root, db = artifacts
        from entity_registry.backfill import run_backfill

        run_backfill(db, str(root))

        feature = db.get_entity("feature:029-entity-lineage-tracking")
        assert feature is not None
        assert feature["parent_type_id"] == "brainstorm:20260227-lineage"

    def test_feature_to_project_via_meta(self, tmp_path):
        """Feature with project_id should link to project parent (priority over brainstorm)."""
        # Create project
        proj_dir = tmp_path / "projects" / "P001"
        proj_dir.mkdir(parents=True)
        (proj_dir / ".meta.json").write_text(json.dumps({
            "id": "P001",
            "name": "Test Project",
        }))

        # Create feature with project_id
        feat_dir = tmp_path / "features" / "030-some-feature"
        feat_dir.mkdir(parents=True)
        (feat_dir / ".meta.json").write_text(json.dumps({
            "id": "030",
            "slug": "some-feature",
            "project_id": "P001",
            "brainstorm_source": "docs/brainstorms/20260227-some.prd.md",
        }))

        (tmp_path / "brainstorms").mkdir(exist_ok=True)

        db = EntityDatabase(str(tmp_path / "test.db"))
        try:
            from entity_registry.backfill import run_backfill

            run_backfill(db, str(tmp_path))

            feature = db.get_entity("feature:030-some-feature")
            assert feature is not None
            # project_id takes precedence over brainstorm_source
            assert feature["parent_type_id"] == "project:P001"
        finally:
            db.close()

    def test_brainstorm_to_backlog_format1(self, artifacts):
        """Brainstorm with '*Source: Backlog #00019*' should link to backlog."""
        root, db = artifacts
        from entity_registry.backfill import run_backfill

        run_backfill(db, str(root))

        brainstorm = db.get_entity("brainstorm:20260227-lineage")
        assert brainstorm is not None
        assert brainstorm["parent_type_id"] == "backlog:00019"

    def test_brainstorm_to_backlog_format2(self, tmp_path):
        """Brainstorm with '**Backlog Item:** 00019' should link to backlog."""
        # Create backlog
        (tmp_path / "backlog.md").write_text(
            "# Backlog\n\n"
            "| ID | Timestamp | Description |\n"
            "|----|-----------|-------------|\n"
            "| 00020 | 2026-02-28T00:00:00Z | Another item |\n"
        )

        # Create brainstorm with format 2
        bs_dir = tmp_path / "brainstorms"
        bs_dir.mkdir()
        (bs_dir / "20260228-another.prd.md").write_text(
            "# Brainstorm\n\n**Backlog Item:** 00020\n\nSome content.\n"
        )

        (tmp_path / "features").mkdir()
        (tmp_path / "projects").mkdir()

        db = EntityDatabase(str(tmp_path / "test.db"))
        try:
            from entity_registry.backfill import run_backfill

            run_backfill(db, str(tmp_path))

            brainstorm = db.get_entity("brainstorm:20260228-another")
            assert brainstorm is not None
            assert brainstorm["parent_type_id"] == "backlog:00020"
        finally:
            db.close()

    def test_derive_parent_backlog_always_none(self):
        """Backlog entities always return None for parent."""
        from entity_registry.backfill import _derive_parent

        assert _derive_parent("backlog", {}, None) is None
        assert _derive_parent("backlog", {"brainstorm_source": "x"}, "y") is None

    def test_derive_parent_feature_brainstorm_stem_extraction(self):
        """Feature brainstorm_source stem extraction removes dir prefix and extension."""
        from entity_registry.backfill import _derive_parent

        result = _derive_parent(
            "feature",
            {"brainstorm_source": "docs/brainstorms/20260227-054029-entity-lineage-tracking.prd.md"},
            None,
        )
        assert result == "brainstorm:20260227-054029-entity-lineage-tracking"

    def test_derive_parent_feature_brainstorm_md_extension(self):
        """Feature brainstorm_source with .md extension should also work."""
        from entity_registry.backfill import _derive_parent

        result = _derive_parent(
            "feature",
            {"brainstorm_source": "docs/brainstorms/20260130-slug.md"},
            None,
        )
        assert result == "brainstorm:20260130-slug"


# ---------------------------------------------------------------------------
# Task 3.6: Orphaned backlog and external brainstorm tests
# ---------------------------------------------------------------------------


class TestOrphanedAndExternal:
    def test_orphaned_backlog_gets_synthetic_entity(self, tmp_path):
        """Feature referencing non-existent backlog_source creates orphaned synthetic."""
        # No backlog.md at all -- backlog:00099 won't be found
        (tmp_path / "brainstorms").mkdir()
        (tmp_path / "projects").mkdir()
        feat_dir = tmp_path / "features" / "031-orphan-test"
        feat_dir.mkdir(parents=True)
        (feat_dir / ".meta.json").write_text(json.dumps({
            "id": "031",
            "slug": "orphan-test",
            "backlog_source": "00099",
        }))

        db = EntityDatabase(str(tmp_path / "test.db"))
        try:
            from entity_registry.backfill import run_backfill

            run_backfill(db, str(tmp_path))

            # Synthetic orphaned backlog should exist
            orphan = db.get_entity("backlog:00099")
            assert orphan is not None
            assert orphan["status"] == "orphaned"
            assert "00099" in orphan["name"]

            # Feature should be parented to the synthetic backlog
            feature = db.get_entity("feature:031-orphan-test")
            assert feature is not None
            assert feature["parent_type_id"] == "backlog:00099"
        finally:
            db.close()

    def test_external_brainstorm_gets_synthetic_entity(self, tmp_path):
        """Feature referencing external brainstorm_source creates external synthetic."""
        (tmp_path / "brainstorms").mkdir()
        (tmp_path / "projects").mkdir()
        feat_dir = tmp_path / "features" / "032-external-test"
        feat_dir.mkdir(parents=True)
        (feat_dir / ".meta.json").write_text(json.dumps({
            "id": "032",
            "slug": "external-test",
            "brainstorm_source": "~/.claude/plans/some-plan.md",
        }))

        db = EntityDatabase(str(tmp_path / "test.db"))
        try:
            from entity_registry.backfill import run_backfill

            run_backfill(db, str(tmp_path))

            # Synthetic external brainstorm should exist
            stem = "some-plan"
            external = db.get_entity(f"brainstorm:{stem}")
            assert external is not None
            assert external["status"] == "external"
            assert "External:" in external["name"]

            # Feature should be parented to the synthetic brainstorm
            feature = db.get_entity("feature:032-external-test")
            assert feature is not None
            assert feature["parent_type_id"] == f"brainstorm:{stem}"
        finally:
            db.close()

    def test_external_absolute_path_detection(self, tmp_path):
        """Absolute paths should be detected as external."""
        (tmp_path / "brainstorms").mkdir()
        (tmp_path / "projects").mkdir()
        feat_dir = tmp_path / "features" / "033-abs-test"
        feat_dir.mkdir(parents=True)
        (feat_dir / ".meta.json").write_text(json.dumps({
            "id": "033",
            "slug": "abs-test",
            "brainstorm_source": "/home/user/plans/plan.prd.md",
        }))

        db = EntityDatabase(str(tmp_path / "test.db"))
        try:
            from entity_registry.backfill import run_backfill

            run_backfill(db, str(tmp_path))

            external = db.get_entity("brainstorm:plan")
            assert external is not None
            assert external["status"] == "external"
        finally:
            db.close()


# ---------------------------------------------------------------------------
# Task 3.8: Idempotency and .prd.md/.md priority tests
# ---------------------------------------------------------------------------


class TestIdempotencyAndPriority:
    def test_backfill_idempotent(self, artifacts):
        """Running backfill twice produces same result (no duplicates, no errors)."""
        root, db = artifacts
        from entity_registry.backfill import run_backfill

        run_backfill(db, str(root))

        # Capture state after first run
        backlog1 = db.get_entity("backlog:00019")
        brainstorm1 = db.get_entity("brainstorm:20260227-lineage")
        feature1 = db.get_entity("feature:029-entity-lineage-tracking")

        # Clear backfill_complete marker to allow re-run
        db.set_metadata("backfill_complete", "0")

        # Run again
        run_backfill(db, str(root))

        # Entities should be identical (INSERT OR IGNORE preserves originals)
        backlog2 = db.get_entity("backlog:00019")
        brainstorm2 = db.get_entity("brainstorm:20260227-lineage")
        feature2 = db.get_entity("feature:029-entity-lineage-tracking")

        assert backlog1["name"] == backlog2["name"]
        assert brainstorm1["name"] == brainstorm2["name"]
        assert feature1["name"] == feature2["name"]
        assert feature1["parent_type_id"] == feature2["parent_type_id"]

    def test_prd_md_priority_over_md(self, tmp_path):
        """A .prd.md file should take priority over a .md file with the same stem."""
        (tmp_path / "brainstorms").mkdir()
        (tmp_path / "features").mkdir()
        (tmp_path / "projects").mkdir()

        # Create both .prd.md and .md with same stem
        (tmp_path / "brainstorms" / "20260227-test.prd.md").write_text(
            "# PRD version\n"
        )
        (tmp_path / "brainstorms" / "20260227-test.md").write_text(
            "# Plain version\n"
        )

        db = EntityDatabase(str(tmp_path / "test.db"))
        try:
            from entity_registry.backfill import run_backfill

            run_backfill(db, str(tmp_path))

            brainstorm = db.get_entity("brainstorm:20260227-test")
            assert brainstorm is not None
            # Artifact path should point to the .prd.md file
            assert brainstorm["artifact_path"].endswith(".prd.md")
        finally:
            db.close()

    def test_md_only_registered_for_unique_stems(self, tmp_path):
        """A .md file should be registered if no .prd.md exists for that stem."""
        (tmp_path / "brainstorms").mkdir()
        (tmp_path / "features").mkdir()
        (tmp_path / "projects").mkdir()

        # Only a .md file (no .prd.md with same stem)
        (tmp_path / "brainstorms" / "20260228-unique.md").write_text(
            "# Unique brainstorm\n"
        )

        db = EntityDatabase(str(tmp_path / "test.db"))
        try:
            from entity_registry.backfill import run_backfill

            run_backfill(db, str(tmp_path))

            brainstorm = db.get_entity("brainstorm:20260228-unique")
            assert brainstorm is not None
            assert brainstorm["artifact_path"].endswith(".md")
        finally:
            db.close()

    def test_no_double_registration_for_prd_stem(self, tmp_path):
        """When both .prd.md and .md exist, only one entity is registered."""
        (tmp_path / "brainstorms").mkdir()
        (tmp_path / "features").mkdir()
        (tmp_path / "projects").mkdir()

        (tmp_path / "brainstorms" / "20260227-dup.prd.md").write_text("# PRD\n")
        (tmp_path / "brainstorms" / "20260227-dup.md").write_text("# Plain\n")

        db = EntityDatabase(str(tmp_path / "test.db"))
        try:
            from entity_registry.backfill import run_backfill

            run_backfill(db, str(tmp_path))

            # Should have exactly one entity for this stem
            entity = db.get_entity("brainstorm:20260227-dup")
            assert entity is not None

            # Count all brainstorm entities
            cur = db._conn.execute(
                "SELECT COUNT(*) FROM entities WHERE entity_type = 'brainstorm'"
            )
            count = cur.fetchone()[0]
            assert count == 1  # only one brainstorm registered
        finally:
            db.close()


# ---------------------------------------------------------------------------
# Task 3.10: Backfill complete marker and partial recovery tests
# ---------------------------------------------------------------------------


class TestBackfillCompleteMarker:
    def test_marker_set_after_full_run(self, artifacts):
        """backfill_complete should be '1' in _metadata after successful run."""
        root, db = artifacts
        from entity_registry.backfill import run_backfill

        assert db.get_metadata("backfill_complete") is None
        run_backfill(db, str(root))
        assert db.get_metadata("backfill_complete") == "1"

    def test_marker_not_set_skips_rerun(self, artifacts):
        """When backfill_complete is '1', run_backfill should skip entirely."""
        root, db = artifacts
        from entity_registry.backfill import run_backfill

        run_backfill(db, str(root))
        assert db.get_metadata("backfill_complete") == "1"

        # Add a new feature artifact AFTER backfill completed
        new_feat = root / "features" / "099-new-feature"
        new_feat.mkdir(parents=True)
        (new_feat / ".meta.json").write_text(json.dumps({
            "id": "099",
            "slug": "new-feature",
        }))

        # Re-run should skip (marker already set)
        run_backfill(db, str(root))

        # New feature should NOT be registered (run was skipped)
        assert db.get_entity("feature:099-new-feature") is None

    def test_marker_not_set_allows_rerun(self, artifacts):
        """When backfill_complete is not '1', run_backfill should execute."""
        root, db = artifacts
        from entity_registry.backfill import run_backfill

        run_backfill(db, str(root))
        assert db.get_metadata("backfill_complete") == "1"

        # Reset marker
        db.set_metadata("backfill_complete", "0")

        # Add a new feature
        new_feat = root / "features" / "099-new-feature"
        new_feat.mkdir(parents=True)
        (new_feat / ".meta.json").write_text(json.dumps({
            "id": "099",
            "slug": "new-feature",
        }))

        # Re-run should execute (marker cleared)
        run_backfill(db, str(root))

        # New feature should be registered
        assert db.get_entity("feature:099-new-feature") is not None
        assert db.get_metadata("backfill_complete") == "1"

    def test_partial_failure_recovery(self, tmp_path):
        """If backfill fails mid-way, re-run should recover via INSERT OR IGNORE."""
        (tmp_path / "brainstorms").mkdir()
        (tmp_path / "projects").mkdir()
        (tmp_path / "features").mkdir()

        # Create a backlog with one item
        (tmp_path / "backlog.md").write_text(
            "# Backlog\n\n"
            "| ID | Timestamp | Description |\n"
            "|----|-----------|-------------|\n"
            "| 00050 | 2026-03-01T00:00:00Z | Partial test |\n"
        )

        db = EntityDatabase(str(tmp_path / "test.db"))
        try:
            from entity_registry.backfill import run_backfill

            # Simulate partial: manually register one entity, no marker
            db.register_entity("backlog", "00050", "Partial test")

            # Full run should succeed (INSERT OR IGNORE on existing entity)
            run_backfill(db, str(tmp_path))

            # Entity should still exist with original name
            backlog = db.get_entity("backlog:00050")
            assert backlog is not None
            assert backlog["name"] == "Partial test"

            # Marker should be set
            assert db.get_metadata("backfill_complete") == "1"
        finally:
            db.close()
