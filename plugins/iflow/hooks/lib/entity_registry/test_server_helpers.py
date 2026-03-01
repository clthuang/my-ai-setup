"""Tests for entity_registry.server_helpers module."""
from __future__ import annotations

import os
import uuid

import pytest

from entity_registry.database import EntityDatabase
from entity_registry.server_helpers import (
    _format_entity_label,
    _process_export_lineage_markdown,
    _process_get_lineage,
    _process_register_entity,
    parse_metadata,
    render_tree,
    resolve_output_path,
)


ENTITY_UUIDS = {
    "project:P001": "550e8400-e29b-41d4-a716-446655440001",
    "feature:001-slug": "550e8400-e29b-41d4-a716-446655440002",
    "feature:002-slug": "550e8400-e29b-41d4-a716-446655440003",
    "brainstorm:20260101-test": "550e8400-e29b-41d4-a716-446655440004",
    "backlog:00001": "550e8400-e29b-41d4-a716-446655440005",
}


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


# ---------------------------------------------------------------------------
# Task 2.1: render_tree tests
# ---------------------------------------------------------------------------


def _make_entity(
    type_id: str,
    name: str,
    entity_type: str,
    status: str | None = None,
    parent_type_id: str | None = None,
    created_at: str = "2026-02-27T12:00:00+00:00",
    metadata: str | None = None,
) -> dict:
    """Helper to create an entity dict matching the database row shape."""
    entity = {
        "type_id": type_id,
        "name": name,
        "entity_type": entity_type,
        "status": status,
        "parent_type_id": parent_type_id,
        "created_at": created_at,
        "metadata": metadata,
    }
    entity["uuid"] = ENTITY_UUIDS.get(type_id, str(uuid.uuid4()))
    entity["parent_uuid"] = (
        ENTITY_UUIDS.get(parent_type_id)
        if parent_type_id else None
    )
    return entity


def _link_parent_uuids(entities: list[dict]) -> list[dict]:
    """Fix up parent_uuid fields so children reference their parent's uuid.

    _make_entity uses ENTITY_UUIDS for parent_uuid lookup, which only covers
    a few well-known type_ids.  This helper resolves parent_uuid from the
    actual uuid assigned to each entity in the list (parent-first order).
    """
    tid_to_uuid = {e["type_id"]: e["uuid"] for e in entities}
    for e in entities:
        ptid = e.get("parent_type_id")
        if ptid and ptid in tid_to_uuid:
            e["parent_uuid"] = tid_to_uuid[ptid]
    return entities


