"""Transition gate tests."""
from __future__ import annotations

# NAMING: All guard tests MUST follow test_G{XX}_{description} pattern
# (uppercase G) for coverage introspection.

import dataclasses
import inspect
import re
from pathlib import Path

import pytest

from transition_gate.constants import (
    ARTIFACT_GUARD_MAP,
    ARTIFACT_PHASE_MAP,
    COMMAND_PHASES,
    EXPECTED_GUARD_IDS,
    GUARD_METADATA,
    HARD_PREREQUISITES,
    MAX_ITERATIONS,
    MIN_ARTIFACT_SIZE,
    PHASE_GUARD_MAP,
    PHASE_SEQUENCE,
    SERVICE_GUARD_MAP,
)
from transition_gate.gate import (
    _phase_index,
    brainstorm_quality_gate,
    brainstorm_readiness_gate,
    check_active_feature,
    check_active_feature_conflict,
    check_backward_transition,
    check_branch,
    check_hard_prerequisites,
    check_merge_conflict,
    check_orchestrate_prerequisite,
    check_partial_phase,
    check_prd_exists,
    check_soft_prerequisites,
    check_task_completion,
    check_terminal_status,
    check_yolo_override,
    fail_open_mcp,
    get_next_phase,
    implement_circuit_breaker,
    phase_handoff_gate,
    planned_to_active_transition,
    pre_merge_validation,
    review_quality_gate,
    secretary_review_criteria,
    validate_artifact,
    validate_prd,
    validate_transition,
)
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


# ---------------------------------------------------------------------------
# Constants: Phase sequence tests (Task 2.1)
# ---------------------------------------------------------------------------


class TestPhaseSequence:
    """PHASE_SEQUENCE and COMMAND_PHASES constants."""

    def test_phase_sequence_length(self) -> None:
        assert len(PHASE_SEQUENCE) == 7

    def test_phase_sequence_all_phases_present(self) -> None:
        """Every Phase enum value appears in PHASE_SEQUENCE."""
        assert set(PHASE_SEQUENCE) == set(Phase)

    def test_phase_sequence_canonical_order(self) -> None:
        assert PHASE_SEQUENCE == (
            Phase.brainstorm,
            Phase.specify,
            Phase.design,
            Phase.create_plan,
            Phase.create_tasks,
            Phase.implement,
            Phase.finish,
        )

    def test_command_phases_starts_with_specify(self) -> None:
        assert COMMAND_PHASES[0] == Phase.specify

    def test_command_phases_excludes_brainstorm(self) -> None:
        assert Phase.brainstorm not in COMMAND_PHASES

    def test_command_phases_length(self) -> None:
        assert len(COMMAND_PHASES) == 6


# ---------------------------------------------------------------------------
# Constants: Prerequisite and artifact maps (Task 2.2)
# ---------------------------------------------------------------------------


class TestPrerequisiteAndArtifactMaps:
    """HARD_PREREQUISITES, ARTIFACT_PHASE_MAP, ARTIFACT_GUARD_MAP."""

    def test_hard_prerequisites_seven_entries(self) -> None:
        assert len(HARD_PREREQUISITES) == 7

    def test_hard_prerequisites_brainstorm_empty(self) -> None:
        assert HARD_PREREQUISITES["brainstorm"] == []

    def test_hard_prerequisites_specify_empty(self) -> None:
        assert HARD_PREREQUISITES["specify"] == []

    def test_hard_prerequisites_design(self) -> None:
        assert HARD_PREREQUISITES["design"] == ["spec.md"]

    def test_hard_prerequisites_create_plan(self) -> None:
        assert HARD_PREREQUISITES["create-plan"] == ["spec.md", "design.md"]

    def test_hard_prerequisites_create_tasks(self) -> None:
        assert HARD_PREREQUISITES["create-tasks"] == ["spec.md", "design.md", "plan.md"]

    def test_hard_prerequisites_implement(self) -> None:
        assert HARD_PREREQUISITES["implement"] == ["spec.md", "tasks.md"]

    def test_hard_prerequisites_finish_empty(self) -> None:
        assert HARD_PREREQUISITES["finish"] == []

    def test_artifact_phase_map_five_entries(self) -> None:
        assert len(ARTIFACT_PHASE_MAP) == 5

    def test_artifact_phase_map_brainstorm(self) -> None:
        assert ARTIFACT_PHASE_MAP["brainstorm"] == "prd.md"

    def test_artifact_phase_map_specify(self) -> None:
        assert ARTIFACT_PHASE_MAP["specify"] == "spec.md"

    def test_artifact_guard_map_two_entries(self) -> None:
        assert len(ARTIFACT_GUARD_MAP) == 2

    def test_artifact_guard_map_implement_spec(self) -> None:
        assert ARTIFACT_GUARD_MAP[("implement", "spec.md")] == "G-05"

    def test_artifact_guard_map_implement_tasks(self) -> None:
        assert ARTIFACT_GUARD_MAP[("implement", "tasks.md")] == "G-06"


# ---------------------------------------------------------------------------
# Constants: Service, iteration, and phase guard maps (Task 2.3)
# ---------------------------------------------------------------------------


class TestServiceAndPhaseGuardMaps:
    """SERVICE_GUARD_MAP, PHASE_GUARD_MAP, MIN_ARTIFACT_SIZE, MAX_ITERATIONS."""

    def test_service_guard_map_four_entries(self) -> None:
        assert len(SERVICE_GUARD_MAP) == 4

    def test_service_guard_map_brainstorm(self) -> None:
        assert SERVICE_GUARD_MAP["brainstorm"] == "G-13"

    def test_service_guard_map_retrospective(self) -> None:
        assert SERVICE_GUARD_MAP["retrospective"] == "G-16"

    def test_phase_guard_map_review_quality_specify(self) -> None:
        assert PHASE_GUARD_MAP["review_quality"]["specify"] == "G-46"

    def test_phase_guard_map_review_quality_five_phases(self) -> None:
        assert len(PHASE_GUARD_MAP["review_quality"]) == 5

    def test_phase_guard_map_phase_handoff_four_phases(self) -> None:
        assert len(PHASE_GUARD_MAP["phase_handoff"]) == 4

    def test_phase_guard_map_phase_handoff_no_implement(self) -> None:
        assert "implement" not in PHASE_GUARD_MAP["phase_handoff"]

    def test_min_artifact_size(self) -> None:
        assert MIN_ARTIFACT_SIZE == 100

    def test_max_iterations_brainstorm(self) -> None:
        assert MAX_ITERATIONS["brainstorm"] == 3

    def test_max_iterations_default(self) -> None:
        assert MAX_ITERATIONS["default"] == 5


# ---------------------------------------------------------------------------
# Constants: Guard metadata integrity (Task 2.6)
# ---------------------------------------------------------------------------


