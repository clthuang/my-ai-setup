"""Shared float-config resolution helper for semantic memory + MCP server.

Extracted from the two near-duplicate implementations previously sitting in
`mcp/memory_server.py` and `semantic_memory/ranking.py`. Feature 085 (FR-4)
consolidates both into a single canonical API.

Import boundary: stdlib ONLY. This module MUST NOT import from any
other `semantic_memory.*` module (ranking, database, retrieval_types,
config.py) or any `plugins/pd/mcp/*` module. The circular-import smoke
test in `validate.sh` enforces this: a regression that adds such an
import will fail the CI step.

Critical invariant (pre-mortem R-1): `isinstance(raw, bool)` MUST
precede `isinstance(raw, (int, float))`. Python's `bool` inherits from
`int`, so naive ordering silently coerces `True` → `1.0` / `False` →
`0.0` instead of returning the supplied `default`.
"""
from __future__ import annotations

import sys


__all__ = ["resolve_float_config"]


def _warn_once(
    key: str,
    raw,
    default: float,
    *,
    prefix: str,
    warned: set,
) -> float:
    """Emit a one-shot stderr warning for a malformed config value.

    The dedup key is `(prefix, key)` so two different consumers sharing
    the helper (ranker, memory-server) still warn once each for their
    own context even when the same config key is reused. Callers pass
    in a shared set that persists across calls for the life of the
    process.
    """
    token = (prefix, key)
    if token not in warned:
        warned.add(token)
        sys.stderr.write(
            f"{prefix} config field {key!r} value {raw!r} "
            f"is not a float; using default {default}\n"
        )
    return default


def resolve_float_config(
    config: dict,
    key: str,
    default: float,
    *,
    prefix: str,
    warned: set,
    clamp: tuple[float, float] | None = None,
) -> float:
    """Resolve a float from `config[key]`, rejecting bools and optionally clamping.

    Type handling (order matters):
      1. Missing key → return `default` (no warning).
      2. `bool` (including subclasses like `numpy.bool_`) → `default` +
         one-shot warning. MUST precede the int/float branch because
         Python `bool` inherits from `int` and would otherwise silently
         coerce.
      3. `int` / `float` → `float(raw)`, then clamp if requested.
      4. `str` → `float(raw)` with `ValueError` → `default` + warning.
      5. Anything else (None, list, dict, custom) → `default` + warning.

    Clamp semantics: when `clamp=(lo, hi)` is supplied, the parsed value
    is silently clipped to `[lo, hi]`. Clamping is intentional operator
    tuning (e.g. 2.5 → 1.0) and does NOT emit a warning.

    `warned` is mutated in place — callers share one set per consumer
    module for cross-call dedup.
    """
    # `dict.get(key, default)` returns `default` sentinel when key is
    # absent, so we can't rely on it alone to distinguish "missing key"
    # from "key present with value == default". Use explicit containment.
    if key not in config:
        return default
    raw = config[key]

    # Order-critical: bool BEFORE int/float. See module docstring.
    if isinstance(raw, bool):
        return _warn_once(key, raw, default, prefix=prefix, warned=warned)
    if isinstance(raw, (int, float)):
        value = float(raw)
    elif isinstance(raw, str):
        try:
            value = float(raw)
        except ValueError:
            return _warn_once(key, raw, default, prefix=prefix, warned=warned)
    else:
        return _warn_once(key, raw, default, prefix=prefix, warned=warned)

    if clamp is not None:
        lo, hi = clamp
        if value < lo:
            value = lo
        elif value > hi:
            value = hi
    return value