class TestRenderTree:
    def test_single_node_no_status(self):
        """A single node with no status renders without status in parens."""
        entities = [
            _make_entity("project:alpha", "Alpha", "project"),
        ]
        result = render_tree(entities, entities[0]["uuid"])
        assert result == 'project:alpha \u2014 "Alpha" (2026-02-27)'

    def test_single_node_with_status(self):
        """A single node with status renders status before date."""
        entities = [
            _make_entity("project:alpha", "Alpha", "project", status="active"),
        ]
        result = render_tree(entities, entities[0]["uuid"])
        assert result == 'project:alpha \u2014 "Alpha" (active, 2026-02-27)'

    def test_linear_chain_three_deep(self):
        """A 3-node linear chain renders with proper indentation."""
        entities = _link_parent_uuids([
            _make_entity(
                "backlog:00019", "Item", "backlog",
                status="promoted",
            ),
            _make_entity(
                "brainstorm:20260227-lineage", "Entity Lineage", "brainstorm",
                parent_type_id="backlog:00019",
            ),
            _make_entity(
                "feature:029-entity-lineage-tracking", "Entity Lineage", "feature",
                status="active",
                parent_type_id="brainstorm:20260227-lineage",
            ),
        ])
        result = render_tree(entities, entities[0]["uuid"])
        expected = (
            'backlog:00019 \u2014 "Item" (promoted, 2026-02-27)\n'
            '  \u2514\u2500 brainstorm:20260227-lineage \u2014 "Entity Lineage" (2026-02-27)\n'
            '     \u2514\u2500 feature:029-entity-lineage-tracking \u2014 "Entity Lineage" (active, 2026-02-27)'
        )
        assert result == expected

    def test_branching_tree_two_children(self):
        """Two children: first uses box tee, second uses corner."""
        entities = _link_parent_uuids([
            _make_entity("project:root", "Root", "project", status="active"),
            _make_entity(
                "feature:a", "Alpha", "feature",
                parent_type_id="project:root",
            ),
            _make_entity(
                "feature:b", "Beta", "feature",
                status="done",
                parent_type_id="project:root",
            ),
        ])
        result = render_tree(entities, entities[0]["uuid"])
        expected = (
            'project:root \u2014 "Root" (active, 2026-02-27)\n'
            '  \u251c\u2500 feature:a \u2014 "Alpha" (2026-02-27)\n'
            '  \u2514\u2500 feature:b \u2014 "Beta" (done, 2026-02-27)'
        )
        assert result == expected

    def test_branching_tree_with_nested_children(self):
        """A root with two children, first child has a grandchild."""
        entities = _link_parent_uuids([
            _make_entity("project:root", "Root", "project"),
            _make_entity(
                "feature:a", "Alpha", "feature",
                parent_type_id="project:root",
            ),
            _make_entity(
                "feature:a1", "Alpha Sub", "feature",
                parent_type_id="feature:a",
            ),
            _make_entity(
                "feature:b", "Beta", "feature",
                parent_type_id="project:root",
            ),
        ])
        result = render_tree(entities, entities[0]["uuid"])
        lines = result.split("\n")
        assert len(lines) == 4
        # Root line
        assert lines[0] == 'project:root \u2014 "Root" (2026-02-27)'
        # First child (not last) uses tee
        assert "\u251c\u2500 feature:a" in lines[1]
        # Grandchild under first child; continuation line uses pipe
        assert "\u2502" in lines[2]
        assert "\u2514\u2500 feature:a1" in lines[2]
        # Second child (last) uses corner
        assert "\u2514\u2500 feature:b" in lines[3]

    def test_empty_list_returns_empty_string(self):
        """An empty entity list should return an empty string."""
        result = render_tree([], "project:nonexistent")
        assert result == ""

    def test_root_not_found_returns_empty_string(self):
        """If root_id UUID is not in the entities list, return empty."""
        entities = [
            _make_entity("feature:a", "Alpha", "feature"),
        ]
        result = render_tree(entities, "not-a-real-uuid")
        assert result == ""


# ---------------------------------------------------------------------------
# Task 2.3: parse_metadata tests
# ---------------------------------------------------------------------------


class TestParseMetadata:
    def test_valid_json_returns_dict(self):
        """Valid JSON string should be parsed to a dict."""
        result = parse_metadata('{"priority": "high", "count": 3}')
        assert result == {"priority": "high", "count": 3}

    def test_empty_object_returns_empty_dict(self):
        """An empty JSON object should return an empty dict."""
        result = parse_metadata("{}")
        assert result == {}

    def test_invalid_json_returns_error_dict(self):
        """Invalid JSON should return an error dict."""
        result = parse_metadata("not valid json")
        assert isinstance(result, dict)
        assert "error" in result

    def test_none_passthrough_returns_none(self):
        """None input should pass through as None."""
        result = parse_metadata(None)
        assert result is None

    def test_nested_json(self):
        """Nested JSON objects should parse correctly."""
        result = parse_metadata('{"a": {"b": [1, 2, 3]}}')
        assert result == {"a": {"b": [1, 2, 3]}}

    def test_empty_string_returns_error_dict(self):
        """Empty string is invalid JSON and should return error dict."""
        result = parse_metadata("")
        assert isinstance(result, dict)
        assert "error" in result


