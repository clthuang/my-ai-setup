"""Unit tests for entity route helpers."""


# ===========================================================================
# Task 1.2: _build_workflow_lookup
# ===========================================================================


class _StubDB:
    """Minimal stub with a list_workflow_phases() method."""

    def __init__(self, phases: list[dict]):
        self._phases = phases

    def list_workflow_phases(self) -> list[dict]:
        return self._phases


def test_build_workflow_lookup_empty_list():
    """Empty phase list returns empty dict."""
    from ui.routes.entities import _build_workflow_lookup

    db = _StubDB([])
    assert _build_workflow_lookup(db) == {}


def test_build_workflow_lookup_correct_keys():
    """Entries are keyed by type_id."""
    from ui.routes.entities import _build_workflow_lookup

    phases = [
        {"type_id": "feature:alpha", "workflow_phase": "design"},
        {"type_id": "feature:beta", "workflow_phase": "implement"},
    ]
    db = _StubDB(phases)
    result = _build_workflow_lookup(db)

    assert len(result) == 2
    assert result["feature:alpha"] == phases[0]
    assert result["feature:beta"] == phases[1]


def test_build_workflow_lookup_last_wins_on_collision():
    """When two entries share a type_id, the last one wins."""
    from ui.routes.entities import _build_workflow_lookup

    phases = [
        {"type_id": "feature:dup", "workflow_phase": "first"},
        {"type_id": "feature:dup", "workflow_phase": "second"},
    ]
    db = _StubDB(phases)
    result = _build_workflow_lookup(db)

    assert len(result) == 1
    assert result["feature:dup"]["workflow_phase"] == "second"


# ===========================================================================
# Task 1.3: _strip_self_from_lineage
# ===========================================================================


def test_strip_self_from_lineage_empty():
    """Empty lineage list returns empty list."""
    from ui.routes.entities import _strip_self_from_lineage

    assert _strip_self_from_lineage([], "feature:x") == []


def test_strip_self_from_lineage_self_removed():
    """Entry matching type_id is removed."""
    from ui.routes.entities import _strip_self_from_lineage

    lineage = [
        {"type_id": "project:parent", "name": "Parent"},
        {"type_id": "feature:self", "name": "Self"},
        {"type_id": "feature:sibling", "name": "Sibling"},
    ]
    result = _strip_self_from_lineage(lineage, "feature:self")

    assert len(result) == 2
    assert all(e["type_id"] != "feature:self" for e in result)


def test_strip_self_from_lineage_absent_returns_all():
    """When type_id is not in lineage, all entries are returned unchanged."""
    from ui.routes.entities import _strip_self_from_lineage

    lineage = [
        {"type_id": "project:a", "name": "A"},
        {"type_id": "feature:b", "name": "B"},
    ]
    result = _strip_self_from_lineage(lineage, "feature:missing")

    assert result == lineage


# ===========================================================================
# Task 1.4: _format_metadata
# ===========================================================================


def test_format_metadata_none():
    """None returns empty string."""
    from ui.routes.entities import _format_metadata

    assert _format_metadata(None) == ""


def test_format_metadata_empty_string():
    """Empty string returns empty string."""
    from ui.routes.entities import _format_metadata

    assert _format_metadata("") == ""


def test_format_metadata_valid_json():
    """Valid JSON string returns pretty-printed JSON."""
    from ui.routes.entities import _format_metadata
    import json

    raw = '{"key": "value", "num": 42}'
    result = _format_metadata(raw)
    expected = json.dumps({"key": "value", "num": 42}, indent=2)

    assert result == expected


def test_format_metadata_invalid_json():
    """Invalid JSON returns the raw string unchanged."""
    from ui.routes.entities import _format_metadata

    raw = "not valid json {{"
    assert _format_metadata(raw) == raw


# ===========================================================================
# Task 1.5a: entity_list error and fallback code paths
# ===========================================================================

import sqlite3
import unittest.mock
from starlette.testclient import TestClient
from entity_registry.database import EntityDatabase


