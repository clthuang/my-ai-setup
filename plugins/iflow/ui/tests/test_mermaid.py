"""Unit tests for Mermaid DAG builder module."""

import re


# ===========================================================================
# Phase 1: _sanitize_id tests (Task 1.1)
# ===========================================================================


def test_sanitize_id_special_chars():
    """feature:021-foo → feature_021_foo_ + 4 hex chars."""
    from ui.mermaid import _sanitize_id

    result = _sanitize_id("feature:021-foo")
    assert result.startswith("feature_021_foo_")
    assert len(result) == len("feature_021_foo_") + 4


def test_sanitize_id_no_collision():
    """Two type_ids differing only in : vs - produce different safe IDs."""
    from ui.mermaid import _sanitize_id

    assert _sanitize_id("a:b") != _sanitize_id("a-b")


def test_sanitize_id_regex_safe():
    """Result matches ^[a-zA-Z_][a-zA-Z0-9_]*$."""
    from ui.mermaid import _sanitize_id

    for tid in ["feature:021-foo", "a:b", "1abc", "order", "xray", "hello"]:
        result = _sanitize_id(tid)
        assert re.match(r"^[a-zA-Z_][a-zA-Z0-9_]*$", result), f"Failed for {tid}: {result}"


def test_sanitize_id_digit_prefix():
    """type_id starting with digit gets n prefix."""
    from ui.mermaid import _sanitize_id

    result = _sanitize_id("1abc")
    assert result.startswith("n")


def test_sanitize_id_o_x_prefix():
    """type_id starting with o or x gets n prefix."""
    from ui.mermaid import _sanitize_id

    assert _sanitize_id("order").startswith("n")
    assert _sanitize_id("xray").startswith("n")


# ===========================================================================
# Phase 1: _sanitize_label tests (Task 1.2)
# ===========================================================================


def test_sanitize_label_quotes():
    """Double quotes replaced with single quotes."""
    from ui.mermaid import _sanitize_label

    assert _sanitize_label('He said "hello"') == "He said 'hello'"


def test_sanitize_label_brackets():
    """Square brackets replaced with parentheses."""
    from ui.mermaid import _sanitize_label

    assert _sanitize_label("feature[0]") == "feature(0)"


def test_sanitize_label_backslash():
    """Backslash replaced with forward slash."""
    from ui.mermaid import _sanitize_label

    assert _sanitize_label("a\\b") == "a/b"


def test_sanitize_label_less_than():
    """< replaced with &lt;."""
    from ui.mermaid import _sanitize_label

    assert _sanitize_label("<script>") == "&lt;script&gt;"


def test_sanitize_label_greater_than():
    """> replaced with &gt;."""
    from ui.mermaid import _sanitize_label

    assert _sanitize_label("a>b") == "a&gt;b"


# ===========================================================================
# Phase 2: build_mermaid_dag tests (Task 2.1)
# ===========================================================================


def _entity(type_id, name=None, entity_type="feature", parent_type_id=None):
    """Helper to create an entity dict."""
    return {
        "type_id": type_id,
        "name": name,
        "entity_type": entity_type,
        "parent_type_id": parent_type_id,
    }


def test_output_starts_with_flowchart_td():
    """First line is 'flowchart TD'."""
    from ui.mermaid import build_mermaid_dag

    entity = _entity("feature:001", "Test")
    result = build_mermaid_dag(entity, [], [])
    assert result.split("\n")[0] == "flowchart TD"


def test_single_entity_no_lineage():
    """1 node, 0 edges, 0 click lines."""
    from ui.mermaid import build_mermaid_dag, _sanitize_id

    entity = _entity("feature:solo", "Solo")
    result = build_mermaid_dag(entity, [], [])
    lines = result.split("\n")

    safe_id = _sanitize_id("feature:solo")
    node_defs = [l for l in lines if '["' in l and "-->" not in l]
    edges = [l for l in lines if "-->" in l]
    clicks = [l for l in lines if l.strip().startswith("click ")]

    assert len(node_defs) == 1
    assert len(edges) == 0
    assert len(clicks) == 0


def test_linear_chain_four_entities():
    """4 nodes, 3 edges, 3 click lines (current excluded)."""
    from ui.mermaid import build_mermaid_dag

    gp = _entity("project:gp", "Grandparent", "project")
    p = _entity("feature:p", "Parent", "feature", parent_type_id="project:gp")
    current = _entity("feature:c", "Current", "feature", parent_type_id="feature:p")
    child = _entity("feature:ch", "Child", "feature", parent_type_id="feature:c")

    result = build_mermaid_dag(current, [gp, p], [child])
    lines = result.split("\n")

    node_defs = [l for l in lines if '["' in l and "-->" not in l]
    edges = [l for l in lines if "-->" in l]
    clicks = [l for l in lines if l.strip().startswith("click ")]

    assert len(node_defs) == 4
    assert len(edges) == 3
    assert len(clicks) == 3  # current excluded


