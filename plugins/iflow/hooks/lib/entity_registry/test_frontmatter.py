"""Tests for entity_registry.frontmatter module."""
from __future__ import annotations

import logging
import os
import tempfile

import pytest

from entity_registry.frontmatter import (
    ALLOWED_ARTIFACT_TYPES,
    ALLOWED_FIELDS,
    FIELD_ORDER,
    OPTIONAL_FIELDS,
    REQUIRED_FIELDS,
    _UUID_V4_RE,
    _parse_block,
    _serialize_header,
    build_header,
    read_frontmatter,
    validate_header,
)

# Valid UUID v4 for reuse across tests
VALID_UUID = "a1b2c3d4-e5f6-4a7b-8c9d-0e1f2a3b4c5d"
VALID_TYPE_ID = "feature:002-markdown-entity-file-header-sc"
VALID_ARTIFACT_TYPE = "spec"
VALID_CREATED_AT = "2026-03-01T12:00:00+00:00"


# ---------------------------------------------------------------------------
# Phase 1: Core Infrastructure
# ---------------------------------------------------------------------------


class TestParseBlock:
    """Tests for _parse_block (Task 1.2.1)."""

    def test_empty_lines_returns_empty_dict(self):
        result = _parse_block([])
        assert result == {}

    def test_single_key_value_line(self):
        result = _parse_block(["entity_uuid: abc-123"])
        assert result == {"entity_uuid": "abc-123"}

    def test_colon_in_value(self):
        """Values may contain ': ' sequences (e.g., entity_type_id: feature:002-foo)."""
        result = _parse_block(["entity_type_id: feature:002-foo"])
        assert result == {"entity_type_id": "feature:002-foo"}

    def test_no_separator_ignored(self):
        """Lines without ': ' separator are silently ignored."""
        result = _parse_block(["no-separator-here"])
        assert result == {}

    def test_invalid_key_chars_ignored(self):
        """Keys with uppercase, digits, or hyphens are ignored."""
        result = _parse_block([
            "Invalid: uppercase",
            "key-with-hyphens: bad",
            "key123: digits",
        ])
        assert result == {}

    def test_blank_and_comment_lines_ignored(self):
        result = _parse_block(["", "# comment line", "   "])
        assert result == {}

    def test_multiple_valid_lines(self):
        result = _parse_block([
            "entity_uuid: abc-123",
            "artifact_type: spec",
            "created_at: 2026-01-01",
        ])
        assert result == {
            "entity_uuid": "abc-123",
            "artifact_type": "spec",
            "created_at": "2026-01-01",
        }


class TestSerializeHeader:
    """Tests for _serialize_header (Task 1.3.1)."""

    def test_required_fields_ordered(self):
        """Required fields appear in FIELD_ORDER with --- delimiters."""
        header = {
            "entity_uuid": VALID_UUID,
            "entity_type_id": VALID_TYPE_ID,
            "artifact_type": VALID_ARTIFACT_TYPE,
            "created_at": VALID_CREATED_AT,
        }
        result = _serialize_header(header)
        lines = result.split("\n")
        # First line is ---, last non-empty line before trailing \n is ---
        assert lines[0] == "---"
        assert lines[1].startswith("entity_uuid: ")
        assert lines[2].startswith("entity_type_id: ")
        assert lines[3].startswith("artifact_type: ")
        assert lines[4].startswith("created_at: ")
        assert lines[5] == "---"

    def test_optional_fields_after_required(self):
        """Optional fields follow required, in FIELD_ORDER order."""
        header = {
            "entity_uuid": VALID_UUID,
            "entity_type_id": VALID_TYPE_ID,
            "artifact_type": VALID_ARTIFACT_TYPE,
            "created_at": VALID_CREATED_AT,
            "feature_id": "002",
            "phase": "specify",
        }
        result = _serialize_header(header)
        lines = result.split("\n")
        # feature_id at index 5, phase at index 6 (after 4 required fields)
        assert lines[5].startswith("feature_id: ")
        assert lines[6].startswith("phase: ")

    def test_unknown_field_appended_after_field_order(self):
        """Unknown fields (not in FIELD_ORDER) appear at the end."""
        header = {
            "entity_uuid": VALID_UUID,
            "entity_type_id": VALID_TYPE_ID,
            "artifact_type": VALID_ARTIFACT_TYPE,
            "created_at": VALID_CREATED_AT,
            "custom_field": "custom_value",
        }
        result = _serialize_header(header)
        lines = result.split("\n")
        # custom_field should be after the 4 known fields, before closing ---
        assert "custom_field: custom_value" in lines

    def test_round_trip_non_empty(self):
        """Serialize then parse back equals original dict."""
        header = {
            "entity_uuid": VALID_UUID,
            "entity_type_id": VALID_TYPE_ID,
            "artifact_type": VALID_ARTIFACT_TYPE,
            "created_at": VALID_CREATED_AT,
        }
        serialized = _serialize_header(header)
        # Extract lines between --- delimiters
        content_lines = serialized.split("\n")
        inner_lines = content_lines[1:-2]  # skip first --- and last ---\n
        parsed = _parse_block(inner_lines)
        assert parsed == header

    def test_round_trip_single_field(self):
        """Single-field dict round-trips correctly."""
        header = {"entity_uuid": VALID_UUID}
        serialized = _serialize_header(header)
        content_lines = serialized.split("\n")
        inner_lines = content_lines[1:-2]
        parsed = _parse_block(inner_lines)
        assert parsed == header

    def test_empty_dict_serializes_to_delimiters_only(self):
        """Empty dict {} serializes as '---\\n---\\n', parses back to {}."""
        header = {}
        serialized = _serialize_header(header)
        assert serialized == "---\n---\n"
        content_lines = serialized.split("\n")
        inner_lines = content_lines[1:-2]
        parsed = _parse_block(inner_lines)
        assert parsed == {}