def _seed_entity(db_file, type_id, entity_type="feature", name=None,
                 status="active", entity_id=None):
    """Insert an entity row for testing (FKs disabled)."""
    conn = sqlite3.connect(db_file)
    conn.execute("PRAGMA foreign_keys = OFF")
    now = "2026-03-08T00:00:00Z"
    conn.execute(
        "INSERT OR IGNORE INTO entities "
        "(type_id, uuid, entity_type, entity_id, name, status, "
        "artifact_path, metadata, created_at, updated_at) "
        "VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?)",
        (type_id, f"uuid-{type_id}", entity_type, entity_id or type_id,
         name or type_id, status, None, None, now, now),
    )
    conn.commit()
    conn.close()


# ---------------------------------------------------------------------------
# Task 1.5a.1: entity_list — missing DB returns error page
# ---------------------------------------------------------------------------
def test_entity_list_missing_db_shows_error():
    """GET /entities with no DB renders error.html with ENTITY_DB_PATH."""
    from ui import create_app

    app = create_app(db_path="/nonexistent/path.db")
    client = TestClient(app)
    response = client.get("/entities")

    assert response.status_code == 200
    assert "Database Not Found" in response.text
    assert "ENTITY_DB_PATH" in response.text


# ---------------------------------------------------------------------------
# Task 1.5a.2: entity_list — DB query error renders error page
# ---------------------------------------------------------------------------
def test_entity_list_db_error_shows_error_message(tmp_path):
    """GET /entities renders error page when DB query raises exception."""
    db_file = str(tmp_path / "test.db")
    EntityDatabase(db_file)

    from ui import create_app

    app = create_app(db_path=db_file)
    app.state.db.list_entities = unittest.mock.MagicMock(
        side_effect=Exception("entity query failed")
    )
    client = TestClient(app)
    response = client.get("/entities")

    assert response.status_code == 200
    assert "entity query failed" in response.text


# ---------------------------------------------------------------------------
# Task 1.5a.3: entity_list — DB error logged to stderr
# ---------------------------------------------------------------------------
def test_entity_list_db_error_logged_to_stderr(tmp_path, capsys):
    """DB query error in entity_list is printed to stderr."""
    db_file = str(tmp_path / "test.db")
    EntityDatabase(db_file)

    from ui import create_app

    app = create_app(db_path=db_file)
    app.state.db.list_entities = unittest.mock.MagicMock(
        side_effect=Exception("stderr test")
    )
    client = TestClient(app)
    client.get("/entities")

    captured = capsys.readouterr()
    assert "stderr test" in captured.err


# ---------------------------------------------------------------------------
# Task 1.5a.4: entity_list — search ValueError falls back to list_entities
# ---------------------------------------------------------------------------
def test_entity_list_search_valueerror_falls_back(tmp_path):
    """When search_entities raises ValueError, falls back to list_entities."""
    db_file = str(tmp_path / "test.db")
    EntityDatabase(db_file)
    _seed_entity(db_file, "feature:fallback-test", name="Fallback Feature")

    from ui import create_app

    app = create_app(db_path=db_file)
    # search_entities raises ValueError (FTS unavailable)
    app.state.db.search_entities = unittest.mock.MagicMock(
        side_effect=ValueError("fts_not_available")
    )
    client = TestClient(app)
    response = client.get("/entities?q=test")

    assert response.status_code == 200
    # Should show "Search unavailable" in the partial content
    assert "Search unavailable" in response.text
    # Should still render entities from list_entities fallback
    assert "Fallback Feature" in response.text


# ---------------------------------------------------------------------------
# Task 1.5a.5: entity_list — empty entities returns page with no crash
# ---------------------------------------------------------------------------
def test_entity_list_empty_returns_page(tmp_path):
    """GET /entities with empty DB returns entities.html without error."""
    db_file = str(tmp_path / "test.db")
    EntityDatabase(db_file)

    from ui import create_app

    app = create_app(db_path=db_file)
    client = TestClient(app)
    response = client.get("/entities")

    assert response.status_code == 200
    assert "Entities" in response.text


# ===========================================================================
# Task 1.6a: entity_detail error and 404 code paths
# ===========================================================================


