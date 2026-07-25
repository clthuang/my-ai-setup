"""Feature 134 NFR-4 trust-gate tests — #056 native-list params at the tool layer.

The transport JSON-parses string args shaped like JSON back into lists, so the
async tool boundary must accept native lists (backlog #056). These tests call
the ASYNC tools (not the _process helpers) because the normalization lives at
that boundary.
"""
from __future__ import annotations

import asyncio
import json
import os
import sys

import pytest

sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
sys.path.insert(
    0,
    os.path.join(
        os.path.dirname(os.path.abspath(__file__)), "..", "hooks", "lib"
    ),
)

import workflow_state_server as wss  # noqa: E402
from entity_registry.database import EntityDatabase  # noqa: E402
from workflow_engine.engine import WorkflowStateEngine  # noqa: E402
from test_workflow_state_server import _bootstrap_test_workspace  # noqa: E402


@pytest.fixture()
def tool_env(tmp_path, monkeypatch):
    """Point the module globals at a temp DB the way server startup does."""
    db = EntityDatabase(str(tmp_path / "entities.db"))
    ws_uuid = _bootstrap_test_workspace(db, "P-134")
    db.register_entity(
        "feature", "134-t", "T", status="active", project_id="P-134",
        workspace_uuid=ws_uuid,
    )
    db.create_workflow_phase(
        "feature:134-t", workflow_phase="brainstorm",
        last_completed_phase=None, mode="standard",
    )
    engine = WorkflowStateEngine(db, str(tmp_path))
    monkeypatch.setattr(wss, "_db", db)
    monkeypatch.setattr(wss, "_engine", engine)
    monkeypatch.setattr(wss, "_entity_engine", None)
    monkeypatch.setattr(wss, "_workspace_uuid", ws_uuid)
    yield db
    db.close()


def test_transition_tool_accepts_native_list_skipped_phases(tool_env):
    """#056: a native list produces one skipped row PER PHASE NAME (the
    double-encoded string form produced one row per CHARACTER — QA132-A)."""
    db = tool_env
    result = json.loads(asyncio.run(wss.transition_phase(
        feature_type_id="feature:134-t",
        target_phase="implement",
        yolo_active=True,
        skipped_phases=["specify", "design", "create-plan"],
    )))
    assert result.get("transitioned") is True, result
    rows = [
        r for r in db.query_phase_events(type_id="feature:134-t")
        if r["event_type"] == "skipped"
    ]
    assert sorted(r["phase"] for r in rows) == [
        "create-plan", "design", "specify",
    ], rows
    # Feature 134 QA blocker pin: the phase actually ADVANCES to the target —
    # transitioned=true + skipped rows alone were vacuously green while
    # last-skipped-wins projection left workflow_phase at 'create-plan'.
    row = db.get_workflow_phase("feature:134-t")
    assert row["workflow_phase"] == "implement", row


def test_complete_tool_accepts_native_list_reviewer_notes(tool_env):
    """#056: a native reviewer_notes list round-trips into the completed
    event's reviewer_notes column."""
    db = tool_env
    notes = ["blocker: none", "warning: naming"]
    result = json.loads(asyncio.run(wss.complete_phase(
        feature_type_id="feature:134-t",
        phase="brainstorm",
        iterations=1,
        reviewer_notes=notes,
    )))
    assert "error" not in result, result
    rows = [
        r for r in db.query_phase_events(
            type_id="feature:134-t", phase="brainstorm", event_type="completed",
        )
    ]
    assert len(rows) == 1, rows
    assert json.loads(rows[0]["reviewer_notes"]) == notes
