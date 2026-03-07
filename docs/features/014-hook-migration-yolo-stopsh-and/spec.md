# Specification: Hook Migration — yolo-stop.sh

## Overview

Replace the hardcoded `phase_map` dictionary in `yolo-stop.sh` with the canonical `PHASE_SEQUENCE` from the transition gate constants module. The hook currently duplicates workflow phase ordering inline (lines 173-183) — this creates a maintenance burden and drift risk when the phase sequence changes. The state engine already defines the authoritative phase sequence in `transition_gate.constants.PHASE_SEQUENCE`.

Additionally, replace the inline `.meta.json` parsing for feature state (status, lastCompletedPhase) with a direct call to the workflow state engine's `get_state()` method, which already implements graceful degradation (falls back to `.meta.json` if the database is unavailable).

**PRD deviation:** The project PRD (FR-13) describes this as "yolo-stop.sh hook uses state engine MCP tool." This spec uses direct Python library imports instead of MCP protocol calls. Hooks execute as bash subprocesses with no MCP client available — they access engine functionality via `PYTHONPATH`-resolved library imports. This is consistent with how all other hooks access shared modules (see Out of Scope).

## Functional Requirements

### FR-1: Replace `phase_map` with `PHASE_SEQUENCE`-derived next-phase lookup

The `yolo-stop.sh` hook must derive the next phase from `transition_gate.constants.PHASE_SEQUENCE` instead of the hardcoded `phase_map` dict. The Python snippet on lines 172-184 must be replaced with an import from the transition gate module.

**Current behavior (lines 172-184):**
```python
phase_map = {
    'null': 'specify',
    'brainstorm': 'specify',
    'specify': 'design',
    'design': 'create-plan',
    'create-plan': 'create-tasks',
    'create-tasks': 'implement',
    'implement': 'finish',
}
last = '${LAST_COMPLETED_PHASE}'
print(phase_map.get(last, ''))
```

**Target behavior — algorithm:**

1. Import `PHASE_SEQUENCE` from `transition_gate.constants`.
2. Build `_PHASE_VALUES = tuple(p.value for p in PHASE_SEQUENCE)` — the ordered list of phase string values: `("brainstorm", "specify", "design", "create-plan", "create-tasks", "implement", "finish")`.
3. Given `last_completed_phase` (string from `.meta.json` or engine state):
   - If `last_completed_phase` is `"null"` or empty string: next phase = `PHASE_SEQUENCE[1].value` (i.e., `"specify"` — the first command phase, skipping `"brainstorm"`).
   - Otherwise: find `last_completed_phase` in `_PHASE_VALUES`. If found at index `i` and `i < len(_PHASE_VALUES) - 1`, next phase = `_PHASE_VALUES[i + 1]`. If at the last index (finish) or not found, next phase = empty string (no next phase).

This preserves the current mappings: `null` → `specify`, `brainstorm` → `specify`, `specify` → `design`, etc. The `brainstorm` → `specify` case is handled naturally by the sequence (brainstorm is at index 0, specify at index 1).

### FR-2: Replace inline `.meta.json` feature state reading with engine `get_state()`

The hook currently:
1. Scans `{artifacts_root}/features/*/.meta.json` for `status="active"` (lines 75-107)
2. Reads feature state by parsing `.meta.json` directly (lines 110-130)
3. Checks `lastCompletedPhase` and `status` fields (lines 132-135)

Replace steps 2-3 with a call to `WorkflowStateEngine.get_state()`, which:
- Reads from the database first
- Falls back to `.meta.json` parsing if database is unavailable (graceful degradation)
- Returns a `FeatureWorkflowState` object with `current_phase`, `last_completed_phase`, `completed_phases`, `mode`, and `source` fields

**Engine construction:** To use `WorkflowStateEngine`, the hook must construct an `EntityDatabase` instance first:
1. Resolve `db_path` from environment variable `ENTITY_DB_PATH`, defaulting to `~/.claude/iflow/entities/entities.db`.
2. Wrap `EntityDatabase(db_path)` construction in a try/except. The constructor performs `sqlite3.connect()` + `_migrate()` eagerly — this can throw `sqlite3.Error` or `OSError` if the path is invalid, the directory doesn't exist, or permissions are wrong.
3. If construction succeeds: create `WorkflowStateEngine(db, artifacts_root)` and call `engine.get_state(feature_type_id)`.
4. If construction fails: fall back to the current inline `.meta.json` parsing for feature state (same behavior as today). This is a hook-level graceful degradation that complements the engine's internal DB → `.meta.json` fallback.

**Note:** Step 1 (active feature scanning) must remain as-is because `get_state()` requires a `feature_type_id` — the hook must still discover which feature is active first. The engine's `list_by_status("active")` could replace this, but that requires database availability (no graceful degradation for listing). Since the hook runs in all environments (including when DB is down), retain the filesystem scan for discovery.

### FR-3: Resolve PYTHONPATH for transition gate imports

The hook runs as a standalone bash script. It must set `PYTHONPATH` to include the `hooks/lib/` directory so that `transition_gate` and `workflow_engine` modules are importable. Use the existing plugin root detection pattern from `common.sh`.

