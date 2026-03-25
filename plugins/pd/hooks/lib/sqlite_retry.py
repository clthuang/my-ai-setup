"""Shared retry module for SQLite concurrency defense.

Provides `with_retry` decorator and `is_transient` predicate for use
across MCP servers (entity, memory, workflow state).

Extracted from workflow_state_server.py `_with_retry` / `_is_transient`.
"""

import functools
import random
import sqlite3
import sys
import time


def is_transient(exc: Exception) -> bool:
    """Classify whether a SQLite error is transient (retryable).

    Only matches "locked" — NOT "sql logic error" (SQLITE_ERROR is generic,
    covers schema/FTS/syntax errors). BEGIN IMMEDIATE prevents the
    stale-transaction root cause.
    See docs/rca/20260324-workflow-sql-error.md:69-75.
    """
    return isinstance(exc, sqlite3.OperationalError) and "locked" in str(exc).lower()


def with_retry(
    server_name: str,
    max_attempts: int = 3,
    backoff: tuple[float, ...] = (0.1, 0.5, 2.0),
):
    """Decorator factory for retrying SQLite operations on transient errors.

    Args:
        server_name: Prefix for stderr log messages (e.g., "entity-server").
        max_attempts: Total number of attempts before re-raising.
        backoff: Tuple of base delays in seconds. When attempts exceed the
            tuple length, the last value is reused. Jitter of up to 50ms
            is added to each delay.
    """

    def decorator(func):
        @functools.wraps(func)
        def wrapper(*args, **kwargs):
            last_exc = None
            for attempt in range(max_attempts):
                try:
                    return func(*args, **kwargs)
                except sqlite3.OperationalError as exc:
                    if not is_transient(exc):
                        raise
                    last_exc = exc
                    if attempt < max_attempts - 1:
                        delay = backoff[min(attempt, len(backoff) - 1)]
                        jitter = random.uniform(0, 0.05)
                        print(
                            f"{server_name}: retry {attempt + 1}/{max_attempts} "
                            f"after {exc} (sleeping {delay:.1f}s)",
                            file=sys.stderr,
                        )
                        time.sleep(delay + jitter)
            raise last_exc  # Exhausted — propagates to caller

        return wrapper

    return decorator