class TestGuardMetadataIntegrity:
    """GUARD_METADATA and EXPECTED_GUARD_IDS integrity checks."""

    def test_integrity_exact_membership(self) -> None:
        """Guard metadata keys match expected guard IDs exactly."""
        assert set(GUARD_METADATA.keys()) == EXPECTED_GUARD_IDS

    def test_integrity_count_43(self) -> None:
        assert len(GUARD_METADATA) == 43

    def test_integrity_expected_guard_ids_count(self) -> None:
        assert len(EXPECTED_GUARD_IDS) == 43

    def test_integrity_all_phases_in_sequence(self) -> None:
        """Every Phase enum value is present in PHASE_SEQUENCE."""
        phase_set = set(PHASE_SEQUENCE)
        for phase in Phase:
            assert phase in phase_set, f"Phase {phase} missing from PHASE_SEQUENCE"

    def test_integrity_phase_sequence_length_seven(self) -> None:
        assert len(PHASE_SEQUENCE) == 7

    def test_integrity_metadata_structure(self) -> None:
        """Every guard metadata entry has required keys with correct types."""
        for guard_id, meta in GUARD_METADATA.items():
            assert "enforcement" in meta, f"{guard_id} missing enforcement"
            assert "yolo_behavior" in meta, f"{guard_id} missing yolo_behavior"
            assert "affected_phases" in meta, f"{guard_id} missing affected_phases"
            assert isinstance(meta["enforcement"], Enforcement), (
                f"{guard_id} enforcement not Enforcement enum"
            )
            assert isinstance(meta["yolo_behavior"], YoloBehavior), (
                f"{guard_id} yolo_behavior not YoloBehavior enum"
            )
            assert isinstance(meta["affected_phases"], list), (
                f"{guard_id} affected_phases not list"
            )

    def test_spot_check_G22_enforcement(self) -> None:
        assert GUARD_METADATA["G-22"]["enforcement"] == Enforcement.soft_warn

    def test_spot_check_G41_yolo_behavior(self) -> None:
        assert GUARD_METADATA["G-41"]["yolo_behavior"] == YoloBehavior.hard_stop

    def test_spot_check_G49_enforcement(self) -> None:
        assert GUARD_METADATA["G-49"]["enforcement"] == Enforcement.soft_warn

    def test_spot_check_G51_enforcement_override(self) -> None:
        """G-51 has intentional enforcement override to hard_block."""
        assert GUARD_METADATA["G-51"]["enforcement"] == Enforcement.hard_block


# ---------------------------------------------------------------------------
# Guard coverage introspection (Task 2.7)
# ---------------------------------------------------------------------------


def test_guard_coverage_introspection() -> None:
    """Verify all 43 guard IDs have at least one test function.

    Collects test function names matching test_G\\d+_ via inspect,
    extracts guard IDs, and asserts coverage of all 43 in EXPECTED_GUARD_IDS.
    """
    # Get all members of the current module
    current_module = inspect.getmodule(test_guard_coverage_introspection)
    assert current_module is not None

    guard_id_pattern = re.compile(r"test_G(\d+)_")
    covered_ids: set[str] = set()

    for name, obj in inspect.getmembers(current_module):
        # Check top-level test functions
        if callable(obj) and guard_id_pattern.match(name):
            match = guard_id_pattern.match(name)
            if match:
                covered_ids.add(f"G-{match.group(1)}")
        # Check test class methods
        if inspect.isclass(obj) and name.startswith("Test"):
            for method_name, _method in inspect.getmembers(obj, predicate=inspect.isfunction):
                match = guard_id_pattern.match(method_name)
                if match:
                    covered_ids.add(f"G-{match.group(1)}")

    missing = EXPECTED_GUARD_IDS - covered_ids
    assert not missing, (
        f"Missing test coverage for {len(missing)} guards: "
        f"{sorted(missing, key=lambda x: int(x.split('-')[1]))}"
    )


# ---------------------------------------------------------------------------
# YAML validation (Task 2.8)
# ---------------------------------------------------------------------------


class TestYamlValidation:
    """Validate GUARD_METADATA against guard-rules.yaml source."""

    @staticmethod
    def _find_yaml_path() -> Path | None:
        """Walk up from this file until .git/ found, then resolve YAML path."""
        current = Path(__file__).resolve().parent
        while current != current.parent:
            if (current / ".git").exists():
                yaml_path = (
                    current
                    / "docs"
                    / "features"
                    / "006-transition-guard-audit-and-rul"
                    / "guard-rules.yaml"
                )
                if yaml_path.exists():
                    return yaml_path
                return None
            current = current.parent
        return None

    @staticmethod
    def _parse_yaml_guards(yaml_path: Path) -> dict[str, dict]:
        """Parse guard-rules.yaml via line-by-line regex (no PyYAML).

        Returns dict of guard_id -> {enforcement, yolo_behavior, affected_phases,
        consolidation_target}.
        """
        guards: dict[str, dict] = {}
        current_id: str | None = None
        current: dict = {}
        in_phases = False

        id_re = re.compile(r'^- id:\s*"(G-\d+)"')
        field_re = re.compile(r'^\s+(\w+):\s*"([^"]+)"')
        phase_re = re.compile(r'^\s+-\s*"([^"]+)"')

        with yaml_path.open() as f:
            for line in f:
                id_match = id_re.match(line)
                if id_match:
                    if current_id is not None:
                        guards[current_id] = current
                    current_id = id_match.group(1)
                    current = {"affected_phases": []}
                    in_phases = False
                    continue

                if line.strip() == "affected_phases:":
                    in_phases = True
                    continue

                if in_phases:
                    phase_match = phase_re.match(line)
                    if phase_match:
                        current["affected_phases"].append(phase_match.group(1))
                        continue
                    else:
                        in_phases = False

                field_match = field_re.match(line)
                if field_match:
                    key, value = field_match.group(1), field_match.group(2)
                    if key in ("enforcement", "yolo_behavior", "consolidation_target"):
                        current[key] = value

            # Don't forget last guard
            if current_id is not None:
                guards[current_id] = current

        return guards

    def test_yaml_validation(self) -> None:
        """Validate every GUARD_METADATA entry against guard-rules.yaml source.

        Normalizes YAML hyphens to Python underscores for enforcement and
        yolo_behavior comparisons.
        """
        yaml_path = self._find_yaml_path()
        if yaml_path is None:
            pytest.skip("guard-rules.yaml not found")

        yaml_guards = self._parse_yaml_guards(yaml_path)

        # Filter to transition_gate guards
        tg_guards = {
            gid: meta
            for gid, meta in yaml_guards.items()
            if meta.get("consolidation_target") == "transition_gate"
        }

        # Verify all expected guards found in YAML
        for guard_id in EXPECTED_GUARD_IDS:
            assert guard_id in tg_guards, (
                f"{guard_id} in EXPECTED_GUARD_IDS but not found in YAML "
                f"with consolidation_target: transition_gate"
            )

        # Verify metadata matches YAML
        errors: list[str] = []
        for guard_id in sorted(EXPECTED_GUARD_IDS, key=lambda x: int(x.split("-")[1])):
            yaml_meta = tg_guards[guard_id]
            py_meta = GUARD_METADATA[guard_id]

            # Normalize YAML hyphens to Python underscores
            yaml_enforcement = yaml_meta["enforcement"].replace("-", "_")
            yaml_yolo = yaml_meta["yolo_behavior"].replace("-", "_")

            # G-51: Skip enforcement comparison — intentional override from
            # soft-warn to hard-block per spec Enforcement Overrides table.
            if guard_id != "G-51":
                if py_meta["enforcement"].value != yaml_enforcement:
                    errors.append(
                        f"{guard_id} enforcement: "
                        f"YAML={yaml_enforcement}, "
                        f"Python={py_meta['enforcement'].value}"
                    )

            if py_meta["yolo_behavior"].value != yaml_yolo:
                errors.append(
                    f"{guard_id} yolo_behavior: "
                    f"YAML={yaml_yolo}, "
                    f"Python={py_meta['yolo_behavior'].value}"
                )

            if py_meta["affected_phases"] != yaml_meta["affected_phases"]:
                errors.append(
                    f"{guard_id} affected_phases: "
                    f"YAML={yaml_meta['affected_phases']}, "
                    f"Python={py_meta['affected_phases']}"
                )

        assert not errors, (
            f"GUARD_METADATA mismatches ({len(errors)}):\n"
            + "\n".join(f"  - {e}" for e in errors)
        )


