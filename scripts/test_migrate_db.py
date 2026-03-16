"""Tests for migrate_db.py CLI scaffold."""

import json
import subprocess
import sys
from pathlib import Path

import pytest

SCRIPT = str(Path(__file__).parent / "migrate_db.py")

SUBCOMMANDS = [
    "backup",
    "manifest",
    "validate",
    "merge-memory",
    "merge-entities",
    "verify",
    "info",
    "check-embeddings",
]


# --- Task 1.1: test_subcommand_help ---


@pytest.mark.parametrize("subcommand", SUBCOMMANDS)
def test_subcommand_help(subcommand: str) -> None:
    """Each subcommand --help exits 0 and shows usage text."""
    result = subprocess.run(
        [sys.executable, SCRIPT, subcommand, "--help"],
        capture_output=True,
        text=True,
        timeout=10,
    )
    assert result.returncode == 0, f"{subcommand} --help failed: {result.stderr}"
    assert "usage:" in result.stdout.lower(), (
        f"{subcommand} --help missing usage text"
    )


# --- Task 1.2: test_subcommand_stubs ---

# Each tuple: (subcommand, list of minimal required args)
SUBCOMMAND_ARGS = [
    ("backup", ["src.db", "dst.db", "--table", "entries"]),
    ("manifest", ["staging-dir", "--plugin-version", "1.0.0"]),
    ("validate", ["bundle-dir"]),
    ("merge-memory", ["src.db", "dst.db"]),
    ("merge-entities", ["src.db", "dst.db"]),
    ("verify", ["db.db", "--expected-count", "5", "--table", "entries"]),
    ("info", ["manifest.json"]),
    ("check-embeddings", ["manifest.json", "dst-memory.db"]),
]


@pytest.mark.parametrize(
    "subcommand,args",
    SUBCOMMAND_ARGS,
    ids=[t[0] for t in SUBCOMMAND_ARGS],
)
def test_subcommand_stubs(subcommand: str, args: list[str]) -> None:
    """Each subcommand with minimal args outputs valid JSON and exits 0."""
    result = subprocess.run(
        [sys.executable, SCRIPT, subcommand, *args],
        capture_output=True,
        text=True,
        timeout=10,
    )
    assert result.returncode == 0, (
        f"{subcommand} failed (exit {result.returncode}): {result.stderr}"
    )
    parsed = json.loads(result.stdout)
    assert isinstance(parsed, dict), f"{subcommand} did not return a JSON object"
