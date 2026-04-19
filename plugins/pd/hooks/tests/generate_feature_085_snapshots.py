"""One-shot snapshot generator for feature 085 hardening tests.

Runs against the PRE-PR codebase to capture golden-file baselines for
user-facing markdown outputs. Regenerating (post-PR) should produce
byte-identical outputs for the clean fixture inputs — any drift is a
behavioral regression and must be justified in the commit message.

Usage:
    python plugins/pd/hooks/tests/generate_feature_085_snapshots.py

Pytest ignores `generate_*.py` by default (collection pattern is
`test_*.py`), so this script sits alongside the test file without being
invoked during normal test runs.
"""
from __future__ import annotations

import os
import sys
from pathlib import Path


# Make `pattern_promotion.generators` importable when running this
# script directly (the tests rely on pytest's rootdir conftest; a
# standalone script needs to insert the lib path itself).
_HERE = Path(__file__).resolve().parent
_HOOKS_LIB = _HERE.parent / "lib"
if str(_HOOKS_LIB) not in sys.path:
    sys.path.insert(0, str(_HOOKS_LIB))

from pattern_promotion.generators._md_insert import _render_block, insert_block
from pattern_promotion.kb_parser import _parse_file


FIXTURES_DIR = _HERE / "fixtures" / "feature_085_snapshots"
INPUT_KB = FIXTURES_DIR / "input_kb.md"
RENDER_BLOCK_OUT = FIXTURES_DIR / "render_block.md"
INSERT_BLOCK_OUT = FIXTURES_DIR / "md_insert.md"


# Deterministic target markdown used for the insert_block snapshot. The
# heading + a small bullet list exercises the `append-to-list` branch.
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


def main() -> None:
    entries, _promoted = _parse_file(INPUT_KB)
    if len(entries) < 1:
        raise SystemExit(
            f"expected >= 1 entry in {INPUT_KB}, got {len(entries)}"
        )

    # Use the first entry as the subject for both snapshots — deterministic
    # and covers both `append-to-list` and `_render_block` default paths.
    entry = entries[0]

    rendered_lines = _render_block(
        entry_name=entry.name,
        description=entry.description,
        mode="append-to-list",
    )
    # Join the block lines so reviewers can read the fixture directly; a
    # trailing newline keeps the file POSIX-friendly and diff-stable.
    render_block_text = "\n".join(rendered_lines) + "\n"

    inserted = insert_block(
        text=_TARGET_MD,
        heading="## Promoted Guidance",
        mode="append-to-list",
        entry_name=entry.name,
        description=entry.description,
    )

    RENDER_BLOCK_OUT.write_text(render_block_text, encoding="utf-8")
    INSERT_BLOCK_OUT.write_text(inserted, encoding="utf-8")

    print(f"wrote {RENDER_BLOCK_OUT.relative_to(Path.cwd()) if RENDER_BLOCK_OUT.is_relative_to(Path.cwd()) else RENDER_BLOCK_OUT}")
    print(f"wrote {INSERT_BLOCK_OUT.relative_to(Path.cwd()) if INSERT_BLOCK_OUT.is_relative_to(Path.cwd()) else INSERT_BLOCK_OUT}")


if __name__ == "__main__":
    main()