# ===========================================================================
# Phase 3: Gate function tests
# ===========================================================================


# ---------------------------------------------------------------------------
# Task 3.1: Internal helpers (_phase_index)
# ---------------------------------------------------------------------------


class TestPhaseIndex:
    """Tests for _phase_index internal helper."""

    def test_phase_index_valid_returns_index(self) -> None:
        """Valid phase returns its index in PHASE_SEQUENCE."""
        assert _phase_index("design") == 2

    def test_phase_index_invalid_returns_negative_one(self) -> None:
        """Invalid phase returns -1."""
        assert _phase_index("nonexistent") == -1

    def test_phase_index_first_and_last(self) -> None:
        """First phase returns 0, last returns 6."""
        assert _phase_index("brainstorm") == 0
        assert _phase_index("finish") == 6


# ---------------------------------------------------------------------------
# Task 3.2: check_yolo_override
# ---------------------------------------------------------------------------


class TestYoloOverride:
    """Tests for check_yolo_override."""

    def test_yolo_override_skip_returns_allowed(self) -> None:
        """skip yolo_behavior -> allowed=True, severity=info."""
        # G-45 has yolo_behavior=skip
        result = check_yolo_override("G-45", is_yolo=True)
        assert result is not None
        assert result.allowed is True
        assert result.severity == Severity.info
        assert "Skipped in YOLO mode" in result.reason

    def test_yolo_override_auto_select_returns_warn(self) -> None:
        """auto_select yolo_behavior -> allowed=True, severity=warn."""
        # G-09 has yolo_behavior=auto_select
        result = check_yolo_override("G-09", is_yolo=True)
        assert result is not None
        assert result.allowed is True
        assert result.severity == Severity.warn
        assert "Auto-selected default in YOLO mode" in result.reason

    def test_yolo_override_hard_stop_returns_none(self) -> None:
        """hard_stop yolo_behavior -> None (guard runs normally)."""
        # G-41 has yolo_behavior=hard_stop
        result = check_yolo_override("G-41", is_yolo=True)
        assert result is None

    def test_yolo_override_unchanged_returns_none(self) -> None:
        """unchanged yolo_behavior -> None (guard runs normally)."""
        # G-02 has yolo_behavior=unchanged
        result = check_yolo_override("G-02", is_yolo=True)
        assert result is None

    def test_yolo_override_unknown_guard_returns_none(self) -> None:
        """Unknown guard_id -> None."""
        result = check_yolo_override("G-99", is_yolo=True)
        assert result is None

    def test_yolo_override_is_yolo_false_returns_none(self) -> None:
        """is_yolo=False -> always None regardless of guard behavior."""
        result = check_yolo_override("G-45", is_yolo=False)
        assert result is None


# ---------------------------------------------------------------------------
# Task 3.3: Artifact & prerequisite functions (G-02..09)
# ---------------------------------------------------------------------------


class TestArtifactValidation:
    """Tests for validate_artifact (G-02..G-06)."""

    # G-02: Level 1 — artifact path exists

    def test_G02_validate_artifact_fail_missing(self) -> None:
        """G-02: Missing artifact -> blocked."""
        result = validate_artifact(
            phase="design",
            artifact_name="spec.md",
            artifact_path_exists=False,
            artifact_size=0,
            has_headers=False,
            has_required_sections=False,
        )
        assert result.allowed is False
        assert result.guard_id == "G-02"
        assert result.severity == Severity.block
        assert "BLOCKED" in result.reason
        assert "spec.md" in result.reason

    def test_G02_validate_artifact_pass_exists(self) -> None:
        """G-02: Artifact exists (all levels pass) -> allowed."""
        result = validate_artifact(
            phase="design",
            artifact_name="spec.md",
            artifact_path_exists=True,
            artifact_size=200,
            has_headers=True,
            has_required_sections=True,
        )
        assert result.allowed is True

    # G-03: Level 2 — artifact size

    def test_G03_validate_artifact_fail_too_small(self) -> None:
        """G-03: Artifact exists but too small -> blocked."""
        result = validate_artifact(
            phase="create-plan",
            artifact_name="spec.md",
            artifact_path_exists=True,
            artifact_size=50,
            has_headers=False,
            has_required_sections=False,
        )
        assert result.allowed is False
        assert result.guard_id == "G-03"
        assert result.severity == Severity.block

    def test_G03_validate_artifact_pass_exact_min(self) -> None:
        """G-03: Artifact at exact minimum size -> passes level 2."""
        result = validate_artifact(
            phase="design",
            artifact_name="spec.md",
            artifact_path_exists=True,
            artifact_size=100,
            has_headers=True,
            has_required_sections=True,
        )
        assert result.allowed is True

    # G-04: Level 3 — has headers

    def test_G04_validate_artifact_fail_no_headers(self) -> None:
        """G-04: No headers -> blocked."""
        result = validate_artifact(
            phase="create-tasks",
            artifact_name="design.md",
            artifact_path_exists=True,
            artifact_size=200,
            has_headers=False,
            has_required_sections=False,
        )
        assert result.allowed is False
        assert result.guard_id == "G-04"
        assert result.severity == Severity.block

    def test_G04_validate_artifact_pass_has_headers(self) -> None:
        """G-04: Has headers (all levels pass) -> allowed."""
        result = validate_artifact(
            phase="create-tasks",
            artifact_name="design.md",
            artifact_path_exists=True,
            artifact_size=200,
            has_headers=True,
            has_required_sections=True,
        )
        assert result.allowed is True

    # G-05: Level 4 — has required sections (default guard)

    def test_G05_validate_artifact_fail_no_sections(self) -> None:
        """G-05: No required sections (default guard) -> blocked."""
        result = validate_artifact(
            phase="implement",
            artifact_name="spec.md",
            artifact_path_exists=True,
            artifact_size=200,
            has_headers=True,
            has_required_sections=False,
        )
        assert result.allowed is False
        assert result.guard_id == "G-05"
        assert result.severity == Severity.block

    def test_G05_validate_artifact_pass_all_sections(self) -> None:
        """G-05: All required sections present -> allowed."""
        result = validate_artifact(
            phase="implement",
            artifact_name="spec.md",
            artifact_path_exists=True,
            artifact_size=200,
            has_headers=True,
            has_required_sections=True,
        )
        assert result.allowed is True
        assert result.guard_id == "G-05"

    # G-06: Level 4 — implement + tasks.md uses G-06

    def test_G06_validate_artifact_fail_tasks_no_sections(self) -> None:
        """G-06: tasks.md missing sections for implement -> blocked with G-06."""
        result = validate_artifact(
            phase="implement",
            artifact_name="tasks.md",
            artifact_path_exists=True,
            artifact_size=200,
            has_headers=True,
            has_required_sections=False,
        )
        assert result.allowed is False
        assert result.guard_id == "G-06"
        assert result.severity == Severity.block

    def test_G06_validate_artifact_pass_tasks_complete(self) -> None:
        """G-06: tasks.md complete for implement -> allowed with G-06."""
        result = validate_artifact(
            phase="implement",
            artifact_name="tasks.md",
            artifact_path_exists=True,
            artifact_size=200,
            has_headers=True,
            has_required_sections=True,
        )
        assert result.allowed is True
        assert result.guard_id == "G-06"


