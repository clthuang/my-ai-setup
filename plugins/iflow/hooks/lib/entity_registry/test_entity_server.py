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