# ---------------------------------------------------------------------------
# Task 1.6a.1: entity_detail — missing DB returns error page
# ---------------------------------------------------------------------------
def test_entity_detail_missing_db_shows_error():
    """GET /entities/<id> with no DB renders error.html."""
    from ui import create_app

    app = create_app(db_path="/nonexistent/path.db")
    client = TestClient(app)
    response = client.get("/entities/feature:test")

    assert response.status_code == 200
    assert "Database Not Found" in response.text


# ---------------------------------------------------------------------------
# Task 1.6a.2: entity_detail — entity not found returns 404
# ---------------------------------------------------------------------------
def test_entity_detail_not_found_returns_404(tmp_path):
    """GET /entities/<nonexistent> returns 404.html with status_code=404."""
    db_file = str(tmp_path / "test.db")
    EntityDatabase(db_file)

    from ui import create_app

    app = create_app(db_path=db_file)
    client = TestClient(app)
    response = client.get("/entities/feature:nonexistent")

    assert response.status_code == 404
    assert "Entity not found" in response.text


# ---------------------------------------------------------------------------
# Task 1.6a.3: entity_detail — DB error renders error page
# ---------------------------------------------------------------------------
def test_entity_detail_db_error_shows_error(tmp_path):
    """GET /entities/<id> renders error page when get_entity raises."""
    db_file = str(tmp_path / "test.db")
    EntityDatabase(db_file)

    from ui import create_app

    app = create_app(db_path=db_file)
    app.state.db.get_entity = unittest.mock.MagicMock(
        side_effect=Exception("detail query failed")
    )
    client = TestClient(app)
    response = client.get("/entities/feature:test")

    assert response.status_code == 200
    assert "detail query failed" in response.text


# ---------------------------------------------------------------------------
# Task 1.6a.4: entity_detail — DB error logged to stderr
# ---------------------------------------------------------------------------
def test_entity_detail_db_error_logged_to_stderr(tmp_path, capsys):
    """DB query error in entity_detail is printed to stderr."""
    db_file = str(tmp_path / "test.db")
    EntityDatabase(db_file)

    from ui import create_app

    app = create_app(db_path=db_file)
    app.state.db.get_entity = unittest.mock.MagicMock(
        side_effect=Exception("detail stderr test")
    )
    client = TestClient(app)
    client.get("/entities/feature:test")

    captured = capsys.readouterr()
    assert "detail stderr test" in captured.err


# ===========================================================================
# Task 2.3: entities.html template
# ===========================================================================


# ---------------------------------------------------------------------------
# Task 2.3.1: entities.html extends base.html
# ---------------------------------------------------------------------------
def test_entities_html_extends_base():
    """entities.html contains {% extends 'base.html' %}."""
    from pathlib import Path

    template_path = Path(__file__).parent.parent / "templates" / "entities.html"
    content = template_path.read_text()

    assert '{% extends "base.html" %}' in content


# ---------------------------------------------------------------------------
# Task 2.3.2: entities.html contains entities-content div
# ---------------------------------------------------------------------------
def test_entities_html_has_entities_content_div():
    """entities.html contains <div id='entities-content'>."""
    from pathlib import Path

    template_path = Path(__file__).parent.parent / "templates" / "entities.html"
    content = template_path.read_text()

    assert 'id="entities-content"' in content


# ---------------------------------------------------------------------------
# Task 2.3.3: entities.html includes _entities_content.html
# ---------------------------------------------------------------------------
def test_entities_html_includes_partial():
    """entities.html contains {% include '_entities_content.html' %}."""
    from pathlib import Path

    template_path = Path(__file__).parent.parent / "templates" / "entities.html"
    content = template_path.read_text()

    assert '{% include "_entities_content.html" %}' in content


# ---------------------------------------------------------------------------
# Task 2.3.4: entities.html has page heading
# ---------------------------------------------------------------------------
def test_entities_html_has_page_heading():
    """entities.html has a heading with 'Entities'."""
    from pathlib import Path

    template_path = Path(__file__).parent.parent / "templates" / "entities.html"
    content = template_path.read_text()

    assert "Entities" in content


