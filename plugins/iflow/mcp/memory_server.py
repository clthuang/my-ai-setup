"""MCP memory server for storing learnings to long-term semantic memory.

Runs as a subprocess via stdio transport.  Never print to stdout
(corrupts JSON-RPC protocol) -- all logging goes to stderr.
"""
from __future__ import annotations

import json
import os
import sys
from contextlib import asynccontextmanager
from datetime import datetime, timezone

# Make semantic_memory importable from hooks/lib/.
sys.path.insert(0, os.path.join(os.path.dirname(__file__), "..", "hooks", "lib"))

# Smoke test: ensure the package is importable at startup.
import semantic_memory  # noqa: F401
from semantic_memory import VALID_CATEGORIES, content_hash
from semantic_memory.config import read_config
from semantic_memory.database import MemoryDatabase
from semantic_memory.embedding import EmbeddingProvider, create_provider
from semantic_memory.keywords import (
    KeywordGenerator,
    SkipKeywordGenerator,
    TieredKeywordGenerator,
)
from semantic_memory.ranking import RankingEngine
from semantic_memory.retrieval import RetrievalPipeline
from semantic_memory.writer import _embed_text_for_entry, _process_pending_embeddings

from mcp.server.fastmcp import FastMCP

# ---------------------------------------------------------------------------
# Core processing function (testable without MCP)
# ---------------------------------------------------------------------------


def _process_store_memory(
    db: MemoryDatabase,
    provider: EmbeddingProvider | None,
    keyword_gen: KeywordGenerator | None,
    name: str,
    description: str,
    reasoning: str,
    category: str,
    references: list[str],
) -> str:
    """Store a learning in the semantic memory database.

    Returns a confirmation string on success or an error string on
    validation failure.  Never raises.
    """
    # -- Validate inputs --
    if not name or not name.strip():
        return "Error: name must be non-empty"
    if not description or not description.strip():
        return "Error: description must be non-empty"
    if not reasoning or not reasoning.strip():
        return "Error: reasoning must be non-empty"
    if category not in VALID_CATEGORIES:
        return (
            f"Error: invalid category '{category}'. "
            f"Must be one of: {', '.join(sorted(VALID_CATEGORIES))}"
        )

    # -- Compute content hash (id) --
    entry_id = content_hash(description)

    # -- Source is always 'session-capture' per spec D6 --
    source = "session-capture"

    # -- Generate keywords if keyword_gen available --
    keywords_json: str | None = None
    if keyword_gen is not None:
        try:
            kw_list = keyword_gen.generate(name, description, reasoning, category)
            if kw_list:
                keywords_json = json.dumps(kw_list)
        except Exception as exc:
            print(
                f"memory-server: keyword generation failed: {exc}",
                file=sys.stderr,
            )

    # -- Build entry dict --
    now = datetime.now(tz=timezone.utc).strftime("%Y-%m-%dT%H:%M:%SZ")
    entry = {
        "id": entry_id,
        "name": name,
        "description": description,
        "reasoning": reasoning,
        "category": category,
        "keywords": keywords_json,
        "source": source,
        "references": json.dumps(references),
        "created_at": now,
        "updated_at": now,
    }

    # -- Upsert into DB --
    db.upsert_entry(entry)

    # -- Generate embedding using shared helper (consistent with writer) --
    if provider is not None:
        stored = db.get_entry(entry_id)
        if stored:
            embed_text = _embed_text_for_entry(stored)
            try:
                vec = provider.embed(embed_text, task_type="document")
                db.update_embedding(entry_id, vec.tobytes())
            except Exception as exc:
                print(
                    f"memory-server: embedding failed: {exc}",
                    file=sys.stderr,
                )

    # -- Process pending embeddings batch --
    if provider is not None:
        try:
            _process_pending_embeddings(db, provider)
        except Exception as exc:
            print(
                f"memory-server: pending embedding scan failed: {exc}",
                file=sys.stderr,
            )

    return f"Stored: {name} (id: {entry_id})"


# ---------------------------------------------------------------------------
# Search processing function (testable without MCP)
# ---------------------------------------------------------------------------