class TestPrerequisites:
    """Tests for check_hard_prerequisites (G-08), validate_prd (G-07), check_prd_exists (G-09)."""

    # G-07: PRD existence

    def test_G07_validate_prd_pass(self) -> None:
        """G-07: PRD exists -> allowed."""
        result = validate_prd(prd_path_exists=True)
        assert result.allowed is True
        assert result.guard_id == "G-07"

    def test_G07_validate_prd_fail(self) -> None:
        """G-07: PRD missing -> blocked."""
        result = validate_prd(prd_path_exists=False)
        assert result.allowed is False
        assert result.guard_id == "G-07"
        assert result.severity == Severity.block

    # G-08: Hard prerequisites

    def test_G08_check_hard_prerequisites_pass_all_present(self) -> None:
        """G-08: All prerequisites present -> allowed."""
        result = check_hard_prerequisites(
            phase="create-plan",
            existing_artifacts=["spec.md", "design.md"],
        )
        assert result.allowed is True
        assert result.guard_id == "G-08"

    def test_G08_check_hard_prerequisites_fail_missing(self) -> None:
        """G-08: Missing prerequisites -> blocked with missing list."""
        result = check_hard_prerequisites(
            phase="create-plan",
            existing_artifacts=["spec.md"],
        )
        assert result.allowed is False
        assert result.guard_id == "G-08"
        assert "design.md" in result.reason

    def test_G08_check_hard_prerequisites_empty_prereqs(self) -> None:
        """G-08: Phase with no prerequisites -> always passes."""
        result = check_hard_prerequisites(
            phase="brainstorm",
            existing_artifacts=[],
        )
        assert result.allowed is True
        assert result.guard_id == "G-08"

    def test_G08_check_hard_prerequisites_unknown_phase(self) -> None:
        """G-08: Unknown phase -> invalid input."""
        result = check_hard_prerequisites(
            phase="nonexistent",
            existing_artifacts=[],
        )
        assert result.allowed is False
        assert result.guard_id == "INVALID"

    # G-09: Soft PRD redirect

    def test_G09_check_prd_exists_pass_prd_present(self) -> None:
        """G-09: PRD exists -> allowed."""
        result = check_prd_exists(
            prd_path_exists=True,
            meta_has_brainstorm_source=False,
        )
        assert result.allowed is True
        assert result.guard_id == "G-09"

    def test_G09_check_prd_exists_fail_no_prd_no_brainstorm(self) -> None:
        """G-09: No PRD, no brainstorm source -> warn."""
        result = check_prd_exists(
            prd_path_exists=False,
            meta_has_brainstorm_source=False,
        )
        assert result.allowed is True  # warn, not block
        assert result.severity == Severity.warn
        assert result.guard_id == "G-09"


# ---------------------------------------------------------------------------
# Task 3.4: Branch & service functions (G-11, G-13..16)
# ---------------------------------------------------------------------------


class TestBranchValidation:
    """Tests for check_branch (G-11)."""

    def test_G11_check_branch_pass_match(self) -> None:
        """G-11: Branches match -> allowed."""
        result = check_branch(
            current_branch="feat/007",
            expected_branch="feat/007",
        )
        assert result.allowed is True
        assert result.guard_id == "G-11"
        assert result.severity == Severity.info

    def test_G11_check_branch_fail_mismatch(self) -> None:
        """G-11: Branches mismatch -> warn with switch suggestion."""
        result = check_branch(
            current_branch="main",
            expected_branch="feat/007",
        )
        assert result.allowed is True  # warn, not block
        assert result.severity == Severity.warn
        assert result.guard_id == "G-11"
        assert "feat/007" in result.reason


class TestFailOpenMcp:
    """Tests for fail_open_mcp (G-13..16)."""

    def test_G13_fail_open_mcp_brainstorm_pass(self) -> None:
        """G-13: Brainstorm service available -> info."""
        result = fail_open_mcp(service_name="brainstorm", service_available=True)
        assert result.allowed is True
        assert result.guard_id == "G-13"
        assert result.severity == Severity.info

    def test_G13_fail_open_mcp_brainstorm_fail(self) -> None:
        """G-13: Brainstorm service unavailable -> warn (fail-open)."""
        result = fail_open_mcp(service_name="brainstorm", service_available=False)
        assert result.allowed is True
        assert result.guard_id == "G-13"
        assert result.severity == Severity.warn

    def test_G14_fail_open_mcp_create_feature_pass(self) -> None:
        """G-14: Create-feature service available -> info."""
        result = fail_open_mcp(service_name="create-feature", service_available=True)
        assert result.allowed is True
        assert result.guard_id == "G-14"

    def test_G14_fail_open_mcp_create_feature_fail(self) -> None:
        """G-14: Create-feature service unavailable -> warn."""
        result = fail_open_mcp(service_name="create-feature", service_available=False)
        assert result.allowed is True
        assert result.guard_id == "G-14"
        assert result.severity == Severity.warn

    def test_G15_fail_open_mcp_create_project_pass(self) -> None:
        """G-15: Create-project service available -> info."""
        result = fail_open_mcp(service_name="create-project", service_available=True)
        assert result.allowed is True
        assert result.guard_id == "G-15"

    def test_G15_fail_open_mcp_create_project_fail(self) -> None:
        """G-15: Create-project service unavailable -> warn."""
        result = fail_open_mcp(service_name="create-project", service_available=False)
        assert result.allowed is True
        assert result.guard_id == "G-15"
        assert result.severity == Severity.warn

    def test_G16_fail_open_mcp_retrospective_pass(self) -> None:
        """G-16: Retrospective service available -> info."""
        result = fail_open_mcp(service_name="retrospective", service_available=True)
        assert result.allowed is True
        assert result.guard_id == "G-16"

    def test_G16_fail_open_mcp_retrospective_fail(self) -> None:
        """G-16: Retrospective service unavailable -> warn."""
        result = fail_open_mcp(service_name="retrospective", service_available=False)
        assert result.allowed is True
        assert result.guard_id == "G-16"
        assert result.severity == Severity.warn

    def test_fail_open_mcp_unknown_service(self) -> None:
        """Unknown service -> invalid input result."""
        result = fail_open_mcp(service_name="unknown", service_available=True)
        assert result.allowed is False
        assert result.guard_id == "INVALID"


