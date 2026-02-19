"""Tests for semantic_memory.importer module."""
from __future__ import annotations

import textwrap

import pytest

from semantic_memory import content_hash
from semantic_memory.database import MemoryDatabase
from semantic_memory.importer import MarkdownImporter


# ---------------------------------------------------------------------------
# Fixtures
# ---------------------------------------------------------------------------


@pytest.fixture
def db():
    """Provide an in-memory MemoryDatabase, closed after test."""
    database = MemoryDatabase(":memory:")
    yield database
    database.close()


@pytest.fixture
def importer(db):
    """MarkdownImporter with in-memory DB."""
    return MarkdownImporter(db=db)


# ---------------------------------------------------------------------------
# Sample markdown content
# ---------------------------------------------------------------------------

ANTI_PATTERNS_MD = textwrap.dedent("""\
    # Anti-Patterns

    ## Observed Anti-Patterns

    ### Anti-Pattern: Premature Optimisation
    Optimising code before profiling leads to complex,
    hard-to-maintain solutions.
    - Observation Count: 5
    - Confidence: high
    - Last Observed: 2026-01-15

    ### Anti-Pattern: God Object
    A single class that knows too much or does too much.
    - Observation Count: 3
    - Confidence: medium
    - Last Observed: 2026-02-01

    ### Anti-Pattern: Copy-Paste Programming
    Duplicating code instead of abstracting shared logic.
    - Observation Count: 2
    - Confidence: low
    - Last Observed: 2026-01-20
""")

PATTERNS_MD = textwrap.dedent("""\
    # Patterns

    ## Observed Patterns

    ### Pattern: Early Return
    Return early from functions to reduce nesting.
    - Observation Count: 4
    - Confidence: high
    - Last Observed: 2026-01-10
""")

HEURISTICS_MD = textwrap.dedent("""\
    # Heuristics

    ## Observed Heuristics

    ### Keep Functions Short
    Functions should do one thing and do it well.
    - Observation Count: 6
    - Confidence: high
    - Last Observed: 2026-02-10
""")

HTML_COMMENT_MD = textwrap.dedent("""\
    # Anti-Patterns

    <!-- This is a template comment
    ### Anti-Pattern: Template Entry
    Do not parse this.
    - Observation Count: 1
    - Confidence: low
    -->

    ### Anti-Pattern: Real Entry
    This should be parsed.
    - Observation Count: 2
    - Confidence: medium
    - Last Observed: 2026-01-05
""")


# ---------------------------------------------------------------------------
# Parsing tests
# ---------------------------------------------------------------------------


class TestParseMarkdownEntries:
    def test_parse_anti_patterns_returns_three_entries(self, importer, tmp_path):
        """Parsing anti-patterns.md with 3 entries returns 3 correct entries."""
        filepath = tmp_path / "anti-patterns.md"
        filepath.write_text(ANTI_PATTERNS_MD)

        entries = importer._parse_markdown_entries(str(filepath), "anti-patterns")
        assert len(entries) == 3

    def test_entry_names_stripped_of_prefix(self, importer, tmp_path):
        """Anti-Pattern: and Pattern: prefixes are stripped from names."""
        filepath = tmp_path / "anti-patterns.md"
        filepath.write_text(ANTI_PATTERNS_MD)

        entries = importer._parse_markdown_entries(str(filepath), "anti-patterns")
        names = [e["name"] for e in entries]
        assert "Premature Optimisation" in names
        assert "God Object" in names
        assert "Copy-Paste Programming" in names

    def test_pattern_prefix_stripped(self, importer, tmp_path):
        """Pattern: prefix is stripped from pattern names."""
        filepath = tmp_path / "patterns.md"
        filepath.write_text(PATTERNS_MD)

        entries = importer._parse_markdown_entries(str(filepath), "patterns")
        assert entries[0]["name"] == "Early Return"

    def test_heuristic_prefix_not_stripped(self, importer, tmp_path):
        """Heuristic names use plain names -- no 'Heuristic: ' prefix to strip."""
        filepath = tmp_path / "heuristics.md"
        filepath.write_text(HEURISTICS_MD)

        entries = importer._parse_markdown_entries(str(filepath), "heuristics")
        assert entries[0]["name"] == "Keep Functions Short"

    def test_html_comments_stripped(self, importer, tmp_path):
        """HTML comments are stripped before parsing, so template entries are excluded."""
        filepath = tmp_path / "anti-patterns.md"
        filepath.write_text(HTML_COMMENT_MD)

        entries = importer._parse_markdown_entries(str(filepath), "anti-patterns")
        assert len(entries) == 1
        assert entries[0]["name"] == "Real Entry"

    def test_entry_metadata_extracted(self, importer, tmp_path):
        """Observation count and confidence are extracted."""
        filepath = tmp_path / "anti-patterns.md"
        filepath.write_text(ANTI_PATTERNS_MD)

        entries = importer._parse_markdown_entries(str(filepath), "anti-patterns")
        first = entries[0]  # Premature Optimisation
        assert first["observation_count"] == 5
        assert first["confidence"] == "high"

    def test_entry_description_extracted(self, importer, tmp_path):
        """Description text is extracted (body before metadata lines)."""
        filepath = tmp_path / "anti-patterns.md"
        filepath.write_text(ANTI_PATTERNS_MD)

        entries = importer._parse_markdown_entries(str(filepath), "anti-patterns")
        first = entries[0]
        assert "Optimising code before profiling" in first["description"]

    def test_content_hash_matches_description(self, importer, tmp_path):
        """content_hash is computed from the description text."""
        filepath = tmp_path / "anti-patterns.md"
        filepath.write_text(ANTI_PATTERNS_MD)

        entries = importer._parse_markdown_entries(str(filepath), "anti-patterns")
        for entry in entries:
            assert entry["content_hash"] == content_hash(entry["description"])

    def test_missing_file_returns_empty(self, importer):
        """Non-existent file returns empty list."""
        entries = importer._parse_markdown_entries("/nonexistent/file.md", "patterns")
        assert entries == []

    def test_category_set_correctly(self, importer, tmp_path):
        """Category is set from the argument, not inferred."""
        filepath = tmp_path / "anti-patterns.md"
        filepath.write_text(ANTI_PATTERNS_MD)

        entries = importer._parse_markdown_entries(str(filepath), "anti-patterns")
        assert all(e["category"] == "anti-patterns" for e in entries)


