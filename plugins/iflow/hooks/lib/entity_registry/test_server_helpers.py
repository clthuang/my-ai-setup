"""Tests for entity_registry.server_helpers module."""
from __future__ import annotations

import pytest

from entity_registry.database import EntityDatabase
from entity_registry.server_helpers import (
    _process_get_lineage,
    _process_register_entity,
    parse_metadata,
    render_tree,
    resolve_output_path,
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
) -> dict:
    """Helper to create an entity dict matching the database row shape."""
    return {
        "type_id": type_id,
        "name": name,
        "entity_type": entity_type,
        "status": status,
        "parent_type_id": parent_type_id,
        "created_at": created_at,
    }


class TestRenderTree:
    def test_single_node_no_status(self):
        """A single node with no status renders without status in parens."""
        entities = [
            _make_entity("project:alpha", "Alpha", "project"),
        ]
        result = render_tree(entities, "project:alpha")
        assert result == 'project:alpha \u2014 "Alpha" (2026-02-27)'

    def test_single_node_with_status(self):
        """A single node with status renders status before date."""
        entities = [
            _make_entity("project:alpha", "Alpha", "project", status="active"),
        ]
        result = render_tree(entities, "project:alpha")
        assert result == 'project:alpha \u2014 "Alpha" (active, 2026-02-27)'

    def test_linear_chain_three_deep(self):
        """A 3-node linear chain renders with proper indentation."""
        entities = [
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
        ]
        result = render_tree(entities, "backlog:00019")
        expected = (
            'backlog:00019 \u2014 "Item" (promoted, 2026-02-27)\n'
            '  \u2514\u2500 brainstorm:20260227-lineage \u2014 "Entity Lineage" (2026-02-27)\n'
            '     \u2514\u2500 feature:029-entity-lineage-tracking \u2014 "Entity Lineage" (active, 2026-02-27)'
        )
        assert result == expected

    def test_branching_tree_two_children(self):
        """Two children: first uses box tee, second uses corner."""
        entities = [
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
        ]
        result = render_tree(entities, "project:root")
        expected = (
            'project:root \u2014 "Root" (active, 2026-02-27)\n'
            '  \u251c\u2500 feature:a \u2014 "Alpha" (2026-02-27)\n'
            '  \u2514\u2500 feature:b \u2014 "Beta" (done, 2026-02-27)'
        )
        assert result == expected

    def test_branching_tree_with_nested_children(self):
        """A root with two children, first child has a grandchild."""
        entities = [
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
        ]
        result = render_tree(entities, "project:root")
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
        """If root_type_id is not in the entities list, return empty."""
        entities = [
            _make_entity("feature:a", "Alpha", "feature"),
        ]
        result = render_tree(entities, "project:missing")
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
    def test_relative_path_resolved_against_artifacts_root(self):
        """A relative path should be joined with artifacts_root."""
        result = resolve_output_path("features/f1/spec.md", "/home/user/docs")
        assert result == "/home/user/docs/features/f1/spec.md"

    def test_absolute_path_used_as_is(self):
        """An absolute path should be returned unchanged."""
        result = resolve_output_path("/absolute/path/file.md", "/home/user/docs")
        assert result == "/absolute/path/file.md"

    def test_none_returns_none(self):
        """None input should return None."""
        result = resolve_output_path(None, "/home/user/docs")
        assert result is None

    def test_simple_filename_resolved(self):
        """A bare filename should be joined with artifacts_root."""
        result = resolve_output_path("spec.md", "/project/docs")
        assert result == "/project/docs/spec.md"

    def test_artifacts_root_trailing_slash(self):
        """Trailing slash on artifacts_root should not double up."""
        result = resolve_output_path("features/spec.md", "/project/docs/")
        # os.path.join handles trailing slash correctly
        assert result == "/project/docs/features/spec.md"


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