# ---------------------------------------------------------------------------
# Task 3.5: Phase transition functions (G-17, G-18, G-22, G-23, G-25)
# ---------------------------------------------------------------------------


class TestPartialPhase:
    """Tests for check_partial_phase (G-17)."""

    def test_G17_check_partial_phase_pass_consistent(self) -> None:
        """G-17: Phase not started -> consistent (pass)."""
        result = check_partial_phase(
            phase="design",
            phase_started=False,
            phase_completed=False,
        )
        assert result.allowed is True
        assert result.guard_id == "G-17"
        assert result.severity == Severity.info

    def test_G17_check_partial_phase_fail_interrupted(self) -> None:
        """G-17: Phase started but not completed -> warn."""
        result = check_partial_phase(
            phase="design",
            phase_started=True,
            phase_completed=False,
        )
        assert result.allowed is True  # warn, not block
        assert result.severity == Severity.warn
        assert result.guard_id == "G-17"
        assert "resume" in result.reason.lower()


class TestBackwardTransition:
    """Tests for check_backward_transition (G-18)."""

    def test_G18_check_backward_transition_pass_forward(self) -> None:
        """G-18: Forward transition -> pass."""
        result = check_backward_transition(
            target_phase="design",
            last_completed_phase="specify",
        )
        assert result.allowed is True
        assert result.guard_id == "G-18"

    def test_G18_check_backward_transition_fail_backward(self) -> None:
        """G-18: Backward transition -> warn."""
        result = check_backward_transition(
            target_phase="specify",
            last_completed_phase="design",
        )
        assert result.allowed is True  # warn, not block
        assert result.severity == Severity.warn
        assert result.guard_id == "G-18"


class TestValidateTransition:
    """Tests for validate_transition (G-22)."""

    def test_G22_validate_transition_pass_sequential(self) -> None:
        """G-22: Sequential transition -> pass."""
        result = validate_transition(
            current_phase="specify",
            target_phase="design",
            completed_phases=["brainstorm", "specify"],
        )
        assert result.allowed is True
        assert result.guard_id == "G-22"

    def test_G22_validate_transition_fail_backward(self) -> None:
        """G-22: Target not ahead of current -> warn."""
        result = validate_transition(
            current_phase="design",
            target_phase="specify",
            completed_phases=["brainstorm", "specify", "design"],
        )
        assert result.allowed is True  # warn (soft-warn enforcement)
        assert result.severity == Severity.warn
        assert result.guard_id == "G-22"

    def test_G22_validate_transition_fail_skipped_phases(self) -> None:
        """G-22: Skipping incomplete phases -> warn."""
        result = validate_transition(
            current_phase="specify",
            target_phase="implement",
            completed_phases=["brainstorm", "specify"],
        )
        assert result.allowed is True  # warn (soft-warn enforcement)
        assert result.severity == Severity.warn
        assert result.guard_id == "G-22"


class TestSoftPrerequisites:
    """Tests for check_soft_prerequisites (G-23)."""

    def test_G23_check_soft_prerequisites_pass_all_completed(self) -> None:
        """G-23: All prior phases completed -> pass."""
        result = check_soft_prerequisites(
            target_phase="design",
            completed_phases=["brainstorm", "specify"],
        )
        assert result.allowed is True
        assert result.guard_id == "G-23"

    def test_G23_check_soft_prerequisites_fail_skipped(self) -> None:
        """G-23: Skipped phases -> warn."""
        result = check_soft_prerequisites(
            target_phase="design",
            completed_phases=[],
        )
        assert result.allowed is True  # warn, not block
        assert result.severity == Severity.warn
        assert result.guard_id == "G-23"
        assert "brainstorm" in result.reason


class TestGetNextPhase:
    """Tests for get_next_phase (G-25)."""

    def test_G25_get_next_phase_pass(self) -> None:
        """G-25: Valid phase -> returns next phase."""
        result = get_next_phase(last_completed_phase="specify")
        assert result.allowed is True
        assert result.guard_id == "G-25"
        assert "design" in result.reason

    def test_G25_get_next_phase_fail_end_of_sequence(self) -> None:
        """G-25: Last phase (finish) -> no next phase."""
        result = get_next_phase(last_completed_phase="finish")
        assert result.allowed is False
        assert result.guard_id == "G-25"
        assert result.severity == Severity.block


# ---------------------------------------------------------------------------
# Task 3.6: Pre-merge functions (G-27..30)
# ---------------------------------------------------------------------------


class TestPreMergeValidation:
    """Tests for pre_merge_validation (G-27/29)."""

    def test_G27_pre_merge_validation_pass(self) -> None:
        """G-27: Checks passed -> allowed."""
        result = pre_merge_validation(
            checks_passed=True,
            max_attempts=3,
            current_attempt=1,
        )
        assert result.allowed is True
        assert result.guard_id == "G-27"

    def test_G27_pre_merge_validation_fail_retry(self) -> None:
        """G-27: Checks failed, under cap -> blocked with retry."""
        result = pre_merge_validation(
            checks_passed=False,
            max_attempts=3,
            current_attempt=1,
        )
        assert result.allowed is False
        assert result.guard_id == "G-27"
        assert result.severity == Severity.block

    def test_G29_pre_merge_validation_fail_exhausted(self) -> None:
        """G-29: Checks failed, at cap -> blocked with exhausted."""
        result = pre_merge_validation(
            checks_passed=False,
            max_attempts=3,
            current_attempt=3,
        )
        assert result.allowed is False
        assert result.guard_id == "G-29"
        assert result.severity == Severity.block
        assert "exhausted" in result.reason.lower()

    def test_G29_pre_merge_validation_fail_over_cap(self) -> None:
        """G-29: Checks failed, over cap -> blocked with exhausted."""
        result = pre_merge_validation(
            checks_passed=False,
            max_attempts=3,
            current_attempt=5,
        )
        assert result.allowed is False
        assert result.guard_id == "G-29"


class TestMergeConflict:
    """Tests for check_merge_conflict (G-28/30)."""

    def test_G28_check_merge_conflict_pass(self) -> None:
        """G-28: Merge succeeded -> allowed."""
        result = check_merge_conflict(is_yolo=False, merge_succeeded=True)
        assert result.allowed is True
        assert result.guard_id == "G-28"

    def test_G28_check_merge_conflict_fail_non_yolo(self) -> None:
        """G-28: Merge failed, non-YOLO -> blocked."""
        result = check_merge_conflict(is_yolo=False, merge_succeeded=False)
        assert result.allowed is False
        assert result.guard_id == "G-28"
        assert result.severity == Severity.block

    def test_G30_check_merge_conflict_fail_yolo(self) -> None:
        """G-30: Merge failed in YOLO -> hard-stop."""
        result = check_merge_conflict(is_yolo=True, merge_succeeded=False)
        assert result.allowed is False
        assert result.guard_id == "G-30"
        assert result.severity == Severity.block
        assert "YOLO" in result.reason

    def test_G28_check_merge_conflict_pass_yolo(self) -> None:
        """G-28: Merge succeeded in YOLO -> allowed."""
        result = check_merge_conflict(is_yolo=True, merge_succeeded=True)
        assert result.allowed is True
        assert result.guard_id == "G-28"


