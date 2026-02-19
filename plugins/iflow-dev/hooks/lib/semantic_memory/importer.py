"""Markdown importer for the semantic memory system.

Scans project-local and global knowledge bank markdown files, parses
entries using the same logic as memory.py, and upserts them into the
semantic memory database with source='import'.  Embeddings and keywords
are left NULL for deferred processing on the next write-path.
"""
from __future__ import annotations

import os
import re
from datetime import datetime, timezone
from typing import TYPE_CHECKING

from semantic_memory import content_hash

if TYPE_CHECKING:
    from semantic_memory.database import MemoryDatabase
    from semantic_memory.embedding import EmbeddingProvider
    from semantic_memory.keywords import KeywordGenerator


# Category filename -> category name mapping.
CATEGORIES = [
    ("anti-patterns.md", "anti-patterns"),
    ("patterns.md", "patterns"),
    ("heuristics.md", "heuristics"),
]


class MarkdownImporter:
    """Import knowledge bank markdown files into the semantic memory database.

    Parameters
    ----------
    db:
        The MemoryDatabase instance to upsert entries into.
    provider:
        Embedding provider (unused during import; embeddings are deferred).
    keyword_gen:
        Keyword generator (unused during import; keywords are deferred).
    """

    def __init__(
        self,
        db: MemoryDatabase,
        provider: EmbeddingProvider | None,
        keyword_gen: KeywordGenerator | None,
    ) -> None:
        self._db = db
        self._provider = provider
        self._keyword_gen = keyword_gen

    def import_all(self, project_root: str, global_store: str) -> int:
        """Import entries from local and global knowledge bank files.

        Scans ``{project_root}/docs/knowledge-bank/*.md`` (local) and
        ``{global_store}/*.md`` (global) for each known category file.

        Returns the total number of entries upserted.
        """
        now = datetime.now(tz=timezone.utc).strftime("%Y-%m-%dT%H:%M:%SZ")
        count = 0

        local_kb = os.path.join(project_root, "docs", "knowledge-bank")
        for filename, category in CATEGORIES:
            filepath = os.path.join(local_kb, filename)
            entries = self._parse_markdown_entries(filepath, category)
            for entry in entries:
                self._upsert_entry(entry, project_root, now)
                count += 1

        for filename, category in CATEGORIES:
            filepath = os.path.join(global_store, filename)
            entries = self._parse_markdown_entries(filepath, category)
            for entry in entries:
                self._upsert_entry(entry, project_root, now)
                count += 1

        return count

    def _upsert_entry(self, parsed: dict, project_root: str, now: str) -> None:
        """Convert a parsed entry dict into the DB format and upsert."""
        entry = {
            "id": parsed["content_hash"],
            "name": parsed["name"],
            "description": parsed["description"],
            "reasoning": None,
            "category": parsed["category"],
            "keywords": None,
            "source": "import",
            "source_project": project_root,
            "references": None,
            "observation_count": parsed["observation_count"],
            "confidence": parsed["confidence"],
            "embedding": None,
            "created_at": now,
            "updated_at": now,
        }
        self._db.upsert_entry(entry)

    def _parse_markdown_entries(
        self, filepath: str, category: str
    ) -> list[dict]:
        """Parse a knowledge bank markdown file into entry dicts.

        Uses the same logic as ``memory.py:parse_entries()`` to ensure
        consistent parsing across the legacy and semantic memory paths.
        """
        if not os.path.isfile(filepath):
            return []

        with open(filepath, "r") as f:
            raw = f.read()

        # Strip HTML comments
        raw = re.sub(r"<!--[\s\S]*?-->", "", raw)

        # Split on ### headings
        chunks = re.split(r"(?m)^### ", raw)
        entries: list[dict] = []

        for chunk in chunks:
            if not chunk.strip():
                continue

            first_line = chunk.split("\n", 1)[0]
            if first_line.startswith("## ") or first_line.startswith("# "):
                continue

            lines = chunk.split("\n")
            header_line = lines[0].strip()

            # Strip type prefix
            name = header_line
            for prefix in ("Anti-Pattern: ", "Pattern: "):
                if name.startswith(prefix):
                    name = name[len(prefix):]
                    break

            # Partition into description and metadata
            desc_lines: list[str] = []
            meta_lines: list[str] = []
            in_metadata = False
            for line in lines[1:]:
                if line.startswith("- ") and not in_metadata:
                    in_metadata = True
                if in_metadata:
                    meta_lines.append(line)
                else:
                    desc_lines.append(line)

            description = "\n".join(desc_lines).strip()

            # Extract metadata with defaults
            obs_count = 1
            confidence = "medium"
            last_observed = None

            for ml in meta_lines:
                ml_lower = ml.lower().strip()
                if ml_lower.startswith("- observation count:"):
                    try:
                        obs_count = int(ml.split(":", 1)[1].strip())
                    except (ValueError, IndexError):
                        pass
                elif ml_lower.startswith("- confidence:"):
                    val = ml.split(":", 1)[1].strip().lower()
                    if val in {"high", "medium", "low"}:
                        confidence = val
                elif ml_lower.startswith("- last observed:"):
                    last_observed = ml.split(":", 1)[1].strip()

            entries.append({
                "name": name,
                "category": category,
                "description": description,
                "observation_count": obs_count,
                "confidence": confidence,
                "last_observed": last_observed,
                "content_hash": content_hash(description),
            })

        return entries
