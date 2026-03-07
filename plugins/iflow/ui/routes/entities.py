"""Entities route — entity list and detail views."""

import json
import sys

from fastapi import APIRouter, Request
from fastapi.responses import HTMLResponse

router = APIRouter(prefix="/entities")

ENTITY_TYPES = ["backlog", "brainstorm", "project", "feature"]


def _build_workflow_lookup(db) -> dict:
    """Return {type_id: workflow_phase_row} from db.list_workflow_phases()."""
    return {wp["type_id"]: wp for wp in db.list_workflow_phases()}


def _strip_self_from_lineage(lineage: list[dict], type_id: str) -> list[dict]:
    """Remove the entry whose type_id matches from a lineage list."""
    return [e for e in lineage if e["type_id"] != type_id]


def _format_metadata(metadata: str | None) -> str:
    """Pretty-print metadata JSON, or return raw string on parse failure."""
    if not metadata:
        return ""
    try:
        return json.dumps(json.loads(metadata), indent=2)
    except (json.JSONDecodeError, TypeError):
        return metadata


@router.get("", response_class=HTMLResponse)
def entity_list(request: Request, type: str | None = None, status: str | None = None, q: str | None = None) -> HTMLResponse:
    return HTMLResponse("placeholder")


@router.get("/{identifier:path}", response_class=HTMLResponse)
def entity_detail(request: Request, identifier: str) -> HTMLResponse:
    return HTMLResponse("placeholder")