# ---------------------------------------------------------------------------
# Task 3.7a: Brainstorm gate functions (G-31..33)
# ---------------------------------------------------------------------------


class TestBrainstormQualityGate:
    """Tests for brainstorm_quality_gate (G-32)."""

    def test_G32_brainstorm_quality_gate_pass_approved(self) -> None:
        """G-32: Reviewer approved -> allowed."""
        result = brainstorm_quality_gate(
            iteration=1,
            max_iterations=3,
            reviewer_approved=True,
        )
        assert result.allowed is True
        assert result.guard_id == "G-32"
        assert result.severity == Severity.info

    def test_G32_brainstorm_quality_gate_fail_not_approved(self) -> None:
        """G-32: Not approved, under cap -> blocked."""
        result = brainstorm_quality_gate(
            iteration=1,
            max_iterations=3,
            reviewer_approved=False,
        )
        assert result.allowed is False
        assert result.guard_id == "G-32"
        assert result.severity == Severity.block

    def test_G32_brainstorm_quality_gate_cap_reached(self) -> None:
        """G-32: Not approved but cap reached -> warn."""
        result = brainstorm_quality_gate(
            iteration=3,
            max_iterations=3,
            reviewer_approved=False,
        )
        assert result.allowed is True
        assert result.guard_id == "G-32"
        assert result.severity == Severity.warn


class TestBrainstormReadinessGate:
    """Tests for brainstorm_readiness_gate (G-31/33)."""

    def test_G31_brainstorm_readiness_pass_ready(self) -> None:
        """G-31: Approved, no blockers -> ready."""
        result = brainstorm_readiness_gate(
            iteration=1,
            max_iterations=3,
            reviewer_approved=True,
            has_blockers=False,
        )
        assert result.allowed is True
        assert result.guard_id == "G-31"
        assert result.severity == Severity.info

    def test_G33_brainstorm_readiness_fail_blockers(self) -> None:
        """G-33: Approved but blockers remain -> blocked."""
        result = brainstorm_readiness_gate(
            iteration=1,
            max_iterations=3,
            reviewer_approved=True,
            has_blockers=True,
        )
        assert result.allowed is False
        assert result.guard_id == "G-33"
        assert result.severity == Severity.block

    def test_G31_brainstorm_readiness_fail_not_ready(self) -> None:
        """G-31: Not approved, under cap -> blocked, retry."""
        result = brainstorm_readiness_gate(
            iteration=1,
            max_iterations=3,
            reviewer_approved=False,
            has_blockers=False,
        )
        assert result.allowed is False
        assert result.guard_id == "G-31"
        assert result.severity == Severity.block

    def test_G33_brainstorm_readiness_cap_reached(self) -> None:
        """G-33: Not approved, cap reached -> warn."""
        result = brainstorm_readiness_gate(
            iteration=3,
            max_iterations=3,
            reviewer_approved=False,
            has_blockers=False,
        )
        assert result.allowed is True
        assert result.guard_id == "G-33"
        assert result.severity == Severity.warn


# ---------------------------------------------------------------------------
# Task 3.7b: Review/handoff gate functions (G-34..40, G-46, G-47)
# ---------------------------------------------------------------------------


class TestReviewQualityGate:
    """Tests for review_quality_gate (G-34/36/38/40/46)."""

    def test_G34_review_quality_create_plan_pass(self) -> None:
        """G-34: create-plan review approved -> allowed."""
        result = review_quality_gate(
            phase="create-plan",
            iteration=1,
            max_iterations=5,
            reviewer_approved=True,
            has_blockers_or_warnings=False,
        )
        assert result.allowed is True
        assert result.guard_id == "G-34"

    def test_G34_review_quality_create_plan_fail(self) -> None:
        """G-34: create-plan review not approved -> blocked."""
        result = review_quality_gate(
            phase="create-plan",
            iteration=1,
            max_iterations=5,
            reviewer_approved=False,
            has_blockers_or_warnings=False,
        )
        assert result.allowed is False
        assert result.guard_id == "G-34"

    def test_G36_review_quality_create_tasks_pass(self) -> None:
        """G-36: create-tasks review approved -> allowed."""
        result = review_quality_gate(
            phase="create-tasks",
            iteration=1,
            max_iterations=5,
            reviewer_approved=True,
            has_blockers_or_warnings=False,
        )
        assert result.allowed is True
        assert result.guard_id == "G-36"

    def test_G36_review_quality_create_tasks_fail(self) -> None:
        """G-36: create-tasks review not approved -> blocked."""
        result = review_quality_gate(
            phase="create-tasks",
            iteration=2,
            max_iterations=5,
            reviewer_approved=False,
            has_blockers_or_warnings=True,
        )
        assert result.allowed is False
        assert result.guard_id == "G-36"

    def test_G38_review_quality_design_pass(self) -> None:
        """G-38: design review approved -> allowed."""
        result = review_quality_gate(
            phase="design",
            iteration=1,
            max_iterations=5,
            reviewer_approved=True,
            has_blockers_or_warnings=False,
        )
        assert result.allowed is True
        assert result.guard_id == "G-38"

    def test_G38_review_quality_design_cap_reached(self) -> None:
        """G-38: design review cap reached -> warn."""
        result = review_quality_gate(
            phase="design",
            iteration=5,
            max_iterations=5,
            reviewer_approved=False,
            has_blockers_or_warnings=True,
        )
        assert result.allowed is True
        assert result.guard_id == "G-38"
        assert result.severity == Severity.warn

    def test_G40_review_quality_implement_pass(self) -> None:
        """G-40: implement review approved -> allowed."""
        result = review_quality_gate(
            phase="implement",
            iteration=1,
            max_iterations=5,
            reviewer_approved=True,
            has_blockers_or_warnings=False,
        )
        assert result.allowed is True
        assert result.guard_id == "G-40"

    def test_G40_review_quality_implement_fail(self) -> None:
        """G-40: implement review not approved -> blocked."""
        result = review_quality_gate(
            phase="implement",
            iteration=1,
            max_iterations=5,
            reviewer_approved=False,
            has_blockers_or_warnings=False,
        )
        assert result.allowed is False
        assert result.guard_id == "G-40"

    def test_G46_review_quality_specify_pass(self) -> None:
        """G-46: specify review approved -> allowed."""
        result = review_quality_gate(
            phase="specify",
            iteration=1,
            max_iterations=5,
            reviewer_approved=True,
            has_blockers_or_warnings=False,
        )
        assert result.allowed is True
        assert result.guard_id == "G-46"

    def test_G46_review_quality_specify_fail(self) -> None:
        """G-46: specify review not approved -> blocked."""
        result = review_quality_gate(
            phase="specify",
            iteration=2,
            max_iterations=5,
            reviewer_approved=False,
            has_blockers_or_warnings=False,
        )
        assert result.allowed is False
        assert result.guard_id == "G-46"

    def test_review_quality_unknown_phase(self) -> None:
        """Unknown phase -> invalid input."""
        result = review_quality_gate(
            phase="nonexistent",
            iteration=1,
            max_iterations=5,
            reviewer_approved=True,
            has_blockers_or_warnings=False,
        )
        assert result.allowed is False
        assert result.guard_id == "INVALID"