def test_fan_out_multiple_children():
    """Parent with 3 children → 3 edges."""
    from ui.mermaid import build_mermaid_dag

    parent = _entity("project:p", "Parent", "project")
    c1 = _entity("feature:c1", "C1", "feature", parent_type_id="project:p")
    c2 = _entity("feature:c2", "C2", "feature", parent_type_id="project:p")
    c3 = _entity("feature:c3", "C3", "feature", parent_type_id="project:p")

    result = build_mermaid_dag(parent, [], [c1, c2, c3])
    edges = [l for l in result.split("\n") if "-->" in l]

    assert len(edges) == 3


def test_current_entity_not_clickable():
    """No click line for current entity."""
    from ui.mermaid import build_mermaid_dag, _sanitize_id

    current = _entity("feature:cur", "Current")
    safe_id = _sanitize_id("feature:cur")
    result = build_mermaid_dag(current, [], [])
    clicks = [l for l in result.split("\n") if l.strip().startswith("click ")]

    for click in clicks:
        assert safe_id not in click


def test_current_entity_gets_current_class():
    """Output contains 'class {safe_id} current'."""
    from ui.mermaid import build_mermaid_dag, _sanitize_id

    current = _entity("feature:cur", "Current")
    safe_id = _sanitize_id("feature:cur")
    result = build_mermaid_dag(current, [], [])

    assert f"class {safe_id} current" in result


def test_name_none_falls_back_to_type_id():
    """Node label uses type_id when name is None."""
    from ui.mermaid import build_mermaid_dag, _sanitize_id, _sanitize_label

    current = _entity("feature:unnamed", None)
    result = build_mermaid_dag(current, [], [])
    safe_label = _sanitize_label("feature:unnamed")

    assert f'["{safe_label}"]' in result


def test_duplicate_entities_deduped():
    """Same type_id in ancestors+children → count node defs = 1."""
    from ui.mermaid import build_mermaid_dag

    entity = _entity("feature:main", "Main")
    dup = _entity("feature:dup", "Dup", "feature", parent_type_id="feature:main")

    # Same entity in both ancestors and children
    result = build_mermaid_dag(entity, [dup], [dup])
    lines = result.split("\n")

    node_defs = [l for l in lines if '["' in l and "-->" not in l]
    # Should have 2 unique nodes: main + dup (not 3)
    assert len(node_defs) == 2


def test_unknown_entity_type_defaults_feature():
    """entity_type='custom' → class {id} feature."""
    from ui.mermaid import build_mermaid_dag, _sanitize_id

    current = _entity("feature:main", "Main")
    child = _entity("custom:child", "Child", "custom", parent_type_id="feature:main")

    result = build_mermaid_dag(current, [], [child])
    safe_id = _sanitize_id("custom:child")

    assert f"class {safe_id} feature" in result


def test_click_handler_uses_href_keyword():
    """Click line matches 'click .* href "/entities/.*"'."""
    from ui.mermaid import build_mermaid_dag

    current = _entity("feature:cur", "Current")
    child = _entity("feature:ch", "Child", "feature", parent_type_id="feature:cur")

    result = build_mermaid_dag(current, [], [child])
    clicks = [l for l in result.split("\n") if l.strip().startswith("click ")]

    assert len(clicks) == 1
    assert re.search(r'click .* href "/entities/.*"', clicks[0])


def test_click_handler_raw_type_id_with_colon():
    """Click line contains /entities/feature:021."""
    from ui.mermaid import build_mermaid_dag

    current = _entity("project:p", "P", "project")
    child = _entity("feature:021", "F021", "feature", parent_type_id="project:p")

    result = build_mermaid_dag(current, [], [child])
    clicks = [l for l in result.split("\n") if l.strip().startswith("click ")]

    assert any("/entities/feature:021" in c for c in clicks)


def test_classdef_lines_emitted():
    """Output contains classDef for feature, project, brainstorm, backlog, current."""
    from ui.mermaid import build_mermaid_dag

    entity = _entity("feature:x", "X")
    result = build_mermaid_dag(entity, [], [])

    assert "classDef feature" in result
    assert "classDef project" in result
    assert "classDef brainstorm" in result
    assert "classDef backlog" in result
    assert "classDef current" in result
    assert "fill:#1d4ed8" in result  # feature fill
    assert "fill:#059669" in result  # project fill
    assert "fill:#0891b2" in result  # brainstorm fill
    assert "fill:#4b5563" in result  # backlog fill
    assert "fill:#7c3aed" in result  # current fill