# ===========================================================================
# Phase 4: Integration Tests — entity list, detail, lineage, search, HTMX
# ===========================================================================

import pytest


@pytest.fixture()
def integration_client(tmp_path):
    """Create a DB seeded with entities and workflow data, return TestClient.

    Entities seeded:
    - feature:feat-alpha  (active, parent=project:proj-one, workflow_phase=implement)
    - feature:feat-beta   (completed, no parent, no workflow)
    - brainstorm:bs-one   (active, no parent, no workflow)
    - project:proj-one    (active, no parent, no workflow)
    """
    db = EntityDatabase(str(tmp_path / "test.db"))

    # Seed entities via the DB API
    db.register_entity("feature", "feat-alpha", "Alpha Feature", status="active")
    db.register_entity("feature", "feat-beta", "Beta Feature", status="completed")
    db.register_entity("brainstorm", "bs-one", "Brainstorm One", status="active")
    db.register_entity("project", "proj-one", "Project One", status="active")

    # Set parent relationship: feat-alpha -> proj-one
    db.set_parent("feature:feat-alpha", "project:proj-one")

    # Disable FK enforcement for raw workflow_phases insert
    db._conn.execute("PRAGMA foreign_keys = OFF")

    # Seed workflow phase for feat-alpha
    # kanban_column must be a valid CHECK value (wip, not "In Progress")
    db._conn.execute(
        "INSERT INTO workflow_phases "
        "(type_id, kanban_column, workflow_phase, updated_at) "
        "VALUES (?, ?, ?, ?)",
        ("feature:feat-alpha", "wip", "implement", "2026-03-08T00:00:00Z"),
    )
    db._conn.commit()

    # Build the app and test client
    from ui import create_app

    app = create_app(str(tmp_path / "test.db"))
    client = TestClient(app)
    return client


# ---------------------------------------------------------------------------
# Task 4.1.1: Entity list returns all seeded entities (FR-1)
# ---------------------------------------------------------------------------
def test_integration_entity_list_returns_all_entities(integration_client):
    """GET /entities returns HTTP 200 with all 4 seeded entities in the table."""
    response = integration_client.get("/entities")

    assert response.status_code == 200
    assert "Alpha Feature" in response.text
    assert "Beta Feature" in response.text
    assert "Brainstorm One" in response.text
    assert "Project One" in response.text
    # Verify entity count indicator
    assert "4 entities" in response.text


# ---------------------------------------------------------------------------
# Task 4.1.2: Type filtering returns only matching entities (FR-2)
# ---------------------------------------------------------------------------
def test_integration_entity_list_type_filter(integration_client):
    """GET /entities?type=feature returns only feature entities."""
    response = integration_client.get("/entities?type=feature")

    assert response.status_code == 200
    assert "Alpha Feature" in response.text
    assert "Beta Feature" in response.text
    # Non-feature entities should NOT appear in the table rows
    assert "Brainstorm One" not in response.text
    assert "Project One" not in response.text
    assert "2 entities" in response.text


# ---------------------------------------------------------------------------
# Task 4.1.3: Status filtering returns only matching entities (FR-3)
# ---------------------------------------------------------------------------
def test_integration_entity_list_status_filter(integration_client):
    """GET /entities?status=active returns only active entities."""
    response = integration_client.get("/entities?status=active")

    assert response.status_code == 200
    assert "Alpha Feature" in response.text
    assert "Brainstorm One" in response.text
    assert "Project One" in response.text
    # Beta Feature has status=completed, should be filtered out
    assert "Beta Feature" not in response.text
    assert "3 entities" in response.text


# ---------------------------------------------------------------------------
# Task 4.2.1: Entity detail returns full data with workflow fields (FR-4)
# ---------------------------------------------------------------------------
def test_integration_entity_detail_with_workflow(integration_client):
    """GET /entities/feature:feat-alpha returns 200 with entity + workflow data."""
    response = integration_client.get("/entities/feature:feat-alpha")

    assert response.status_code == 200
    # Entity fields
    assert "Alpha Feature" in response.text
    assert "feature:feat-alpha" in response.text
    assert "active" in response.text
    # Workflow fields from the template (kanban_column, workflow_phase)
    assert "wip" in response.text
    assert "implement" in response.text
    # Workflow State section should be rendered
    assert "Workflow State" in response.text