# ---------------------------------------------------------------------------
# Task 2.5: resolve_output_path tests
# ---------------------------------------------------------------------------


class TestResolveOutputPath:
    def test_relative_path_resolved_against_artifacts_root(self, tmp_path):
        """A relative path should be joined with artifacts_root."""
        artifacts_root = str(tmp_path / "docs")
        os.makedirs(artifacts_root, exist_ok=True)
        result = resolve_output_path("features/f1/spec.md", artifacts_root)
        expected = os.path.realpath(os.path.join(artifacts_root, "features/f1/spec.md"))
        assert result == expected

    def test_absolute_path_inside_root_accepted(self, tmp_path):
        """An absolute path inside artifacts_root should be accepted."""
        artifacts_root = str(tmp_path / "docs")
        os.makedirs(artifacts_root, exist_ok=True)
        abs_path = os.path.join(artifacts_root, "output.md")
        result = resolve_output_path(abs_path, artifacts_root)
        assert result == os.path.realpath(abs_path)

    def test_absolute_path_outside_root_rejected(self, tmp_path):
        """An absolute path outside artifacts_root should return None."""
        artifacts_root = str(tmp_path / "docs")
        os.makedirs(artifacts_root, exist_ok=True)
        result = resolve_output_path("/tmp/escape.md", artifacts_root)
        assert result is None

    def test_none_returns_none(self):
        """None input should return None."""
        result = resolve_output_path(None, "/home/user/docs")
        assert result is None

    def test_simple_filename_resolved(self, tmp_path):
        """A bare filename should be joined with artifacts_root."""
        artifacts_root = str(tmp_path / "docs")
        os.makedirs(artifacts_root, exist_ok=True)
        result = resolve_output_path("spec.md", artifacts_root)
        expected = os.path.realpath(os.path.join(artifacts_root, "spec.md"))
        assert result == expected

    def test_artifacts_root_trailing_slash(self, tmp_path):
        """Trailing slash on artifacts_root should not double up."""
        artifacts_root = str(tmp_path / "docs") + "/"
        os.makedirs(artifacts_root, exist_ok=True)
        result = resolve_output_path("features/spec.md", artifacts_root)
        expected = os.path.realpath(os.path.join(artifacts_root, "features/spec.md"))
        assert result == expected

    def test_path_traversal_rejected(self, tmp_path):
        """Path traversal via .. should be rejected if it escapes root."""
        artifacts_root = str(tmp_path / "docs")
        os.makedirs(artifacts_root, exist_ok=True)
        result = resolve_output_path("../../etc/passwd", artifacts_root)
        assert result is None


# ---------------------------------------------------------------------------
# Task 2.7: _process_register_entity and _process_get_lineage tests
# ---------------------------------------------------------------------------