# ---------------------------------------------------------------------------
# Phase 2: Validation & Build Functions
# ---------------------------------------------------------------------------


def _valid_header() -> dict:
    """Helper: return a minimal valid header dict."""
    return {
        "entity_uuid": VALID_UUID,
        "entity_type_id": VALID_TYPE_ID,
        "artifact_type": VALID_ARTIFACT_TYPE,
        "created_at": VALID_CREATED_AT,
    }


class TestValidateHeader:
    """Tests for validate_header (Task 2.1.1)."""

    def test_ac5_valid_header_returns_empty_list(self):
        """AC-5: all required fields with valid values returns empty list."""
        errors = validate_header(_valid_header())
        assert errors == []

    def test_ac6_missing_required_field(self):
        """AC-6: missing each required field individually returns error with field name."""
        for field in REQUIRED_FIELDS:
            header = _valid_header()
            del header[field]
            errors = validate_header(header)
            assert len(errors) >= 1, f"Expected error for missing {field}"
            assert any(field in e for e in errors), (
                f"Error for missing {field} should mention the field name"
            )

    def test_ac7_invalid_uuid_format(self):
        """AC-7: invalid UUID format returns validation error."""
        header = _valid_header()
        header["entity_uuid"] = "not-a-uuid"
        errors = validate_header(header)
        assert len(errors) >= 1
        assert any("entity_uuid" in e or "UUID" in e for e in errors)

    def test_valid_uuid_no_error(self):
        """Valid lowercase UUID returns no error."""
        errors = validate_header(_valid_header())
        assert errors == []

    def test_uppercase_uuid_accepted(self):
        """Uppercase hex UUID accepted -- lowercased before regex match."""
        header = _valid_header()
        header["entity_uuid"] = "A1B2C3D4-E5F6-4A7B-8C9D-0E1F2A3B4C5D"
        errors = validate_header(header)
        assert errors == []

    def test_invalid_artifact_type(self):
        """Invalid artifact_type returns validation error."""
        header = _valid_header()
        header["artifact_type"] = "unknown_type"
        errors = validate_header(header)
        assert len(errors) >= 1
        assert any("artifact_type" in e for e in errors)

    def test_each_valid_artifact_type(self):
        """Each valid artifact_type returns no error."""
        for at in ALLOWED_ARTIFACT_TYPES:
            header = _valid_header()
            header["artifact_type"] = at
            errors = validate_header(header)
            assert errors == [], f"Unexpected error for artifact_type={at}: {errors}"

    def test_invalid_created_at(self):
        """Invalid created_at (not ISO 8601) returns validation error."""
        header = _valid_header()
        header["created_at"] = "not-a-date"
        errors = validate_header(header)
        assert len(errors) >= 1
        assert any("created_at" in e for e in errors)

    def test_valid_created_at_with_timezone(self):
        """Valid created_at with timezone returns no error."""
        header = _valid_header()
        header["created_at"] = "2026-03-01T12:00:00+05:30"
        errors = validate_header(header)
        assert errors == []

    def test_unknown_field_returns_error(self):
        """Unknown field present returns validation error."""
        header = _valid_header()
        header["bogus_field"] = "some_value"
        errors = validate_header(header)
        assert len(errors) >= 1
        assert any("bogus_field" in e for e in errors)

    def test_multiple_errors_no_short_circuit(self):
        """Multiple errors all returned (no short-circuit)."""
        header = {
            # missing entity_uuid entirely
            "entity_type_id": VALID_TYPE_ID,
            "artifact_type": "invalid_type",  # bad artifact_type
            "created_at": "not-a-date",  # bad date
            "bogus": "x",  # unknown field
        }
        errors = validate_header(header)
        # Should have at least 4 errors: missing uuid, bad artifact_type,
        # bad created_at, unknown field
        assert len(errors) >= 4


