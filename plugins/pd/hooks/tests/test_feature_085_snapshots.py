"""Golden-file snapshot tests for feature 085 (memory-server-hardening).

Baselines were captured against the PRE-PR codebase by
`generate_feature_085_snapshots.py` (see `plugins/pd/hooks/tests/`).
Post-PR runs MUST produce byte-identical outputs for the clean input
fixture; drift signals a behavioral change in the user-facing markdown
rendering path and must be explicitly justified before merging.

Only FR-1 (entry_name sanitization) and FR-4 (config_utils extraction)
could plausibly affect these outputs; the fixture is constructed to
avoid all forbidden substrings so FR-1 never rejects and FR-4 is not
invoked by `_render_block` / `insert_block`.
"""
from __future__ import annotations

import os
import sys
from pathlib import Path


# Ensure `pattern_promotion` is importable both under pytest and when
# running this file directly. pytest's rootdir conftest already handles
# most of this, but we add the hooks/lib path explicitly for hermeticity.
_HERE = Path(__file__).resolve().parent
_HOOKS_LIB = _HERE.parent / "lib"
if str(_HOOKS_LIB) not in sys.path:
    sys.path.insert(0, str(_HOOKS_LIB))

from pattern_promotion.generators._md_insert import _render_block, insert_block
from pattern_promotion.kb_parser import _parse_file


_FIXTURES_DIR = _HERE / "fixtures" / "feature_085_snapshots"
_INPUT_KB = _FIXTURES_DIR / "input_kb.md"
_RENDER_BLOCK_GOLDEN = _FIXTURES_DIR / "render_block.md"
_INSERT_BLOCK_GOLDEN = _FIXTURES_DIR / "md_insert.md"


# Must match the constant used by `generate_feature_085_snapshots.py`.
_TARGET_MD = (
    "# Target\n"
    "\n"
    "## Promoted Guidance\n"
    "\n"
    "- existing bullet one\n"
    "- existing bullet two\n"
    "\n"
    "## Tail\n"
    "\n"
    "Trailing content.\n"
)


def _first_entry():
    entries, _promoted = _parse_file(_INPUT_KB)
    assert entries, f"fixture parsed zero entries: {_INPUT_KB}"
    return entries[0]


def test_render_block_snapshot_matches():
    """_render_block output for the first fixture entry must match the golden file."""
    entry = _first_entry()
    actual = "\n".join(
        _render_block(
            entry_name=entry.name,
            description=entry.description,
            mode="append-to-list",
        )
    ) + "\n"
    expected = _RENDER_BLOCK_GOLDEN.read_text(encoding="utf-8")
    assert actual == expected, (
        "Snapshot drift in _render_block output. "
        "If intentional, re-run generate_feature_085_snapshots.py and "
        "justify in the commit message."
    )


def test_insert_block_snapshot_matches():
    """insert_block output for the first fixture entry must match the golden file."""
    entry = _first_entry()
    actual = insert_block(
        text=_TARGET_MD,
        heading="## Promoted Guidance",
        mode="append-to-list",
        entry_name=entry.name,
        description=entry.description,
    )
    expected = _INSERT_BLOCK_GOLDEN.read_text(encoding="utf-8")
    assert actual == expected, (
        "Snapshot drift in insert_block output. "
        "If intentional, re-run generate_feature_085_snapshots.py and "
        "justify in the commit message."
    )