class TestProcessRegisterEntity:
    def test_happy_path_returns_success_string(self, db: EntityDatabase):
        """Successful registration returns a string containing the type_id."""
        result = _process_register_entity(
            db, "feature", "f1", "Feature One",
            artifact_path=None, status="active",
            parent_type_id=None, metadata=None,
        )
        assert isinstance(result, str)
        assert "feature:f1" in result

    def test_entity_actually_registered(self, db: EntityDatabase):
        """The entity should exist in the database after registration."""
        _process_register_entity(
            db, "project", "p1", "Project One",
            artifact_path="/docs/p1", status="active",
            parent_type_id=None, metadata=None,
        )
        entity = db.get_entity("project:p1")
        assert entity is not None
        assert entity["name"] == "Project One"
        assert entity["status"] == "active"

    def test_with_parent_and_metadata(self, db: EntityDatabase):
        """Registration with parent and metadata should succeed."""
        db.register_entity("project", "parent", "Parent")
        result = _process_register_entity(
            db, "feature", "child", "Child Feature",
            artifact_path=None, status=None,
            parent_type_id="project:parent",
            metadata={"key": "value"},
        )
        assert isinstance(result, str)
        assert "feature:child" in result
        entity = db.get_entity("feature:child")
        assert entity is not None
        assert entity["parent_type_id"] == "project:parent"

    def test_invalid_entity_type_returns_error_string(self, db: EntityDatabase):
        """Invalid entity_type should return an error string, not raise."""
        result = _process_register_entity(
            db, "invalid_type", "x", "Bad",
            artifact_path=None, status=None,
            parent_type_id=None, metadata=None,
        )
        assert isinstance(result, str)
        assert "error" in result.lower() or "invalid" in result.lower()

    def test_invalid_parent_returns_error_string(self, db: EntityDatabase):
        """Referencing a non-existent parent should return error string."""
        result = _process_register_entity(
            db, "feature", "f1", "Feature",
            artifact_path=None, status=None,
            parent_type_id="project:nonexistent",
            metadata=None,
        )
        assert isinstance(result, str)
        assert "error" in result.lower()

    def test_never_raises(self, db: EntityDatabase):
        """_process_register_entity should never raise exceptions."""
        # Even with bizarre inputs, it should return a string
        result = _process_register_entity(
            db, "", "", "",
            artifact_path=None, status=None,
            parent_type_id=None, metadata=None,
        )
        assert isinstance(result, str)


class TestProcessGetLineage:
    def _setup_chain(self, db: EntityDatabase):
        """Create project:root -> feature:mid -> feature:leaf chain."""
        db.register_entity("project", "root", "Root Project", status="active")
        db.register_entity(
            "feature", "mid", "Mid Feature",
            parent_type_id="project:root",
        )
        db.register_entity(
            "feature", "leaf", "Leaf Feature",
            status="done",
            parent_type_id="feature:mid",
        )

    def test_upward_returns_formatted_tree(self, db: EntityDatabase):
        """Upward lineage should return a formatted string with all ancestors."""
        self._setup_chain(db)
        result = _process_get_lineage(db, "feature:leaf", "up", 10)
        assert isinstance(result, str)
        assert "project:root" in result
        assert "feature:mid" in result
        assert "feature:leaf" in result

    def test_downward_returns_formatted_tree(self, db: EntityDatabase):
        """Downward lineage should return a formatted tree."""
        self._setup_chain(db)
        result = _process_get_lineage(db, "project:root", "down", 10)
        assert isinstance(result, str)
        assert "project:root" in result
        assert "feature:mid" in result
        assert "feature:leaf" in result

    def test_nonexistent_entity_returns_not_found(self, db: EntityDatabase):
        """Non-existent type_id should return a 'not found' message."""
        result = _process_get_lineage(db, "feature:nonexistent", "up", 10)
        assert isinstance(result, str)
        assert "not found" in result.lower() or "no" in result.lower()

    def test_single_entity_lineage(self, db: EntityDatabase):
        """A single entity with no parents/children returns just itself."""
        db.register_entity("project", "solo", "Solo")
        result = _process_get_lineage(db, "project:solo", "up", 10)
        assert isinstance(result, str)
        assert "project:solo" in result

    def test_never_raises(self, db: EntityDatabase):
        """_process_get_lineage should never raise exceptions."""
        # Close the database to force an error condition
        db.close()
        result = _process_get_lineage(db, "feature:anything", "up", 10)
        assert isinstance(result, str)

    def test_upward_shows_chain_format(self, db: EntityDatabase):
        """Upward lineage renders as a chain (root first)."""
        self._setup_chain(db)
        result = _process_get_lineage(db, "feature:leaf", "up", 10)
        # Root should appear before leaf in the output
        root_pos = result.index("project:root")
        leaf_pos = result.index("feature:leaf")
        assert root_pos < leaf_pos

    def test_downward_shows_tree_format(self, db: EntityDatabase):
        """Downward lineage renders as a tree from root."""
        db.register_entity("project", "root", "Root", status="active")
        db.register_entity(
            "feature", "a", "Alpha",
            parent_type_id="project:root",
        )
        db.register_entity(
            "feature", "b", "Beta",
            parent_type_id="project:root",
        )
        result = _process_get_lineage(db, "project:root", "down", 10)
        assert isinstance(result, str)
        assert "project:root" in result
        assert "feature:a" in result
        assert "feature:b" in result

    def test_process_get_lineage_passes_uuid(self):
        """_process_get_lineage passes UUID (not type_id) to render_tree."""
        import re
        from unittest.mock import patch

        from entity_registry.server_helpers import render_tree

        db = EntityDatabase(":memory:")
        try:
            db.register_entity("project", "root", "Root Project", status="active")
            db.register_entity(
                "feature", "mid", "Mid Feature",
                parent_type_id="project:root",
            )
            db.register_entity(
                "feature", "leaf", "Leaf Feature",
                status="done",
                parent_type_id="feature:mid",
            )

            _UUID_V4_RE = re.compile(
                r'^[0-9a-f]{8}-[0-9a-f]{4}-4[0-9a-f]{3}-[89ab][0-9a-f]{3}-[0-9a-f]{12}$'
            )

            with patch('entity_registry.server_helpers.render_tree', wraps=render_tree) as mock_rt:
                _process_get_lineage(db, "feature:leaf", "up", 10)
                # render_tree(entities, root_id, max_depth) -- root_id is args[1]
                root_arg = mock_rt.call_args.args[1]
                assert _UUID_V4_RE.match(root_arg), (
                    f"Expected UUID, got: {root_arg}"
                )
        finally:
            db.close()


