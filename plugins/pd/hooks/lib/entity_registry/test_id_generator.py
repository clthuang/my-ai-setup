"""Tests for entity_registry.id_generator module."""
from __future__ import annotations

import pytest

from entity_registry.database import EntityDatabase
from entity_registry.id_generator import (
    _scan_existing_max_seq,
    _slugify,
    generate_entity_id,
)


# ---------------------------------------------------------------------------
# Fixtures
# ---------------------------------------------------------------------------


@pytest.fixture
def db():
    """In-memory EntityDatabase."""
    database = EntityDatabase(":memory:")
    yield database
    database.close()


# ---------------------------------------------------------------------------
# _slugify tests
# ---------------------------------------------------------------------------


class TestSlugify:
    def test_basic_lowercase(self):
        assert _slugify("Hello World") == "hello-world"

    def test_special_characters_replaced(self):
        assert _slugify("My Feature! (v2)") == "my-feature-v2"

    def test_consecutive_hyphens_collapsed(self):
        assert _slugify("a---b") == "a-b"

    def test_leading_trailing_hyphens_stripped(self):
        assert _slugify("--hello--") == "hello"

    def test_max_length_truncation(self):
        long_name = "this-is-a-very-long-name-that-exceeds-the-max"
        result = _slugify(long_name, max_length=30)
        assert len(result) <= 30

    def test_truncation_on_hyphen_boundary(self):
        # "enterprise-reliability-platform" is 31 chars
        result = _slugify("enterprise reliability platform", max_length=30)
        # Should truncate to "enterprise-reliability" (not mid-word)
        assert "-" not in result or not result.endswith("-")
        assert len(result) <= 30

    def test_max_length_exact(self):
        name = "a" * 30
        assert _slugify(name, max_length=30) == "a" * 30

    def test_empty_string(self):
        assert _slugify("") == ""

    def test_numbers_preserved(self):
        assert _slugify("feature 052") == "feature-052"

    def test_unicode_stripped(self):
        result = _slugify("caf\u00e9 d\u00e9ploiement")
        # Non-ASCII chars become hyphens
        assert result == "caf-d-ploiement"


# ---------------------------------------------------------------------------
# _scan_existing_max_seq tests
# ---------------------------------------------------------------------------


class TestScanExistingMaxSeq:
    def test_no_existing_entities(self, db: EntityDatabase):
        assert _scan_existing_max_seq(db, "task") == 0

    def test_finds_max_from_existing(self, db: EntityDatabase):
        db.register_entity("feature", "051-old-feature", "Old Feature")
        db.register_entity("feature", "052-new-feature", "New Feature")
        assert _scan_existing_max_seq(db, "feature") == 52

    def test_ignores_non_matching_ids(self, db: EntityDatabase):
        db.register_entity("feature", "custom-no-seq", "Custom")
        assert _scan_existing_max_seq(db, "feature") == 0

    def test_scoped_to_entity_type(self, db: EntityDatabase):
        db.register_entity("feature", "052-some-feature", "Feature")
        db.register_entity("project", "001-some-project", "Project")
        assert _scan_existing_max_seq(db, "project") == 1
        assert _scan_existing_max_seq(db, "feature") == 52


# ---------------------------------------------------------------------------
# generate_entity_id tests
# ---------------------------------------------------------------------------


class TestGenerateEntityId:
    def test_first_id_for_new_type(self, db: EntityDatabase):
        """New type with no existing entities starts at 001."""
        result = generate_entity_id(db, "task", "My First Task")
        assert result == "001-my-first-task"

    def test_sequential_ids(self, db: EntityDatabase):
        """Multiple calls increment the sequence."""
        id1 = generate_entity_id(db, "task", "Task One")
        id2 = generate_entity_id(db, "task", "Task Two")
        id3 = generate_entity_id(db, "task", "Task Three")
        assert id1 == "001-task-one"
        assert id2 == "002-task-two"
        assert id3 == "003-task-three"

    def test_continues_from_existing(self, db: EntityDatabase):
        """Existing entities bootstrap the sequence counter."""
        db.register_entity("feature", "052-existing", "Existing Feature")
        result = generate_entity_id(db, "feature", "Structured Logging")
        assert result == "053-structured-logging"

    def test_per_type_counters(self, db: EntityDatabase):
        """Each entity type has its own independent counter."""
        id_task = generate_entity_id(db, "task", "A Task")
        id_init = generate_entity_id(db, "initiative", "An Initiative")
        assert id_task == "001-a-task"
        assert id_init == "001-an-initiative"

    def test_slug_max_30_chars(self, db: EntityDatabase):
        long_name = "A Very Long Entity Name That Definitely Exceeds Thirty Characters"
        result = generate_entity_id(db, "task", long_name)
        # Extract slug (everything after "NNN-")
        slug = result.split("-", 1)[1]
        assert len(slug) <= 30

    def test_slug_lowercase_hyphens(self, db: EntityDatabase):
        result = generate_entity_id(db, "initiative", "Enterprise Reliability")
        assert result == "001-enterprise-reliability"

    def test_metadata_persisted(self, db: EntityDatabase):
        """Counter is persisted in _metadata table."""
        generate_entity_id(db, "task", "First")
        raw = db.get_metadata("next_seq_task")
        assert raw == "1"
        generate_entity_id(db, "task", "Second")
        raw = db.get_metadata("next_seq_task")
        assert raw == "2"

    def test_bootstrap_from_metadata_if_seeded(self, db: EntityDatabase):
        """If _metadata already has next_seq, use it (e.g., seeded by migration)."""
        db.set_metadata("next_seq_objective", "5")
        result = generate_entity_id(db, "objective", "Quarterly Goal")
        assert result == "006-quarterly-goal"

    def test_empty_name_fallback(self, db: EntityDatabase):
        """Empty name produces 'unnamed' slug."""
        result = generate_entity_id(db, "task", "")
        assert result == "001-unnamed"

    def test_special_chars_in_name(self, db: EntityDatabase):
        result = generate_entity_id(db, "task", "Fix bug #123 (urgent!)")
        assert result == "001-fix-bug-123-urgent"
