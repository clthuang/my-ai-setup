"""Backfill CLI: import markdown entries from all registered projects and generate embeddings."""
from __future__ import annotations

import argparse
import os
import sys

_lib_dir = os.path.join(os.path.dirname(os.path.abspath(__file__)), "..")
if _lib_dir not in sys.path:
    sys.path.insert(0, _lib_dir)

from semantic_memory.config import read_config
from semantic_memory.database import MemoryDatabase
from semantic_memory.embedding import create_provider
from semantic_memory.importer import MarkdownImporter
from semantic_memory.writer import _check_provider_migration, _process_pending_embeddings


def _read_registry(registry_path: str) -> list[str]:
    """Read project paths from registry file. Skips comments and missing dirs."""
    if not os.path.isfile(registry_path):
        return []
    paths: list[str] = []
    with open(registry_path) as f:
        for line in f:
            line = line.strip()
            if line and not line.startswith("#") and os.path.isdir(line):
                paths.append(line)
    return paths


def backfill(project_root: str, global_store: str, registry_path: str | None = None) -> dict:
    """Run the full backfill pipeline. Returns stats dict."""
    db_path = os.path.join(global_store, "memory.db")
    os.makedirs(os.path.dirname(db_path), exist_ok=True)
    db = MemoryDatabase(db_path)

    try:
        # 1. Determine which projects to scan
        project_roots: list[str] = []
        if registry_path:
            project_roots = _read_registry(registry_path)
        if project_root not in project_roots:
            project_roots.append(project_root)

        # 2. Count before
        before = db.count_entries()

        # 3. Import from all registered projects
        importer = MarkdownImporter(db)
        total_imported = 0
        for proj in project_roots:
            count = importer.import_all(proj, global_store)
            if count > 0:
                print(f"  Imported from {proj}: {count} entries")
            total_imported += count

        after = db.count_entries()
        new_entries = after - before

        # 4. Create provider and generate embeddings
        config = read_config(project_root)
        provider = create_provider(config)

        embedded = 0
        if provider:
            _check_provider_migration(db, config, provider)

            # Process ALL pending in batches of 50
            while True:
                pending = db.count_entries_without_embedding()
                if pending == 0:
                    break
                count = _process_pending_embeddings(db, provider)
                embedded += count
                print(f"  Embedded {count} entries ({pending - count} remaining)")
                if count == 0:
                    break  # All failed, stop
        else:
            print("  No embedding provider available — skipping embedding generation")

        # 5. Final stats
        total = db.count_entries()
        with_embedding = total - db.count_entries_without_embedding()

        return {
            "projects_scanned": len(project_roots),
            "imported": total_imported,
            "new_entries": new_entries,
            "embedded": embedded,
            "total": total,
            "with_embedding": with_embedding,
            "provider": provider.provider_name if provider else None,
            "model": provider.model_name if provider else None,
        }
    finally:
        db.close()


def main() -> None:
    """CLI entry point."""
    parser = argparse.ArgumentParser(description="Backfill semantic memory from knowledge bank markdown files")
    parser.add_argument(
        "--project-root",
        default=os.getcwd(),
        help="Current project root (for config reading)",
    )
    parser.add_argument(
        "--global-store",
        required=True,
        help="Path to ~/.claude/iflow/memory",
    )
    parser.add_argument(
        "--registry",
        default=None,
        help="Path to projects.txt (optional; if omitted, only imports current project)",
    )
    args = parser.parse_args()

    stats = backfill(
        project_root=args.project_root,
        global_store=args.global_store,
        registry_path=args.registry,
    )

    print()
    print(f"  Projects scanned: {stats['projects_scanned']}")
    print(f"  Entries imported:  {stats['imported']} ({stats['new_entries']} new)")
    print(f"  Embeddings added:  {stats['embedded']}")
    print(f"  Total entries:     {stats['total']} ({stats['with_embedding']} with embeddings)")
    if stats["provider"]:
        print(f"  Provider:          {stats['provider']} ({stats['model']})")


if __name__ == "__main__":
    main()