# ---------------------------------------------------------------------------
# Import into DB tests
# ---------------------------------------------------------------------------


class TestImportIntoDB:
    def test_import_three_entries(self, db, importer, tmp_path):
        """Importing 3 entries results in db.count_entries() == 3."""
        kb_dir = tmp_path / "docs" / "knowledge-bank"
        kb_dir.mkdir(parents=True)
        (kb_dir / "anti-patterns.md").write_text(ANTI_PATTERNS_MD)
        (kb_dir / "patterns.md").write_text("")
        (kb_dir / "heuristics.md").write_text("")

        count = importer.import_all(
            project_root=str(tmp_path),
            global_store=str(tmp_path / "global"),
        )
        assert count == 3
        assert db.count_entries() == 3

    def test_reimport_is_idempotent(self, db, importer, tmp_path):
        """Re-importing the same files does not create duplicates."""
        kb_dir = tmp_path / "docs" / "knowledge-bank"
        kb_dir.mkdir(parents=True)
        (kb_dir / "anti-patterns.md").write_text(ANTI_PATTERNS_MD)
        (kb_dir / "patterns.md").write_text("")
        (kb_dir / "heuristics.md").write_text("")

        importer.import_all(str(tmp_path), str(tmp_path / "global"))
        importer.import_all(str(tmp_path), str(tmp_path / "global"))

        # Still 3 entries (upsert dedup by content hash)
        assert db.count_entries() == 3

    def test_embeddings_and_keywords_are_null(self, db, importer, tmp_path):
        """After import, embeddings and keywords are NULL (deferred)."""
        kb_dir = tmp_path / "docs" / "knowledge-bank"
        kb_dir.mkdir(parents=True)
        (kb_dir / "anti-patterns.md").write_text(ANTI_PATTERNS_MD)
        (kb_dir / "patterns.md").write_text("")
        (kb_dir / "heuristics.md").write_text("")

        importer.import_all(str(tmp_path), str(tmp_path / "global"))

        for entry in db.get_all_entries():
            assert entry["embedding"] is None
            assert entry["keywords"] is None

    def test_import_all_scans_local_and_global(self, db, importer, tmp_path):
        """import_all scans both local knowledge-bank and global store."""
        # Local: 3 anti-patterns
        kb_dir = tmp_path / "docs" / "knowledge-bank"
        kb_dir.mkdir(parents=True)
        (kb_dir / "anti-patterns.md").write_text(ANTI_PATTERNS_MD)
        (kb_dir / "patterns.md").write_text("")
        (kb_dir / "heuristics.md").write_text("")

        # Global: 1 pattern
        global_dir = tmp_path / "global"
        global_dir.mkdir(parents=True)
        (global_dir / "anti-patterns.md").write_text("")
        (global_dir / "patterns.md").write_text(PATTERNS_MD)
        (global_dir / "heuristics.md").write_text("")

        count = importer.import_all(str(tmp_path), str(global_dir))
        assert count == 4  # 3 local + 1 global
        assert db.count_entries() == 4

    def test_missing_dirs_handled_gracefully(self, db, importer, tmp_path):
        """Missing local or global directories do not cause errors."""
        count = importer.import_all(
            str(tmp_path / "nonexistent"),
            str(tmp_path / "also-nonexistent"),
        )
        assert count == 0
        assert db.count_entries() == 0

    def test_source_is_import(self, db, importer, tmp_path):
        """Entries imported have source='import'."""
        kb_dir = tmp_path / "docs" / "knowledge-bank"
        kb_dir.mkdir(parents=True)
        (kb_dir / "anti-patterns.md").write_text(ANTI_PATTERNS_MD)
        (kb_dir / "patterns.md").write_text("")
        (kb_dir / "heuristics.md").write_text("")

        importer.import_all(str(tmp_path), str(tmp_path / "global"))

        for entry in db.get_all_entries():
            assert entry["source"] == "import"

    def test_source_project_set(self, db, importer, tmp_path):
        """source_project is set to the project_root argument."""
        kb_dir = tmp_path / "docs" / "knowledge-bank"
        kb_dir.mkdir(parents=True)
        (kb_dir / "anti-patterns.md").write_text(ANTI_PATTERNS_MD)
        (kb_dir / "patterns.md").write_text("")
        (kb_dir / "heuristics.md").write_text("")

        importer.import_all(str(tmp_path), str(tmp_path / "global"))

        for entry in db.get_all_entries():
            assert entry["source_project"] == str(tmp_path)

    def test_import_returns_total_count(self, db, importer, tmp_path):
        """import_all returns the total count of entries imported."""
        kb_dir = tmp_path / "docs" / "knowledge-bank"
        kb_dir.mkdir(parents=True)
        (kb_dir / "anti-patterns.md").write_text(ANTI_PATTERNS_MD)
        (kb_dir / "patterns.md").write_text(PATTERNS_MD)
        (kb_dir / "heuristics.md").write_text(HEURISTICS_MD)

        count = importer.import_all(str(tmp_path), str(tmp_path / "global"))
        assert count == 5  # 3 + 1 + 1
