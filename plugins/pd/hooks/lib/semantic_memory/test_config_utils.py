"""Tests for `semantic_memory.config_utils.resolve_float_config`.

Extracted helper used by both `mcp/memory_server.py` and
`semantic_memory/ranking.py`. The critical invariant (per feature 085
pre-mortem) is the bool-before-int check order: Python's `bool <: int`
inheritance means `isinstance(True, int)` returns `True`, so a naive
`isinstance(raw, (int, float))` check first would silently coerce
`True` → `1.0` / `False` → `0.0` instead of returning `default`.
"""
from __future__ import annotations

import pytest

from semantic_memory.config_utils import resolve_float_config


def test_resolve_returns_default_for_True():
    """Critical: True must return `default`, NOT 1.0 (bool is int subclass)."""
    warned: set = set()
    assert resolve_float_config(
        {"k": True}, "k", 0.05, prefix="[x]", warned=warned
    ) == 0.05
    # One-shot warning recorded on malformed value.
    assert ("[x]", "k") in warned


def test_resolve_returns_default_for_False():
    """Critical: False must return `default`, NOT 0.0 (bool is int subclass)."""
    warned: set = set()
    assert resolve_float_config(
        {"k": False}, "k", 0.05, prefix="[x]", warned=warned
    ) == 0.05
    assert ("[x]", "k") in warned


def test_resolve_int_becomes_float():
    warned: set = set()
    result = resolve_float_config(
        {"k": 5}, "k", 0.05, prefix="[x]", warned=warned
    )
    assert result == 5.0
    assert isinstance(result, float)
    assert warned == set()


def test_resolve_string_parses():
    warned: set = set()
    result = resolve_float_config(
        {"k": "0.25"}, "k", 0.05, prefix="[x]", warned=warned
    )
    assert result == 0.25
    assert isinstance(result, float)
    assert warned == set()


def test_resolve_string_invalid_returns_default():
    warned: set = set()
    result = resolve_float_config(
        {"k": "bad"}, "k", 0.05, prefix="[x]", warned=warned
    )
    assert result == 0.05
    assert ("[x]", "k") in warned


def test_resolve_clamp_bounds_applied():
    """Values outside clamp range are clipped silently (no warning)."""
    warned: set = set()
    # Over the upper bound
    assert resolve_float_config(
        {"k": 2.0}, "k", 0.05, prefix="[x]", warned=warned, clamp=(0.0, 1.0)
    ) == 1.0
    # Under the lower bound
    assert resolve_float_config(
        {"k": -0.5}, "k", 0.05, prefix="[x]", warned=warned, clamp=(0.0, 1.0)
    ) == 0.0
    # Clamping is silent -- operator tuning, not a config error.
    assert warned == set()


def test_resolve_warn_once_per_key_prefix(capsys):
    """Repeated calls for the same (prefix, key) emit only one warning."""
    warned: set = set()
    resolve_float_config({"k": "garbage"}, "k", 0.05, prefix="[x]", warned=warned)
    resolve_float_config({"k": "garbage"}, "k", 0.05, prefix="[x]", warned=warned)
    resolve_float_config({"k": "garbage"}, "k", 0.05, prefix="[x]", warned=warned)
    assert len(warned) == 1
    captured = capsys.readouterr()
    warning_lines = [line for line in captured.err.splitlines() if "[x]" in line]
    assert len(warning_lines) == 1


def test_resolve_none_returns_default():
    """None value → default + warning (unknown type)."""
    warned: set = set()
    assert resolve_float_config(
        {"k": None}, "k", 0.05, prefix="[x]", warned=warned
    ) == 0.05
    assert ("[x]", "k") in warned


def test_resolve_missing_key_returns_default():
    """Missing key → default via dict.get fallback; NO warning (no malformed value)."""
    warned: set = set()
    assert resolve_float_config(
        {}, "k", 0.05, prefix="[x]", warned=warned
    ) == 0.05
    assert warned == set()
