"""Tests for entity_registry.frontmatter_sync module."""
from __future__ import annotations

import pytest


# ---------------------------------------------------------------------------
# Phase 1: Dataclass and constant tests (task 1.2a)
# ---------------------------------------------------------------------------


class TestDataclasses:
    """Verify dataclass construction and field accessibility."""

    def test_field_mismatch_construction(self):
        """FieldMismatch stores field, file_value, db_value (spec R4)."""
        from entity_registry.frontmatter_sync import FieldMismatch

        m = FieldMismatch(field="entity_uuid", file_value="abc", db_value="xyz")
        assert m.field == "entity_uuid"
        assert m.file_value == "abc"
        assert m.db_value == "xyz"

    def test_drift_report_construction(self):
        """DriftReport stores all 6 fields."""
        from entity_registry.frontmatter_sync import DriftReport, FieldMismatch

        report = DriftReport(
            filepath="/tmp/test.md",
            type_id="feature:001-test",
            status="in_sync",
            file_fields={"entity_uuid": "abc"},
            db_fields={"uuid": "abc"},
            mismatches=[],
        )
        assert report.filepath == "/tmp/test.md"
        assert report.type_id == "feature:001-test"
        assert report.status == "in_sync"
        assert report.file_fields == {"entity_uuid": "abc"}
        assert report.db_fields == {"uuid": "abc"}
        assert report.mismatches == []

    def test_stamp_result_construction(self):
        """StampResult stores filepath, action, message."""
        from entity_registry.frontmatter_sync import StampResult

        result = StampResult(filepath="/tmp/test.md", action="created", message="OK")
        assert result.filepath == "/tmp/test.md"
        assert result.action == "created"
        assert result.message == "OK"

    def test_ingest_result_construction(self):
        """IngestResult stores filepath, action, message."""
        from entity_registry.frontmatter_sync import IngestResult

        result = IngestResult(filepath="/tmp/test.md", action="updated", message="OK")
        assert result.filepath == "/tmp/test.md"
        assert result.action == "updated"
        assert result.message == "OK"


class TestConstants:
    """Verify module-level constants."""

    def test_comparable_field_map_content(self):
        """COMPARABLE_FIELD_MAP has exactly 2 entries (spec R6)."""
        from entity_registry.frontmatter_sync import COMPARABLE_FIELD_MAP

        assert len(COMPARABLE_FIELD_MAP) == 2
        assert COMPARABLE_FIELD_MAP["entity_uuid"] == "uuid"
        assert COMPARABLE_FIELD_MAP["entity_type_id"] == "type_id"

    def test_module_imports_resolve(self):
        """Module re-exports ARTIFACT_BASENAME_MAP and ARTIFACT_PHASE_MAP."""
        from entity_registry import frontmatter_sync

        assert hasattr(frontmatter_sync, "COMPARABLE_FIELD_MAP")
        assert hasattr(frontmatter_sync, "ARTIFACT_BASENAME_MAP")
        assert hasattr(frontmatter_sync, "ARTIFACT_PHASE_MAP")


# ---------------------------------------------------------------------------
# Phase 2: Internal helper tests (tasks 2.1a, 2.2a)
# ---------------------------------------------------------------------------


