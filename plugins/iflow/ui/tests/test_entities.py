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