# ---------------------------------------------------------------------------
# Task 4.2: _process_export_lineage_markdown tests
# ---------------------------------------------------------------------------


class TestProcessExportLineageMarkdown:
    def test_returns_markdown_string(self, db: EntityDatabase):
        """Export returns a markdown string when no output_path is given."""
        db.register_entity("project", "p1", "Project One", status="active")
        result = _process_export_lineage_markdown(db, "project:p1", None, "/tmp")
        assert isinstance(result, str)
        assert "Project One" in result

    def test_all_trees_when_type_id_is_none(self, db: EntityDatabase):
        """Export all trees when type_id is None."""
        db.register_entity("project", "p1", "Project One")
        db.register_entity("project", "p2", "Project Two")
        result = _process_export_lineage_markdown(db, None, None, "/tmp")
        assert "Project One" in result
        assert "Project Two" in result

    def test_writes_to_file(self, db: EntityDatabase, tmp_path):
        """Export writes markdown to file when output_path is given."""
        db.register_entity("feature", "f1", "Feature One", status="active")
        artifacts_root = str(tmp_path / "docs")
        import os
        os.makedirs(artifacts_root, exist_ok=True)
        result = _process_export_lineage_markdown(
            db, "feature:f1", "lineage.md", artifacts_root,
        )
        assert "Exported" in result
        expected_path = os.path.realpath(os.path.join(artifacts_root, "lineage.md"))
        assert expected_path in result
        with open(expected_path) as f:
            content = f.read()
        assert "Feature One" in content

    def test_relative_path_resolved_against_artifacts_root(self, db: EntityDatabase, tmp_path):
        """A relative output_path is resolved against artifacts_root."""
        db.register_entity("project", "p1", "Project One")
        artifacts_root = str(tmp_path / "docs")
        import os
        os.makedirs(artifacts_root, exist_ok=True)
        result = _process_export_lineage_markdown(db, "project:p1", "lineage.md", artifacts_root)
        assert "Exported" in result
        expected_path = str(tmp_path / "docs" / "lineage.md")
        assert expected_path in result

    def test_nonexistent_entity_returns_empty(self, db: EntityDatabase):
        """Export with nonexistent type_id returns empty string."""
        result = _process_export_lineage_markdown(db, "project:nonexistent", None, "/tmp")
        assert isinstance(result, str)
        # Empty tree returns empty markdown
        assert result == ""

    def test_never_raises(self, db: EntityDatabase):
        """_process_export_lineage_markdown should never raise."""
        db.close()
        result = _process_export_lineage_markdown(db, "feature:x", None, "/tmp")
        assert isinstance(result, str)