class TestPhaseHandoffGate:
    """Tests for phase_handoff_gate (G-35/37/39/47)."""

    def test_G35_phase_handoff_create_plan_pass(self) -> None:
        """G-35: create-plan handoff approved -> allowed."""
        result = phase_handoff_gate(
            phase="create-plan",
            iteration=1,
            max_iterations=5,
            reviewer_approved=True,
            has_blockers_or_warnings=False,
        )
        assert result.allowed is True
        assert result.guard_id == "G-35"

    def test_G35_phase_handoff_create_plan_fail(self) -> None:
        """G-35: create-plan handoff not approved -> blocked."""
        result = phase_handoff_gate(
            phase="create-plan",
            iteration=1,
            max_iterations=5,
            reviewer_approved=False,
            has_blockers_or_warnings=False,
        )
        assert result.allowed is False
        assert result.guard_id == "G-35"

    def test_G37_phase_handoff_create_tasks_pass(self) -> None:
        """G-37: create-tasks handoff approved -> allowed."""
        result = phase_handoff_gate(
            phase="create-tasks",
            iteration=1,
            max_iterations=5,
            reviewer_approved=True,
            has_blockers_or_warnings=False,
        )
        assert result.allowed is True
        assert result.guard_id == "G-37"

    def test_G37_phase_handoff_create_tasks_fail(self) -> None:
        """G-37: create-tasks handoff not approved -> blocked."""
        result = phase_handoff_gate(
            phase="create-tasks",
            iteration=2,
            max_iterations=5,
            reviewer_approved=False,
            has_blockers_or_warnings=True,
        )
        assert result.allowed is False
        assert result.guard_id == "G-37"

    def test_G39_phase_handoff_design_pass(self) -> None:
        """G-39: design handoff approved -> allowed."""
        result = phase_handoff_gate(
            phase="design",
            iteration=1,
            max_iterations=5,
            reviewer_approved=True,
            has_blockers_or_warnings=False,
        )
        assert result.allowed is True
        assert result.guard_id == "G-39"

    def test_G39_phase_handoff_design_cap_reached(self) -> None:
        """G-39: design handoff cap reached -> warn."""
        result = phase_handoff_gate(
            phase="design",
            iteration=5,
            max_iterations=5,
            reviewer_approved=False,
            has_blockers_or_warnings=True,
        )
        assert result.allowed is True
        assert result.guard_id == "G-39"
        assert result.severity == Severity.warn

    def test_G47_phase_handoff_specify_pass(self) -> None:
        """G-47: specify handoff approved -> allowed."""
        result = phase_handoff_gate(
            phase="specify",
            iteration=1,
            max_iterations=5,
            reviewer_approved=True,
            has_blockers_or_warnings=False,
        )
        assert result.allowed is True
        assert result.guard_id == "G-47"

    def test_G47_phase_handoff_specify_fail(self) -> None:
        """G-47: specify handoff not approved -> blocked."""
        result = phase_handoff_gate(
            phase="specify",
            iteration=2,
            max_iterations=5,
            reviewer_approved=False,
            has_blockers_or_warnings=False,
        )
        assert result.allowed is False
        assert result.guard_id == "G-47"

    def test_phase_handoff_unknown_phase(self) -> None:
        """Unknown phase -> invalid input."""
        result = phase_handoff_gate(
            phase="nonexistent",
            iteration=1,
            max_iterations=5,
            reviewer_approved=True,
            has_blockers_or_warnings=False,
        )
        assert result.allowed is False
        assert result.guard_id == "INVALID"


# ---------------------------------------------------------------------------
# Task 3.7c: Circuit breaker (G-41)
# ---------------------------------------------------------------------------


class TestCircuitBreaker:
    """Tests for implement_circuit_breaker (G-41)."""

    def test_G41_circuit_breaker_under_cap(self) -> None:
        """G-41: Under cap -> allowed."""
        result = implement_circuit_breaker(
            is_yolo=False,
            iteration=2,
            max_iterations=5,
        )
        assert result.allowed is True
        assert result.guard_id == "G-41"
        assert result.severity == Severity.info

    def test_G41_circuit_breaker_yolo_hard_stop(self) -> None:
        """G-41: YOLO at cap -> hard-stop."""
        result = implement_circuit_breaker(
            is_yolo=True,
            iteration=5,
            max_iterations=5,
        )
        assert result.allowed is False
        assert result.guard_id == "G-41"
        assert result.severity == Severity.block
        assert "YOLO" in result.reason

    def test_G41_circuit_breaker_non_yolo_cap(self) -> None:
        """G-41: Non-YOLO at cap -> warn (user decides)."""
        result = implement_circuit_breaker(
            is_yolo=False,
            iteration=5,
            max_iterations=5,
        )
        assert result.allowed is True
        assert result.guard_id == "G-41"
        assert result.severity == Severity.warn


# ---------------------------------------------------------------------------
# Task 3.8: Status & feature functions (G-45, G-48..53, G-60)
# ---------------------------------------------------------------------------


class TestSecretaryReviewCriteria:
    """Tests for secretary_review_criteria (G-45)."""

    def test_G45_secretary_review_criteria_pass_skip(self) -> None:
        """G-45: High confidence + direct match -> skip review."""
        result = secretary_review_criteria(confidence=90.0, is_direct_match=True)
        assert result.allowed is True
        assert result.guard_id == "G-45"
        assert result.severity == Severity.info

    def test_G45_secretary_review_criteria_fail_low_confidence(self) -> None:
        """G-45: Low confidence -> review required."""
        result = secretary_review_criteria(confidence=50.0, is_direct_match=True)
        assert result.allowed is True  # warn, not block
        assert result.severity == Severity.warn
        assert result.guard_id == "G-45"


class TestActiveFeatureConflict:
    """Tests for check_active_feature_conflict (G-48)."""

    def test_G48_check_active_feature_conflict_pass_none(self) -> None:
        """G-48: No active features -> pass."""
        result = check_active_feature_conflict(active_feature_count=0)
        assert result.allowed is True
        assert result.guard_id == "G-48"

    def test_G48_check_active_feature_conflict_fail_exists(self) -> None:
        """G-48: Active features exist -> warn."""
        result = check_active_feature_conflict(active_feature_count=2)
        assert result.allowed is True  # warn, not block
        assert result.severity == Severity.warn
        assert result.guard_id == "G-48"


class TestActiveFeature:
    """Tests for check_active_feature (G-49)."""

    def test_G49_check_active_feature_pass(self) -> None:
        """G-49: Active feature exists -> pass."""
        result = check_active_feature(has_active_feature=True)
        assert result.allowed is True
        assert result.guard_id == "G-49"

    def test_G49_check_active_feature_fail(self) -> None:
        """G-49: No active feature -> warn."""
        result = check_active_feature(has_active_feature=False)
        assert result.allowed is True  # warn, not block
        assert result.severity == Severity.warn
        assert result.guard_id == "G-49"