class TestBuildHeader:
    """Tests for build_header (Task 2.2.1)."""

    def test_ac10_valid_args_returns_valid_dict(self):
        """AC-10: valid required args returns dict passing validate_header."""
        header = build_header(
            VALID_UUID, VALID_TYPE_ID, VALID_ARTIFACT_TYPE, VALID_CREATED_AT,
        )
        assert header["entity_uuid"] == VALID_UUID
        assert header["entity_type_id"] == VALID_TYPE_ID
        assert header["artifact_type"] == VALID_ARTIFACT_TYPE
        assert header["created_at"] == VALID_CREATED_AT
        assert validate_header(header) == []

    def test_ac11_invalid_artifact_type_raises(self):
        """AC-11: invalid artifact_type raises ValueError."""
        with pytest.raises(ValueError):
            build_header(VALID_UUID, VALID_TYPE_ID, "invalid", VALID_CREATED_AT)

    def test_invalid_uuid_raises(self):
        """Invalid UUID raises ValueError."""
        with pytest.raises(ValueError):
            build_header("not-a-uuid", VALID_TYPE_ID, VALID_ARTIFACT_TYPE, VALID_CREATED_AT)

    def test_invalid_created_at_raises(self):
        """Invalid created_at raises ValueError."""
        with pytest.raises(ValueError):
            build_header(VALID_UUID, VALID_TYPE_ID, VALID_ARTIFACT_TYPE, "bad-date")

    def test_valid_with_optional_kwargs(self):
        """Valid required + valid optional kwargs all present in output."""
        header = build_header(
            VALID_UUID, VALID_TYPE_ID, VALID_ARTIFACT_TYPE, VALID_CREATED_AT,
            feature_id="002",
            feature_slug="markdown-entity-file-header-sc",
            phase="specify",
        )
        assert header["feature_id"] == "002"
        assert header["feature_slug"] == "markdown-entity-file-header-sc"
        assert header["phase"] == "specify"
        assert validate_header(header) == []

    def test_unknown_kwarg_raises(self):
        """Unknown optional kwarg raises ValueError."""
        with pytest.raises(ValueError):
            build_header(
                VALID_UUID, VALID_TYPE_ID, VALID_ARTIFACT_TYPE, VALID_CREATED_AT,
                bogus_field="value",
            )


# ---------------------------------------------------------------------------
# Phase 3: Read Function
# ---------------------------------------------------------------------------


def _write_file(path: str, content: str) -> None:
    """Helper: write text content to a file with UTF-8 encoding."""
    with open(path, "w", encoding="utf-8") as f:
        f.write(content)


def _write_binary(path: str, data: bytes) -> None:
    """Helper: write binary content to a file."""
    with open(path, "wb") as f:
        f.write(data)