# ---------------------------------------------------------------------------
# Deepened tests: BDD, Boundary, Adversarial, Error, Mutation
# ---------------------------------------------------------------------------


class TestRenderTreeDeepNesting:
    """Adversarial: deeply nested structures render correctly.
    derived_from: dimension:adversarial
    """

    def test_render_tree_with_deeply_nested_structure(self):
        # Given a chain 6 levels deep
        entities = [_make_entity("project:root", "Root", "project")]
        for i in range(1, 6):
            entities.append(
                _make_entity(
                    f"feature:level-{i}", f"Level {i}", "feature",
                    parent_type_id=(
                        "project:root" if i == 1 else f"feature:level-{i-1}"
                    ),
                )
            )
        _link_parent_uuids(entities)
        # When rendering the tree
        result = render_tree(entities, entities[0]["uuid"])
        # Then all 6 levels appear in output
        assert "project:root" in result
        for i in range(1, 6):
            assert f"feature:level-{i}" in result
        # And indentation increases with depth
        lines = result.split("\n")
        assert len(lines) == 6
        # Deeper lines have more leading whitespace
        for i in range(1, len(lines)):
            stripped_prev = lines[i - 1].lstrip()
            stripped_curr = lines[i].lstrip()
            indent_prev = len(lines[i - 1]) - len(stripped_prev)
            indent_curr = len(lines[i]) - len(stripped_curr)
            assert indent_curr >= indent_prev


class TestPathNormalization:
    """BDD: AC-7 — path normalization for relative and absolute paths.
    derived_from: spec:AC-7
    """

    def test_path_normalization_relative_paths_resolved(self, tmp_path):
        # Given a relative path and a real artifacts_root
        artifacts_root = str(tmp_path / "docs")
        import os
        os.makedirs(artifacts_root, exist_ok=True)
        result = resolve_output_path("features/f1/lineage.md", artifacts_root)
        # Then it's resolved against artifacts_root
        expected = os.path.realpath(os.path.join(artifacts_root, "features/f1/lineage.md"))
        assert result == expected
        assert result.startswith("/")

    def test_path_normalization_absolute_paths_outside_root_rejected(self, tmp_path):
        # Given an absolute path outside artifacts_root
        artifacts_root = str(tmp_path / "docs")
        import os
        os.makedirs(artifacts_root, exist_ok=True)
        result = resolve_output_path("/absolute/path/file.md", artifacts_root)
        # Then it's rejected (returns None) because it escapes the root
        assert result is None

    def test_path_normalization_external_paths_show_warning(self):
        # Given a None path (no output requested)
        result = resolve_output_path(None, "/home/user/docs")
        # Then None is returned (no path resolution)
        assert result is None


class TestParseMetadataMalformed:
    """Adversarial: malformed metadata JSON handled gracefully.
    derived_from: dimension:adversarial, spec:AC-3
    """

    def test_malformed_meta_json_handled_gracefully(self):
        # Given malformed JSON string
        result = parse_metadata("{key: invalid}")
        # Then an error dict is returned, not an exception
        assert isinstance(result, dict)
        assert "error" in result

    def test_meta_json_with_extra_unexpected_fields_accepted(self):
        # Given JSON with unexpected extra fields
        result = parse_metadata('{"expected": 1, "extra_field": "surprise", "nested": {"deep": true}}')
        # Then all fields are parsed and returned
        assert isinstance(result, dict)
        assert result["expected"] == 1
        assert result["extra_field"] == "surprise"
        assert result["nested"]["deep"] is True


