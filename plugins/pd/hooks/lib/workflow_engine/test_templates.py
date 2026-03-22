"""Tests for workflow_engine.templates module."""
from __future__ import annotations

import pytest

from workflow_engine.templates import (
    FEATURE_7_PHASE,
    FIVE_D_FULL,
    WEIGHT_TEMPLATES,
    get_template,
)


# ---------------------------------------------------------------------------
# WEIGHT_TEMPLATES structure tests
# ---------------------------------------------------------------------------


class TestWeightTemplatesRegistry:
    def test_all_values_are_non_empty_lists(self):
        """Every template value must be a non-empty list of strings."""
        for key, phases in WEIGHT_TEMPLATES.items():
            assert isinstance(phases, list), f"{key} value is not a list"
            assert len(phases) > 0, f"{key} has empty phase list"
            for phase in phases:
                assert isinstance(phase, str), f"{key} has non-string phase: {phase}"

    def test_feature_standard_is_7_phase(self):
        assert WEIGHT_TEMPLATES[("feature", "standard")] == FEATURE_7_PHASE

    def test_feature_full_is_7_phase(self):
        assert WEIGHT_TEMPLATES[("feature", "full")] == FEATURE_7_PHASE

    def test_feature_light(self):
        assert WEIGHT_TEMPLATES[("feature", "light")] == [
            "specify", "implement", "finish",
        ]

    def test_task_light(self):
        assert WEIGHT_TEMPLATES[("task", "light")] == ["deliver"]

    def test_task_standard(self):
        assert WEIGHT_TEMPLATES[("task", "standard")] == [
            "define", "deliver", "debrief",
        ]

    def test_project_standard_is_5d(self):
        assert WEIGHT_TEMPLATES[("project", "standard")] == FIVE_D_FULL

    def test_project_full_is_5d(self):
        assert WEIGHT_TEMPLATES[("project", "full")] == FIVE_D_FULL

    def test_project_light(self):
        assert WEIGHT_TEMPLATES[("project", "light")] == [
            "define", "design", "deliver", "debrief",
        ]

    def test_initiative_standard_is_5d(self):
        assert WEIGHT_TEMPLATES[("initiative", "standard")] == FIVE_D_FULL

    def test_initiative_full_is_5d(self):
        assert WEIGHT_TEMPLATES[("initiative", "full")] == FIVE_D_FULL

    def test_objective_standard(self):
        assert WEIGHT_TEMPLATES[("objective", "standard")] == [
            "define", "design", "deliver", "debrief",
        ]

    def test_key_result_standard(self):
        assert WEIGHT_TEMPLATES[("key_result", "standard")] == [
            "define", "deliver", "debrief",
        ]

    def test_expected_template_count(self):
        """Registry should have exactly 12 defined templates."""
        assert len(WEIGHT_TEMPLATES) == 12

    def test_templates_are_independent_copies(self):
        """Registry values should be independent lists (not shared refs)."""
        t1 = WEIGHT_TEMPLATES[("initiative", "full")]
        t2 = WEIGHT_TEMPLATES[("initiative", "standard")]
        # Both equal to FIVE_D_FULL but should be distinct list objects
        assert t1 == t2
        assert t1 is not t2


# ---------------------------------------------------------------------------
# get_template() tests
# ---------------------------------------------------------------------------


class TestGetTemplate:
    def test_lookup_feature_standard(self):
        result = get_template("feature", "standard")
        assert result == FEATURE_7_PHASE

    def test_lookup_feature_light(self):
        result = get_template("feature", "light")
        assert result == ["specify", "implement", "finish"]

    def test_lookup_task_light(self):
        result = get_template("task", "light")
        assert result == ["deliver"]

    def test_lookup_project_standard(self):
        result = get_template("project", "standard")
        assert result == FIVE_D_FULL

    def test_unknown_pair_raises_key_error(self):
        with pytest.raises(KeyError, match="No workflow template"):
            get_template("feature", "ultra")

    def test_unknown_type_raises_key_error(self):
        with pytest.raises(KeyError, match="No workflow template"):
            get_template("unknown_type", "standard")

    def test_returns_copy_not_original(self):
        """get_template should return a copy to prevent registry mutation."""
        result = get_template("feature", "standard")
        result.append("extra-phase")
        # Original should be unchanged
        assert "extra-phase" not in get_template("feature", "standard")

    def test_all_defined_pairs_retrievable(self):
        """Every key in WEIGHT_TEMPLATES should be retrievable via get_template."""
        for (etype, weight) in WEIGHT_TEMPLATES:
            result = get_template(etype, weight)
            assert result == WEIGHT_TEMPLATES[(etype, weight)]