class TestDeriveOptionalFields:
    """Tests for _derive_optional_fields() helper (task 2.1a)."""

    def test_derive_feature_entity(self):
        """Feature type_id with artifact_type='spec' yields feature_id, feature_slug, phase."""
        from entity_registry.frontmatter_sync import _derive_optional_fields

        entity = {
            "type_id": "feature:003-bidirectional-uuid-sync-betwee",
            "metadata": None,
            "parent_type_id": None,
        }
        result = _derive_optional_fields(entity, "spec")
        assert result["feature_id"] == "003"
        assert result["feature_slug"] == "bidirectional-uuid-sync-betwee"
        assert result["phase"] == "specify"

    def test_derive_project_id_from_metadata(self):
        """Entity with metadata JSON containing project_id extracts it."""
        from entity_registry.frontmatter_sync import _derive_optional_fields

        entity = {
            "type_id": "feature:001-test",
            "metadata": '{"project_id": "P001"}',
            "parent_type_id": None,
        }
        result = _derive_optional_fields(entity, "spec")
        assert result["project_id"] == "P001"

    def test_derive_project_id_from_parent(self):
        """Entity with parent_type_id='project:P001' extracts project_id."""
        from entity_registry.frontmatter_sync import _derive_optional_fields

        entity = {
            "type_id": "feature:001-test",
            "metadata": None,
            "parent_type_id": "project:P001",
        }
        result = _derive_optional_fields(entity, "spec")
        assert result["project_id"] == "P001"

    def test_derive_metadata_priority(self):
        """When both metadata JSON and parent_type_id have project_id, metadata wins."""
        from entity_registry.frontmatter_sync import _derive_optional_fields

        entity = {
            "type_id": "feature:001-test",
            "metadata": '{"project_id": "META-ID"}',
            "parent_type_id": "project:PARENT-ID",
        }
        result = _derive_optional_fields(entity, "spec")
        assert result["project_id"] == "META-ID"

    def test_derive_non_feature_entity(self):
        """Non-feature entity (project) has no feature_id or feature_slug."""
        from entity_registry.frontmatter_sync import _derive_optional_fields

        entity = {
            "type_id": "project:P001",
            "metadata": None,
            "parent_type_id": None,
        }
        result = _derive_optional_fields(entity, "spec")
        assert "feature_id" not in result
        assert "feature_slug" not in result

    def test_derive_malformed_metadata(self):
        """Invalid JSON metadata falls back to parent_type_id for project_id."""
        from entity_registry.frontmatter_sync import _derive_optional_fields

        entity = {
            "type_id": "feature:001-test",
            "metadata": "not-valid-json{{{",
            "parent_type_id": "project:FALLBACK",
        }
        result = _derive_optional_fields(entity, "spec")
        assert result["project_id"] == "FALLBACK"

    def test_derive_no_project_id(self):
        """Neither metadata nor parent provides project_id — key absent from result."""
        from entity_registry.frontmatter_sync import _derive_optional_fields

        entity = {
            "type_id": "feature:001-test",
            "metadata": None,
            "parent_type_id": None,
        }
        result = _derive_optional_fields(entity, "spec")
        assert "project_id" not in result


class TestDeriveFeatureDirectory:
    """Tests for _derive_feature_directory() helper (task 2.2a)."""

    def test_derive_dir_from_artifact_path_dir(self, tmp_path):
        """artifact_path that is a directory returns it directly."""
        from entity_registry.frontmatter_sync import _derive_feature_directory

        feature_dir = tmp_path / "features" / "003-my-feature"
        feature_dir.mkdir(parents=True)
        entity = {"artifact_path": str(feature_dir), "entity_id": "003-my-feature"}
        result = _derive_feature_directory(entity, str(tmp_path))
        assert result == str(feature_dir)

    def test_derive_dir_from_artifact_path_file(self, tmp_path):
        """artifact_path that is a file returns its dirname."""
        from entity_registry.frontmatter_sync import _derive_feature_directory

        feature_dir = tmp_path / "features" / "003-my-feature"
        feature_dir.mkdir(parents=True)
        spec_file = feature_dir / "spec.md"
        spec_file.write_text("# Spec")
        entity = {"artifact_path": str(spec_file), "entity_id": "003-my-feature"}
        result = _derive_feature_directory(entity, str(tmp_path))
        assert result == str(feature_dir)

    def test_derive_dir_from_entity_id(self, tmp_path):
        """No artifact_path, constructs from entity_id when directory exists."""
        from entity_registry.frontmatter_sync import _derive_feature_directory

        feature_dir = tmp_path / "features" / "003-my-feature"
        feature_dir.mkdir(parents=True)
        entity = {"artifact_path": None, "entity_id": "003-my-feature"}
        result = _derive_feature_directory(entity, str(tmp_path))
        assert result == str(feature_dir)

    def test_derive_dir_none(self, tmp_path):
        """No artifact_path and constructed path doesn't exist returns None."""
        from entity_registry.frontmatter_sync import _derive_feature_directory

        entity = {"artifact_path": None, "entity_id": "999-nonexistent"}
        result = _derive_feature_directory(entity, str(tmp_path))
        assert result is None