def _process_search_memory(
    db: MemoryDatabase,
    provider: EmbeddingProvider | None,
    config: dict,
    query: str,
    limit: int = 10,
) -> str:
    """Search the semantic memory database for relevant entries.

    Returns formatted results or an error string. Never raises.
    """
    if not query or not query.strip():
        return "Error: query must be non-empty"

    pipeline = RetrievalPipeline(db, provider, config)
    result = pipeline.retrieve(query.strip())

    all_entries = db.get_all_entries()
    entries_by_id = {e["id"]: e for e in all_entries}

    engine = RankingEngine(config)
    selected = engine.rank(result, entries_by_id, limit)

    if not selected:
        return "No matching memories found."

    cat_prefix_map = {
        "anti-patterns": "Anti-Pattern",
        "patterns": "Pattern",
        "heuristics": "Heuristic",
    }

    lines: list[str] = [f"Found {len(selected)} relevant memories:\n"]
    for entry in selected:
        prefix = cat_prefix_map.get(entry["category"], entry["category"])
        lines.append(f"### {prefix}: {entry['name']}")
        lines.append(entry["description"])
        if entry.get("reasoning"):
            lines.append(f"- Why: {entry['reasoning']}")
        lines.append(f"- Confidence: {entry.get('confidence', 'medium')}")
        lines.append("")

    return "\n".join(lines)


# ---------------------------------------------------------------------------
# Module-level globals (set during lifespan)
# ---------------------------------------------------------------------------

_db: MemoryDatabase | None = None
_provider: EmbeddingProvider | None = None
_keyword_gen: KeywordGenerator | None = None
_config: dict = {}

# ---------------------------------------------------------------------------
# Lifespan handler
# ---------------------------------------------------------------------------


@asynccontextmanager
async def lifespan(server):
    """Manage DB connection and providers lifecycle."""
    global _db, _provider, _keyword_gen, _config

    global_store = os.path.expanduser("~/.claude/iflow/memory")
    os.makedirs(global_store, exist_ok=True)

    _db = MemoryDatabase(os.path.join(global_store, "memory.db"))

    # Read config from the project root (cwd at server start).
    project_root = os.getcwd()
    config = read_config(project_root)
    _config = config

    _provider = create_provider(config)
    if _provider is not None:
        print(
            f"memory-server: embedding provider={_provider.provider_name} "
            f"model={_provider.model_name}",
            file=sys.stderr,
        )
    else:
        print("memory-server: no embedding provider available", file=sys.stderr)

    # Keyword generator: TieredKeywordGenerator if configured, else Skip.
    try:
        _keyword_gen = TieredKeywordGenerator(config)
    except Exception:
        _keyword_gen = SkipKeywordGenerator()

    try:
        yield {}
    finally:
        if _db is not None:
            _db.close()
            _db = None
        _provider = None
        _keyword_gen = None
        _config = {}


# ---------------------------------------------------------------------------
# MCP server
# ---------------------------------------------------------------------------

mcp = FastMCP("memory-server", lifespan=lifespan)


@mcp.tool()
async def store_memory(
    name: str,
    description: str,
    reasoning: str,
    category: str,
    references: list[str] | None = None,
) -> str:
    """Save a learning to long-term memory.

    Parameters
    ----------
    name:
        Short title for the learning (e.g. 'Always validate hook inputs').
    description:
        Detailed description of what was learned.
    reasoning:
        Why this learning matters or how it was discovered.
    category:
        One of: anti-patterns, patterns, heuristics.
    references:
        Optional list of file paths or URLs related to this learning.

    Returns confirmation message or error.
    """
    if _db is None:
        return "Error: database not initialized (server not started)"

    return _process_store_memory(
        db=_db,
        provider=_provider,
        keyword_gen=_keyword_gen,
        name=name,
        description=description,
        reasoning=reasoning,
        category=category,
        references=references if references is not None else [],
    )


@mcp.tool()
async def search_memory(
    query: str,
    limit: int = 10,
) -> str:
    """Search long-term memory for relevant learnings.

    Use this when you need to recall past learnings, patterns, or
    anti-patterns relevant to the current task.  Especially useful
    when the session context has shifted from the initial topic.

    Parameters
    ----------
    query:
        What to search for (e.g. 'hook development patterns',
        'git workflow mistakes', 'testing best practices').
    limit:
        Maximum number of results to return (default: 10).

    Returns matching memories ranked by relevance.
    """
    if _db is None:
        return "Error: database not initialized (server not started)"

    return _process_search_memory(
        db=_db,
        provider=_provider,
        config=_config,
        query=query,
        limit=limit,
    )


# ---------------------------------------------------------------------------
# Entry point
# ---------------------------------------------------------------------------

if __name__ == "__main__":
    mcp.run(transport="stdio")