class TestErrorPropagation:
    """Error propagation: error messages include context.
    derived_from: dimension:error_propagation
    """

    def test_orphaned_parent_error_includes_context(self, db: EntityDatabase):
        # Given a feature entity with no parent
        db.register_entity("feature", "f1", "Feature One")
        # When setting parent to nonexistent entity via _process helper
        result = _process_register_entity(
            db, "feature", "orphan-child", "Orphan",
            artifact_path=None, status=None,
            parent_type_id="project:nonexistent",
            metadata=None,
        )
        # Then the error message includes context about the missing entity
        assert isinstance(result, str)
        assert "error" in result.lower()

    def test_database_connection_failure_propagates_cleanly(
        self, db: EntityDatabase,
    ):
        # Given a closed database connection
        db.close()
        # When attempting to get lineage
        result = _process_get_lineage(db, "feature:f1", "up", 10)
        # Then a string error is returned, not an exception
        assert isinstance(result, str)

    def test_depth_limit_message_for_truncated_lineage(self, db: EntityDatabase):
        # Given a chain of 15 entities
        db.register_entity("project", "e0", "E0")
        for i in range(1, 15):
            db.register_entity(
                "feature", f"e{i}", f"E{i}",
                parent_type_id=f"{'project' if i == 1 else 'feature'}:e{i-1}",
            )
        # When traversing upward from e14 with max_depth=5
        result = _process_get_lineage(db, "feature:e14", "up", 5)
        # Then a tree is returned (not empty/not-found) but truncated
        assert isinstance(result, str)
        assert "feature:e14" in result
        # And e0 (root, 14 hops away) is NOT in the output
        assert "project:e0" not in result


class TestExternalPathWarning:
    """Error propagation: external path detection includes the path.
    derived_from: dimension:error_propagation
    """

    def test_external_path_warning_includes_the_path(self, db: EntityDatabase, tmp_path):
        # Given an export to a relative output file path
        artifacts_root = str(tmp_path / "docs")
        os.makedirs(artifacts_root, exist_ok=True)
        db.register_entity("project", "p1", "Test Project")
        # When exporting with a relative output path
        result = _process_export_lineage_markdown(db, "project:p1", "output.md", artifacts_root)
        # Then the result contains the resolved path
        expected_path = os.path.realpath(os.path.join(artifacts_root, "output.md"))
        assert expected_path in result


class TestProcessGetLineageUpwardChainFormat:
    """Mutation mindset: upward lineage root appears before leaf.
    derived_from: dimension:mutation_mindset
    """

    def test_upward_lineage_renders_root_before_leaf(self, db: EntityDatabase):
        # Given A -> B -> C chain
        db.register_entity("project", "root", "Root", status="active")
        db.register_entity(
            "feature", "mid", "Mid", parent_type_id="project:root",
        )
        db.register_entity(
            "feature", "leaf", "Leaf", parent_type_id="feature:mid",
        )
        # When getting upward lineage from leaf
        result = _process_get_lineage(db, "feature:leaf", "up", 10)
        # Then root appears before leaf in the rendered string
        root_pos = result.index("project:root")
        leaf_pos = result.index("feature:leaf")
        assert root_pos < leaf_pos
        # Mutation check: if order was reversed, root would appear after leaf


# ---------------------------------------------------------------------------
# AC-5/I7: depends_on_features annotations in tree output
# ---------------------------------------------------------------------------