class TestReadFrontmatter:
    """Tests for read_frontmatter (Task 3.1.1)."""

    def test_ac2_valid_frontmatter(self, tmp_path):
        """AC-2: file with valid frontmatter returns dict with all fields."""
        fpath = str(tmp_path / "spec.md")
        _write_file(fpath, (
            "---\n"
            f"entity_uuid: {VALID_UUID}\n"
            f"entity_type_id: {VALID_TYPE_ID}\n"
            f"artifact_type: {VALID_ARTIFACT_TYPE}\n"
            f"created_at: {VALID_CREATED_AT}\n"
            "---\n"
            "# Spec Content\n"
        ))
        result = read_frontmatter(fpath)
        assert result is not None
        assert result["entity_uuid"] == VALID_UUID
        assert result["entity_type_id"] == VALID_TYPE_ID
        assert result["artifact_type"] == VALID_ARTIFACT_TYPE
        assert result["created_at"] == VALID_CREATED_AT

    def test_ac3_legacy_file_no_frontmatter(self, tmp_path):
        """AC-3: legacy file (no --- on line 1) returns None."""
        fpath = str(tmp_path / "spec.md")
        _write_file(fpath, "# Just a markdown file\nNo frontmatter here.\n")
        result = read_frontmatter(fpath)
        assert result is None

    def test_ac4_malformed_no_closing(self, tmp_path, caplog):
        """AC-4: malformed frontmatter (opening --- but no closing ---) returns None + warning."""
        fpath = str(tmp_path / "spec.md")
        _write_file(fpath, (
            "---\n"
            f"entity_uuid: {VALID_UUID}\n"
            "some content without closing delimiter\n"
        ))
        with caplog.at_level(logging.WARNING, logger="entity_registry.frontmatter"):
            result = read_frontmatter(fpath)
        assert result is None
        assert any("malformed" in r.message.lower() for r in caplog.records)

    def test_empty_file(self, tmp_path):
        """Empty file returns None."""
        fpath = str(tmp_path / "empty.md")
        _write_file(fpath, "")
        result = read_frontmatter(fpath)
        assert result is None

    def test_empty_block_returns_empty_dict(self, tmp_path):
        """--- on line 1 and --- on line 2 (empty block) returns {} (empty dict, NOT None)."""
        fpath = str(tmp_path / "spec.md")
        _write_file(fpath, "---\n---\nBody content\n")
        result = read_frontmatter(fpath)
        assert result is not None
        assert result == {}

    def test_values_with_colons(self, tmp_path):
        """Frontmatter with values containing ': ' parses correctly."""
        fpath = str(tmp_path / "spec.md")
        _write_file(fpath, (
            "---\n"
            f"entity_type_id: {VALID_TYPE_ID}\n"
            "---\n"
            "Body\n"
        ))
        result = read_frontmatter(fpath)
        assert result is not None
        assert result["entity_type_id"] == VALID_TYPE_ID

    def test_binary_content_returns_none(self, tmp_path, caplog):
        """Binary content (null bytes in first 8192 bytes) returns None + warning."""
        fpath = str(tmp_path / "binary.md")
        _write_binary(fpath, b"---\n\x00binary data\n---\n")
        with caplog.at_level(logging.WARNING, logger="entity_registry.frontmatter"):
            result = read_frontmatter(fpath)
        assert result is None
        assert any("binary" in r.message.lower() for r in caplog.records)

    def test_file_not_found_returns_none(self, tmp_path, caplog):
        """File does not exist returns None + warning."""
        fpath = str(tmp_path / "nonexistent.md")
        with caplog.at_level(logging.WARNING, logger="entity_registry.frontmatter"):
            result = read_frontmatter(fpath)
        assert result is None
        assert any("not found" in r.message.lower() or "file not found" in r.message.lower()
                    for r in caplog.records)

    def test_body_preserved_only_header_parsed(self, tmp_path):
        """Body content after frontmatter is not included in parsed dict."""
        fpath = str(tmp_path / "spec.md")
        _write_file(fpath, (
            "---\n"
            f"entity_uuid: {VALID_UUID}\n"
            "---\n"
            "body_key: this should not appear\n"
            "# Heading\n"
        ))
        result = read_frontmatter(fpath)
        assert result is not None
        assert "body_key" not in result
        assert result == {"entity_uuid": VALID_UUID}

    def test_large_file_only_header_parsed(self, tmp_path):
        """Large file with frontmatter -- only header portion parsed."""
        fpath = str(tmp_path / "large.md")
        body = "x" * 100_000 + "\n"
        _write_file(fpath, (
            "---\n"
            f"entity_uuid: {VALID_UUID}\n"
            "---\n"
            + body
        ))
        result = read_frontmatter(fpath)
        assert result is not None
        assert result == {"entity_uuid": VALID_UUID}
