"""Tests for entity_server MCP handler dual-identity messages."""
from __future__ import annotations

import os
import re
import sys

import pytest

# Make entity_server importable.
_mcp_dir = os.path.normpath(os.path.join(os.path.dirname(__file__), "..", "..", "..", "mcp"))
if _mcp_dir not in sys.path:
    sys.path.insert(0, _mcp_dir)

import entity_server
from entity_registry.database import EntityDatabase

_UUID_V4_RE = re.compile(
    r"[0-9a-f]{8}-[0-9a-f]{4}-4[0-9a-f]{3}-[89ab][0-9a-f]{3}-[0-9a-f]{12}"
)


@pytest.fixture
def db(tmp_path, monkeypatch):
    """Provide EntityDatabase and inject into entity_server._db."""
    database = EntityDatabase(str(tmp_path / "test.db"))
    monkeypatch.setattr(entity_server, "_db", database)
    yield database
    database.close()


@pytest.mark.asyncio
async def test_set_parent_handler_dual_identity_message(db):
    """set_parent handler response contains both UUID and type_id for child and parent."""
    parent_uuid = db.register_entity("project", "parent", "Parent Project", status="active")
    child_uuid = db.register_entity("feature", "child", "Child Feature")

    result = await entity_server.set_parent("feature:child", "project:parent")

    assert isinstance(result, str)
    # Should contain child UUID and type_id
    assert child_uuid in result
    assert "feature:child" in result
    # Should contain parent UUID and type_id
    assert parent_uuid in result
    assert "project:parent" in result


@pytest.mark.asyncio
async def test_update_entity_handler_dual_identity_message(db):
    """update_entity handler response contains both UUID and type_id."""
    entity_uuid = db.register_entity("feature", "f1", "Feature One", status="active")

    result = await entity_server.update_entity("feature:f1", status="completed")

    assert isinstance(result, str)
    # Should contain UUID
    assert _UUID_V4_RE.search(result)
    # Should contain type_id
    assert "feature:f1" in result


# ---------------------------------------------------------------------------
# Deepened tests: Phase B — spec-driven test deepening
# ---------------------------------------------------------------------------


@pytest.mark.asyncio
async def test_register_entity_handler_dual_identity_message(db):
    """register_entity handler response contains both UUID and type_id.
    Anticipate: If the handler only returns type_id (pre-migration behavior),
    the UUID would be missing from the response.
    derived_from: spec:R28, spec:R34
    """
    result = await entity_server.register_entity(
        entity_type="feature",
        entity_id="reg-test",
        name="Registration Test",
    )
    assert isinstance(result, str)
    # Should contain UUID
    assert _UUID_V4_RE.search(result), f"Expected UUID in: {result}"
    # Should contain type_id
    assert "feature:reg-test" in result
    # Should match format "Registered entity: {uuid} ({type_id})"
    assert "Registered entity:" in result


@pytest.mark.asyncio
async def test_set_parent_handler_uses_uuid_identifiers(db):
    """set_parent handler can accept UUID identifiers (not just type_id).
    Anticipate: If handler passes raw input to set_parent without
    dual-read resolution, UUID input would fail.
    derived_from: spec:R27, dimension:adversarial
    """
    parent_uuid = db.register_entity("project", "parent2", "Parent")
    child_uuid = db.register_entity("feature", "child2", "Child")
    # Use UUID for child and type_id for parent
    result = await entity_server.set_parent(child_uuid, "project:parent2")
    assert isinstance(result, str)
    # Should not contain "Error"
    assert "Error" not in result
    # Should contain both UUIDs and type_ids
    assert child_uuid in result
    assert parent_uuid in result


@pytest.mark.asyncio
async def test_get_entity_handler_returns_uuid_field(db):
    """get_entity handler response includes uuid field.
    Anticipate: If get_entity dict conversion drops uuid column,
    the response would be missing the canonical identifier.
    derived_from: spec:AC-17, spec:R28
    """
    entity_uuid = db.register_entity("feature", "get-test", "Get Test")
    result = await entity_server.get_entity("feature:get-test")
    assert isinstance(result, str)
    # Should contain the UUID somewhere in the response
    assert entity_uuid in result or _UUID_V4_RE.search(result)