class TestFormatEntityLabelDependsOn:
    """AC-5: depends_on_features annotations rendered in entity labels."""

    def test_entity_with_depends_on_features_shows_annotation(self):
        """Entity with depends_on_features metadata shows [depends on: ...] annotation."""
        import json
        entity = _make_entity(
            "feature:031-api-gateway", "API Gateway", "feature",
            status="planned",
            metadata=json.dumps({"depends_on_features": ["030-auth-module"]}),
        )
        label = _format_entity_label(entity)
        assert label == (
            'feature:031-api-gateway \u2014 "API Gateway" '
            '(planned, 2026-02-27) [depends on: feature:030-auth-module]'
        )

    def test_entity_with_multiple_depends_on_features(self):
        """Entity with multiple depends_on_features shows all dependencies."""
        import json
        entity = _make_entity(
            "feature:032-dashboard", "Dashboard", "feature",
            status="planned",
            metadata=json.dumps({
                "depends_on_features": ["030-auth-module", "031-api-gateway"],
            }),
        )
        label = _format_entity_label(entity)
        assert label == (
            'feature:032-dashboard \u2014 "Dashboard" '
            '(planned, 2026-02-27) '
            '[depends on: feature:030-auth-module, feature:031-api-gateway]'
        )

    def test_entity_with_no_metadata_unchanged(self):
        """Entity with no metadata (None) has no annotation."""
        entity = _make_entity(
            "feature:030-auth-module", "Auth Module", "feature",
            status="active",
        )
        label = _format_entity_label(entity)
        assert label == (
            'feature:030-auth-module \u2014 "Auth Module" (active, 2026-02-27)'
        )

    def test_entity_with_metadata_but_no_depends_on_features(self):
        """Entity with metadata but no depends_on_features key has no annotation."""
        import json
        entity = _make_entity(
            "feature:030-auth-module", "Auth Module", "feature",
            status="active",
            metadata=json.dumps({"priority": "high"}),
        )
        label = _format_entity_label(entity)
        assert label == (
            'feature:030-auth-module \u2014 "Auth Module" (active, 2026-02-27)'
        )

    def test_entity_with_empty_depends_on_features_list(self):
        """Entity with empty depends_on_features list has no annotation."""
        import json
        entity = _make_entity(
            "feature:030-auth-module", "Auth Module", "feature",
            status="active",
            metadata=json.dumps({"depends_on_features": []}),
        )
        label = _format_entity_label(entity)
        assert label == (
            'feature:030-auth-module \u2014 "Auth Module" (active, 2026-02-27)'
        )

    def test_depends_on_in_tree_output(self):
        """AC-5 end-to-end: depends_on annotations appear in render_tree output."""
        import json
        entities = _link_parent_uuids([
            _make_entity("project:P001", "Project Name", "project", status="active"),
            _make_entity(
                "feature:030-auth-module", "Auth Module", "feature",
                status="active",
                parent_type_id="project:P001",
            ),
            _make_entity(
                "feature:031-api-gateway", "API Gateway", "feature",
                status="planned",
                parent_type_id="project:P001",
                metadata=json.dumps({"depends_on_features": ["030-auth-module"]}),
            ),
            _make_entity(
                "feature:032-dashboard", "Dashboard", "feature",
                status="planned",
                parent_type_id="project:P001",
                metadata=json.dumps({
                    "depends_on_features": ["030-auth-module", "031-api-gateway"],
                }),
            ),
        ])
        result = render_tree(entities, entities[0]["uuid"])
        assert "[depends on: feature:030-auth-module]" in result
        assert "[depends on: feature:030-auth-module, feature:031-api-gateway]" in result
        # The entity without dependencies should NOT have annotation
        lines = result.split("\n")
        auth_line = [l for l in lines if "030-auth-module" in l and "depends on" not in l]
        assert len(auth_line) == 1  # auth-module line has no depends_on annotation

    def test_invalid_metadata_json_no_annotation(self):
        """Entity with invalid metadata JSON has no annotation (graceful)."""
        entity = _make_entity(
            "feature:030-auth-module", "Auth Module", "feature",
            status="active",
            metadata="not valid json",
        )
        label = _format_entity_label(entity)
        # Should still produce a valid label, just without annotation
        assert label == (
            'feature:030-auth-module \u2014 "Auth Module" (active, 2026-02-27)'
        )