**Path resolution:** The hook's `SCRIPT_DIR` already points to the hooks directory. `PYTHONPATH` should be set to `${SCRIPT_DIR}/lib` before invoking Python.

### FR-4: Preserve all existing controls

All existing YOLO controls must be preserved with identical behavior:
- YOLO mode check (lines 20-23)
- YOLO paused check (lines 25-29)
- Usage limit check (lines 32-69)
- Active feature scanning (lines 75-107) — filesystem-based, retained per FR-2 note
- Completion check: `status == "completed"` or feature workflow is at terminal phase (lines 132-135)
- Stuck detection (lines 148-154)
- Max iterations / stop count (lines 159-169)
- Block message format (lines 191-199)

### FR-5: Update hook tests

Existing tests in `hooks/tests/test-hooks.sh` that exercise `yolo-stop.sh` must continue to pass. No new test infrastructure is needed — the existing test cases cover the phase transition logic via `.meta.json` fixtures.

## Non-Functional Requirements

### NFR-1: No new dependencies

The hook must not introduce any new Python packages. `transition_gate` and `workflow_engine` are already available in the hooks/lib directory.

### NFR-2: Performance

The hook must complete within 500ms. Adding the engine import adds module loading overhead — acceptable as long as the 500ms budget is met.

### NFR-3: Graceful degradation

Two levels of fallback:
1. **Engine-level:** If the database is unreachable after `EntityDatabase` is constructed, `WorkflowStateEngine.get_state()` internally falls back to `.meta.json` parsing.
2. **Hook-level:** If `EntityDatabase` construction itself fails (invalid path, permissions, missing directory), or if the `transition_gate`/`workflow_engine` imports fail, the hook falls back to the current inline `phase_map` dictionary and `.meta.json` parsing. This is a safety net — not a long-term design.

### NFR-4: Stderr suppression

All Python subprocess calls must continue to suppress stderr (`2>/dev/null`) to prevent corrupting JSON output, per the hook development guide. This also suppresses the engine's diagnostic stderr messages (e.g., "DB unhealthy, falling back to .meta.json") which is acceptable — those messages are informational only.

## Acceptance Criteria

- AC-1: `yolo-stop.sh` no longer contains a hardcoded `phase_map` dictionary in its primary code path (the fallback path may retain it per NFR-3)
- AC-2: Next-phase lookup uses `transition_gate.constants.PHASE_SEQUENCE` as the source of truth
- AC-3: Given a feature with `lastCompletedPhase="specify"`, when the hook runs, it produces `"Invoke /iflow:design"` in the block reason — identical to current behavior
- AC-4: Given a feature with `lastCompletedPhase=null`, when the hook runs, it produces `"Invoke /iflow:specify"` in the block reason — identical to current behavior
- AC-5: Given a feature with `lastCompletedPhase="finish"` or `status="completed"`, the hook exits cleanly (no block)
- AC-6: All existing tests in `test-hooks.sh` pass without modification
- AC-7: If `transition_gate` import fails or `EntityDatabase` construction fails, the hook falls back to the inline `phase_map` dictionary and direct `.meta.json` parsing (does not crash or produce invalid JSON)
- AC-8: When `EntityDatabase` is constructable, `WorkflowStateEngine.get_state()` is called to retrieve feature state instead of inline `.meta.json` parsing. Existing tests exercise the `.meta.json` fallback path inherently (no database present in test environment).
- AC-9: PYTHONPATH is set correctly to resolve `transition_gate` and `workflow_engine` imports

## Out of Scope

- Migrating `yolo-guard.sh` (PreToolUse hook) — separate feature or follow-up
- Migrating `session-start.sh` `.meta.json` parsing — separate concern
- Adding MCP client calls from bash hooks — hooks use Python library imports, not MCP protocol
- Changing the block message format
- Adding new test cases (existing coverage is sufficient for this migration)

## Technical Notes

- The `PHASE_SEQUENCE` constant is a tuple of `Phase` enum values. Each `Phase` has a `.value` attribute that returns the string name (e.g., `"specify"`, `"design"`). The `create_plan` enum member has value `"create-plan"` (hyphenated).
- `PHASE_SEQUENCE[0]` is `Phase.brainstorm`. `PHASE_SEQUENCE[1]` is `Phase.specify`. The null → specify mapping uses index 1 explicitly to skip brainstorm.
- The `WorkflowStateEngine` constructor requires `db: EntityDatabase` and `artifacts_root: str`. The constructor itself does no I/O — the risk is in `EntityDatabase` construction which does eager `sqlite3.connect()` + `_migrate()`.
- The `EntityDatabase` default path is `~/.claude/iflow/entities/entities.db`, overridable via `ENTITY_DB_PATH` environment variable.
- `WorkflowStateEngine.get_state()` writes diagnostic messages to stderr (e.g., "DB unhealthy, falling back to .meta.json"). These are suppressed by the hook's `2>/dev/null` stderr redirection (NFR-4).
- The engine's `get_state()` method accepts `feature_type_id` in format `"feature:{id}-{slug}"`.
