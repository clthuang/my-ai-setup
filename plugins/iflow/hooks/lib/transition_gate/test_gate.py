"""Transition gate tests."""
from __future__ import annotations

# NAMING: All guard tests MUST follow test_G{XX}_{description} pattern
# (uppercase G) for coverage introspection.

import dataclasses

import pytest

from transition_gate.models import (
    Enforcement,
    FeatureState,
    Phase,
    PhaseInfo,
    Severity,
    TransitionResult,
    YoloBehavior,
)


# ---------------------------------------------------------------------------
# Phase enum tests
# ---------------------------------------------------------------------------


class TestPhaseEnum:
    """Phase enum instantiation and str-mixin behavior."""

    def test_phase_has_seven_values(self) -> None:
        assert len(Phase) == 7

    def test_phase_brainstorm(self) -> None:
        assert Phase.brainstorm == "brainstorm"

    def test_phase_specify(self) -> None:
        assert Phase.specify == "specify"

    def test_phase_design(self) -> None:
        assert Phase.design == "design"

    def test_phase_create_plan_hyphen(self) -> None:
        """str mixin: Python identifier uses underscore, value uses hyphen."""
        assert Phase.create_plan == "create-plan"

    def test_phase_create_tasks_hyphen(self) -> None:
        assert Phase.create_tasks == "create-tasks"

    def test_phase_implement(self) -> None:
        assert Phase.implement == "implement"

    def test_phase_finish(self) -> None:
        assert Phase.finish == "finish"

    def test_phase_constructible_from_string(self) -> None:
        assert Phase("create-plan") is Phase.create_plan


# ---------------------------------------------------------------------------
# Severity enum tests
# ---------------------------------------------------------------------------


class TestSeverityEnum:
    """Severity enum instantiation."""

    def test_severity_block(self) -> None:
        assert Severity.block == "block"

    def test_severity_warn(self) -> None:
        assert Severity.warn == "warn"

    def test_severity_info(self) -> None:
        assert Severity.info == "info"

    def test_severity_has_three_values(self) -> None:
        assert len(Severity) == 3


# ---------------------------------------------------------------------------
# Enforcement enum tests
# ---------------------------------------------------------------------------


class TestEnforcementEnum:
    """Enforcement enum instantiation."""

    def test_enforcement_hard_block(self) -> None:
        assert Enforcement.hard_block == "hard_block"

    def test_enforcement_soft_warn(self) -> None:
        assert Enforcement.soft_warn == "soft_warn"

    def test_enforcement_informational(self) -> None:
        assert Enforcement.informational == "informational"

    def test_enforcement_has_three_values(self) -> None:
        assert len(Enforcement) == 3


# ---------------------------------------------------------------------------
# YoloBehavior enum tests
# ---------------------------------------------------------------------------


class TestYoloBehaviorEnum:
    """YoloBehavior enum instantiation."""

    def test_yolo_auto_select(self) -> None:
        assert YoloBehavior.auto_select == "auto_select"

    def test_yolo_hard_stop(self) -> None:
        assert YoloBehavior.hard_stop == "hard_stop"

    def test_yolo_skip(self) -> None:
        assert YoloBehavior.skip == "skip"

    def test_yolo_unchanged(self) -> None:
        assert YoloBehavior.unchanged == "unchanged"

    def test_yolo_has_four_values(self) -> None:
        assert len(YoloBehavior) == 4


# ---------------------------------------------------------------------------
# TransitionResult dataclass tests
# ---------------------------------------------------------------------------


class TestTransitionResult:
    """TransitionResult dataclass instantiation and frozen behavior."""

    def test_construct_allowed(self) -> None:
        result = TransitionResult(
            allowed=True,
            reason="All checks passed",
            severity=Severity.info,
            guard_id="G-22",
        )
        assert result.allowed is True
        assert result.reason == "All checks passed"
        assert result.severity == Severity.info
        assert result.guard_id == "G-22"

    def test_construct_blocked(self) -> None:
        result = TransitionResult(
            allowed=False,
            reason="Phase not reached",
            severity=Severity.block,
            guard_id="G-22",
        )
        assert result.allowed is False
        assert result.severity == Severity.block

    def test_frozen_raises_on_mutation(self) -> None:
        result = TransitionResult(
            allowed=True,
            reason="ok",
            severity=Severity.info,
            guard_id="G-01",
        )
        with pytest.raises(dataclasses.FrozenInstanceError):
            result.allowed = False  # type: ignore[misc]


# ---------------------------------------------------------------------------
# FeatureState dataclass tests
# ---------------------------------------------------------------------------


class TestFeatureState:
    """FeatureState dataclass instantiation."""

    def test_construct_minimal(self) -> None:
        fs = FeatureState(
            feature_id="007",
            status="active",
            current_branch="feat/007",
            expected_branch="feat/007",
        )
        assert fs.feature_id == "007"
        assert fs.status == "active"
        assert fs.completed_phases == []
        assert fs.active_phase is None
        assert fs.meta_has_brainstorm_source is False

    def test_construct_full(self) -> None:
        fs = FeatureState(
            feature_id="007",
            status="active",
            current_branch="feat/007",
            expected_branch="feat/007",
            completed_phases=["brainstorm", "specify"],
            active_phase="design",
            meta_has_brainstorm_source=True,
        )
        assert fs.completed_phases == ["brainstorm", "specify"]
        assert fs.active_phase == "design"
        assert fs.meta_has_brainstorm_source is True

    def test_mutable(self) -> None:
        """FeatureState is intentionally mutable (not frozen)."""
        fs = FeatureState(
            feature_id="007",
            status="planned",
            current_branch="main",
            expected_branch="feat/007",
        )
        fs.status = "active"
        assert fs.status == "active"


# ---------------------------------------------------------------------------
# PhaseInfo dataclass tests
# ---------------------------------------------------------------------------


class TestPhaseInfo:
    """PhaseInfo dataclass instantiation."""

    def test_construct(self) -> None:
        pi = PhaseInfo(
            phase=Phase.brainstorm,
            started=True,
            completed=False,
        )
        assert pi.phase == Phase.brainstorm
        assert pi.started is True
        assert pi.completed is False

    def test_completed_phase(self) -> None:
        pi = PhaseInfo(
            phase=Phase.specify,
            started=True,
            completed=True,
        )
        assert pi.completed is True