# ---------------------------------------------------------------------------
# Task 4.2.2: Entity detail 404 for nonexistent entity (FR-4)
# ---------------------------------------------------------------------------
def test_integration_entity_detail_not_found(integration_client):
    """GET /entities/nonexistent:xxx returns HTTP 404 with 'Entity not found'."""
    response = integration_client.get("/entities/nonexistent:xxx")

    assert response.status_code == 404
    assert "Entity not found" in response.text


# ---------------------------------------------------------------------------
# Task 4.2.3: Lineage — ancestors and children displayed (FR-5)
# ---------------------------------------------------------------------------
def test_integration_entity_detail_lineage(integration_client):
    """Detail page for feat-alpha shows ancestors (proj-one) and no children.
    Detail page for proj-one shows no ancestors and children (feat-alpha).
    Self is stripped from both lists."""
    # feat-alpha has parent proj-one
    response = integration_client.get("/entities/feature:feat-alpha")
    assert response.status_code == 200
    # Ancestors section should show the parent
    assert "project:proj-one" in response.text
    # feat-alpha has no children, so "No children" should appear
    assert "No children" in response.text

    # proj-one is a parent, should show feat-alpha as child
    response_parent = integration_client.get("/entities/project:proj-one")
    assert response_parent.status_code == 200
    # Children section should show the child
    assert "feature:feat-alpha" in response_parent.text
    # proj-one has no parent, so "No parent" should appear
    assert "No parent" in response_parent.text


# ---------------------------------------------------------------------------
# Task 4.3.1: Search returns FTS matches; fallback on FTS unavailable (FR-8)
# ---------------------------------------------------------------------------
def test_integration_search_returns_fts_matches(integration_client):
    """GET /entities?q=Alpha returns entities matching the FTS query."""
    response = integration_client.get("/entities?q=Alpha")

    assert response.status_code == 200
    assert "Alpha Feature" in response.text


def test_integration_search_fts_fallback(tmp_path):
    """When search_entities raises ValueError, fallback returns all entities
    with search input disabled."""
    db = EntityDatabase(str(tmp_path / "test.db"))
    db.register_entity("feature", "fb-test", "Fallback Test", status="active")

    from ui import create_app

    app = create_app(str(tmp_path / "test.db"))
    # Mock search_entities to raise ValueError (FTS unavailable)
    app.state.db.search_entities = unittest.mock.MagicMock(
        side_effect=ValueError("FTS index not available")
    )
    client = TestClient(app)
    response = client.get("/entities?q=term")

    assert response.status_code == 200
    # Fallback shows all entities (from list_entities)
    assert "Fallback Test" in response.text
    # Search should be marked as unavailable
    assert "Search unavailable" in response.text


# ---------------------------------------------------------------------------
# Task 4.3.2: HTMX partial — no <html> tag, has table content (FR-9)
# ---------------------------------------------------------------------------
def test_integration_htmx_partial_entities(integration_client):
    """GET /entities with HX-Request header returns content partial only.
    No <html> tag, but has the table."""
    response = integration_client.get(
        "/entities", headers={"HX-Request": "true"}
    )

    assert response.status_code == 200
    # Partial should NOT contain <html> (no full page wrapper)
    assert "<html" not in response.text
    # Partial SHOULD contain the table with entities
    assert "<table" in response.text
    assert "Alpha Feature" in response.text


# ---------------------------------------------------------------------------
# Task 4.3.3: Missing DB returns error.html content
# ---------------------------------------------------------------------------
def test_integration_entities_missing_db_error():
    """App with nonexistent DB path returns error page for /entities."""
    from ui import create_app

    app = create_app(db_path="/nonexistent/path.db")
    client = TestClient(app)
    response = client.get("/entities")

    assert response.status_code == 200
    assert "Database Not Found" in response.text
    assert "ENTITY_DB_PATH" in response.text