class TestPlannedToActiveTransition:
    """Tests for planned_to_active_transition (G-50)."""

    def test_G50_planned_to_active_pass(self) -> None:
        """G-50: Planned status + branch exists -> allowed."""
        result = planned_to_active_transition(
            current_status="planned",
            branch_exists=True,
        )
        assert result.allowed is True
        assert result.guard_id == "G-50"

    def test_G50_planned_to_active_fail_wrong_status(self) -> None:
        """G-50: Not planned status -> blocked."""
        result = planned_to_active_transition(
            current_status="active",
            branch_exists=True,
        )
        assert result.allowed is False
        assert result.guard_id == "G-50"
        assert result.severity == Severity.block

    def test_G50_planned_to_active_fail_no_branch(self) -> None:
        """G-50: Planned but no branch -> blocked."""
        result = planned_to_active_transition(
            current_status="planned",
            branch_exists=False,
        )
        assert result.allowed is False
        assert result.guard_id == "G-50"
        assert result.severity == Severity.block


class TestTerminalStatus:
    """Tests for check_terminal_status (G-51)."""

    def test_G51_check_terminal_status_pass_active(self) -> None:
        """G-51: Non-terminal status (active) -> allowed."""
        result = check_terminal_status(current_status="active")
        assert result.allowed is True
        assert result.guard_id == "G-51"

    def test_G51_check_terminal_status_fail_completed(self) -> None:
        """G-51: Terminal status (completed) -> hard-blocked."""
        result = check_terminal_status(current_status="completed")
        assert result.allowed is False
        assert result.guard_id == "G-51"
        assert result.severity == Severity.block

    def test_G51_check_terminal_status_fail_abandoned(self) -> None:
        """G-51: Terminal status (abandoned) -> hard-blocked."""
        result = check_terminal_status(current_status="abandoned")
        assert result.allowed is False
        assert result.guard_id == "G-51"
        assert result.severity == Severity.block


class TestTaskCompletion:
    """Tests for check_task_completion (G-52/53)."""

    def test_G52_check_task_completion_fail_incomplete(self) -> None:
        """G-52: Incomplete tasks -> warn."""
        result = check_task_completion(incomplete_task_count=3)
        assert result.allowed is True  # warn, not block
        assert result.severity == Severity.warn
        assert result.guard_id == "G-52"

    def test_G53_check_task_completion_pass_all_done(self) -> None:
        """G-53: All tasks complete -> pass."""
        result = check_task_completion(incomplete_task_count=0)
        assert result.allowed is True
        assert result.guard_id == "G-53"
        assert result.severity == Severity.info


class TestOrchestratePrerequisite:
    """Tests for check_orchestrate_prerequisite (G-60)."""

    def test_G60_check_orchestrate_prerequisite_pass_yolo(self) -> None:
        """G-60: YOLO mode -> allowed."""
        result = check_orchestrate_prerequisite(is_yolo=True)
        assert result.allowed is True
        assert result.guard_id == "G-60"

    def test_G60_check_orchestrate_prerequisite_fail_no_yolo(self) -> None:
        """G-60: Non-YOLO -> blocked."""
        result = check_orchestrate_prerequisite(is_yolo=False)
        assert result.allowed is False
        assert result.guard_id == "G-60"
        assert result.severity == Severity.block


# ===========================================================================
# Phase 4: Public API (__init__.py) import verification tests
# ===========================================================================


class TestPublicApiImports:
    """Verify __init__.py re-exports all public symbols."""

    def test_import_key_symbols(self) -> None:
        """Core imports work: validate_transition, TransitionResult, Phase."""
        from transition_gate import validate_transition, TransitionResult, Phase

        assert callable(validate_transition)
        assert TransitionResult is not None
        assert Phase is not None

    def test_all_length_38(self) -> None:
        """__all__ contains exactly 38 entries (26 functions + 4 enums + 3 dataclasses + 5 constants)."""
        import transition_gate

        assert len(transition_gate.__all__) == 38, (
            f"Expected 38 entries in __all__, got {len(transition_gate.__all__)}"
        )

    def test_all_names_accessible(self) -> None:
        """Every name in __all__ is accessible via getattr without AttributeError."""
        import transition_gate

        for name in transition_gate.__all__:
            obj = getattr(transition_gate, name, None)
            assert obj is not None, (
                f"Name '{name}' in __all__ is not accessible on transition_gate module"
            )

    def test_all_sorted_alphabetically(self) -> None:
        """__all__ is sorted alphabetically for readability."""
        import transition_gate

        assert transition_gate.__all__ == sorted(transition_gate.__all__), (
            "__all__ is not sorted alphabetically"
        )


# ===========================================================================
# Phase 5: Integration verification
# ===========================================================================


# ---------------------------------------------------------------------------
# Task 5.1: SC-5 canonical sequence test
# ---------------------------------------------------------------------------


def test_canonical_sequence_matches_skill_md() -> None:
    """SC-5: PHASE_SEQUENCE matches the arrow-delimited sequence in SKILL.md.

    Reads SKILL.md, finds the arrow-delimited phase sequence under the
    "Phase Sequence" heading, parses phase names, and compares against
    PHASE_SEQUENCE from constants.py.
    """
    # Navigate from hooks/lib/transition_gate/ up to plugin root, then
    # into skills/workflow-state/SKILL.md
    skill_path = (
        Path(__file__).resolve().parents[3]
        / "skills"
        / "workflow-state"
        / "SKILL.md"
    )

    if not skill_path.exists():
        pytest.skip(f"SKILL.md not found at expected path: {skill_path}")

    content = skill_path.read_text()
    lines = content.splitlines()

    # Search for arrow-delimited sequence under "Phase Sequence" heading
    arrow_char = "\u2192"  # Unicode right arrow
    found_heading = False
    sequence_line: str | None = None

    for line in lines:
        # Look for the heading (## Phase Sequence)
        stripped = line.strip()
        if stripped.startswith("#") and "Phase Sequence" in stripped:
            found_heading = True
            continue

        # After finding heading, look for the arrow-delimited line
        if found_heading and arrow_char in line:
            sequence_line = line.strip()
            break

        # If we hit a new heading after finding ours, stop searching
        if found_heading and stripped.startswith("#") and "Phase Sequence" not in stripped:
            break

    if sequence_line is None:
        pytest.fail(
            "Arrow-delimited sequence not found under any expected heading "
            "in SKILL.md"
        )

    # Parse phase names from the arrow-delimited line
    skill_phases = [
        phase.strip()
        for phase in sequence_line.split(arrow_char)
        if phase.strip()
    ]

    # Compare against PHASE_SEQUENCE (use .value for str enum comparison)
    library_phases = [p.value for p in PHASE_SEQUENCE]

    assert skill_phases == library_phases, (
        f"PHASE_SEQUENCE does not match SKILL.md.\n"
        f"  SKILL.md:  {skill_phases}\n"
        f"  Library:   {library_phases}"
    )
