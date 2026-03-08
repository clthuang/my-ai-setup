# Design: Kanban Column Lifecycle Fix

## Prior Art Research

**Codebase patterns found:**
- `ENTITY_MACHINES` (workflow_state_server.py:49-86) — dict-of-dicts with `columns` sub-dict mapping phase→kanban_column for brainstorm/backlog. Used by `_process_transition_entity_phase()` which does atomic UPDATE of both `workflow_phase` and `kanban_column` in a single SQL statement.
- `STATUS_TO_KANBAN` (backfill.py:35-40) — status-based mapping (`planned→backlog`, `active→wip`, `completed→completed`, `abandoned→completed`). Used during initial DB population.
- `db.update_workflow_phase()` (database.py:1330) — accepts `kanban_column` as optional kwarg with `_UNSET` sentinel. Already supports partial updates.
- `db.create_workflow_phase()` (database.py:1248) — accepts `kanban_column` with default `"backlog"`. The engine's degraded-mode backfill (engine.py:590) never passes it.

**Design principle:** Follow the existing `ENTITY_MACHINES.columns` pattern — a simple dict mapping phase→kanban_column, with the same atomic update approach.

## Architecture Overview

### Approach: Phase-Based Kanban Derivation

The fix adds a feature phase-to-kanban mapping and injects kanban_column updates into the 4 code paths that change feature workflow state:

```
FEATURE_PHASE_TO_KANBAN (shared constant)
         │
    ┌────┴────────────────────────────┐
    │                                 │
    ▼                                 ▼
workflow_state_server.py          reconciliation.py
    │                                 │
    ├─ _process_transition_phase()    ├─ _check_single_feature()
    │    → db.update_workflow_phase   │    → detect kanban drift
    │      (kanban_column=...)        │
    │                                 ├─ _reconcile_single_feature()
    ├─ _process_complete_phase()      │    → db.update_workflow_phase
    │    → db.update_workflow_phase   │      (kanban_column=...)
    │      (kanban_column=...)        │
    │                                 └───────────────────────────
    └─ engine.py (degraded backfill)
         → db.create_workflow_phase
           (kanban_column=...)
```

### Component Changes

**1. New file: `plugins/iflow/hooks/lib/workflow_engine/constants.py`**

Single constant shared between MCP server and reconciliation:

```python
FEATURE_PHASE_TO_KANBAN: dict[str, str] = {
    "brainstorm": "backlog",
    "specify": "backlog",
    "design": "prioritised",
    "create-plan": "prioritised",
    "create-tasks": "prioritised",
    "implement": "wip",
    "finish": "documenting",
}
```

`"finish"` maps to `"documenting"` (active finish phase). The terminal `"completed"` kanban value is derived conditionally: when `phase == "finish"` AND the feature is fully completed (R3 logic).

**2. `workflow_state_server.py` — 3 function changes**

*a. `_process_transition_phase()` (line ~503):*
After `db.update_entity()` call, add kanban update for features:
```python
if feature_type_id.startswith("feature:"):
    from workflow_engine.constants import FEATURE_PHASE_TO_KANBAN
    kanban = FEATURE_PHASE_TO_KANBAN.get(target_phase)
    if kanban:
        db.update_workflow_phase(feature_type_id, kanban_column=kanban)
```

*b. `_process_complete_phase()` (line ~578):*
After `db.update_entity()` call, add kanban update for features:
```python
if feature_type_id.startswith("feature:"):
    from workflow_engine.constants import FEATURE_PHASE_TO_KANBAN
    if phase == "finish":
        kanban = "completed"
    else:
        kanban = FEATURE_PHASE_TO_KANBAN.get(state.current_phase)
    if kanban:
        db.update_workflow_phase(feature_type_id, kanban_column=kanban)
```

`state` is the return value of `engine.complete_phase()` (line 545) — `state.current_phase` is the phase the feature advanced INTO.

*c. `_process_init_feature_state()` (line ~726):*
No direct change needed here — this function doesn't call `create_workflow_phase`. The workflow_phases row is created lazily by `engine.py`'s hydration path when the engine first accesses the feature state. The kanban fix is applied in engine.py (change 3 below).

**3. `engine.py` — degraded-mode backfill (line ~590)**

Pass `kanban_column` to `create_workflow_phase`:
```python
from workflow_engine.constants import FEATURE_PHASE_TO_KANBAN

kanban = FEATURE_PHASE_TO_KANBAN.get(state.current_phase, "backlog")
self.db.create_workflow_phase(
    feature_type_id,
    kanban_column=kanban,
    workflow_phase=state.current_phase,
    last_completed_phase=state.last_completed_phase,
    mode=state.mode,
)
```

**4. `reconciliation.py` — 2 function changes**

Shared helper for kanban derivation:
```python
from .constants import FEATURE_PHASE_TO_KANBAN

def _derive_expected_kanban(workflow_phase: str | None, last_completed_phase: str | None) -> str | None:
    """Derive expected kanban_column from workflow state."""
    if workflow_phase is None:
        return None
    if workflow_phase == "finish" and last_completed_phase == "finish":
        return "completed"
    return FEATURE_PHASE_TO_KANBAN.get(workflow_phase)
```

*a. `_check_single_feature()` (line ~236):*
After existing mismatch checks, add:
```python
expected_kanban = _derive_expected_kanban(
    state.current_phase, state.last_completed_phase
)
if expected_kanban is not None and expected_kanban != row["kanban_column"]:
    mismatches.append(WorkflowMismatch(
        field="kanban_column",
        meta_json_value=expected_kanban,
        db_value=row["kanban_column"],
    ))
```

*b. `_reconcile_single_feature()` (line ~296):*
Add kanban_column to the update call:
```python
expected_kanban = _derive_expected_kanban(
    meta["workflow_phase"], meta["last_completed_phase"]
)
db.update_workflow_phase(
    feature_type_id,
    workflow_phase=meta["workflow_phase"],
    last_completed_phase=meta["last_completed_phase"],
    mode=meta["mode"],
    kanban_column=expected_kanban,  # NEW
)
```

**5. Data remediation: `scripts/fix_kanban_columns.py`**

One-time script:
```python
STATUS_TO_KANBAN = {
    "planned": "backlog",
    "active": "wip",
    "completed": "completed",
    "abandoned": "completed",
}

UPDATE wp
SET kanban_column = CASE e.status
    WHEN 'planned' THEN 'backlog'
    WHEN 'active' THEN 'wip'
    WHEN 'completed' THEN 'completed'
    WHEN 'abandoned' THEN 'completed'
END
FROM entities e
WHERE wp.type_id = e.type_id
AND wp.type_id LIKE 'feature:%'
```

Idempotent — safe to run multiple times.

## Interface Design

### New Constant

```python
# plugins/iflow/hooks/lib/workflow_engine/constants.py

FEATURE_PHASE_TO_KANBAN: dict[str, str] = {
    "brainstorm": "backlog",
    "specify": "backlog",
    "design": "prioritised",
    "create-plan": "prioritised",
    "create-tasks": "prioritised",
    "implement": "wip",
    "finish": "documenting",
}
```

### New Helper

```python
# plugins/iflow/hooks/lib/workflow_engine/reconciliation.py

def _derive_expected_kanban(
    workflow_phase: str | None,
    last_completed_phase: str | None,
) -> str | None:
    """Derive expected kanban_column from workflow state.

    Returns None if phase is None (skip comparison).
    Returns "completed" for terminal finish state.
    Otherwise looks up FEATURE_PHASE_TO_KANBAN.
    """
    if workflow_phase is None:
        return None
    if workflow_phase == "finish" and last_completed_phase == "finish":
        return "completed"
    return FEATURE_PHASE_TO_KANBAN.get(workflow_phase)
```

### Modified Function Signatures

No signature changes. All modifications add logic within existing function bodies using existing parameters. The `db.update_workflow_phase()` already accepts `kanban_column` as an optional kwarg.

### Data Flow

```
Feature created (init_feature_state)
  └→ engine hydration → create_workflow_phase(kanban_column=FEATURE_PHASE_TO_KANBAN[phase])

Feature transitions (transition_phase MCP tool)
  └→ _process_transition_phase → db.update_workflow_phase(kanban_column=FEATURE_PHASE_TO_KANBAN[target])

Phase completed (complete_phase MCP tool)
  └→ _process_complete_phase → db.update_workflow_phase(kanban_column="completed" | FEATURE_PHASE_TO_KANBAN[next])

Drift detected (reconcile_check MCP tool)
  └→ _check_single_feature → _derive_expected_kanban() → compare vs row["kanban_column"]

Drift fixed (reconcile_apply MCP tool)
  └→ _reconcile_single_feature → db.update_workflow_phase(kanban_column=_derive_expected_kanban())
```

## Technical Decisions

| Decision | Choice | Rationale |
|---|---|---|
| Constant location | `workflow_engine/constants.py` | Avoids reconciliation.py importing from MCP server (dependency inversion). Both consumers import from workflow_engine package. |
| Finish dual mapping | Dict maps `finish→documenting`; code handles `finish+completed→completed` | Simple dict can't have two values for same key. Conditional logic is 2 lines in each consumer. |
| Import style | Module-level import in constants.py; function-level or module-level in consumers | Standard Python import. No circular dependency risk. |
| Data remediation | Standalone script | One-time operation. Keeps backfill.py focused on initial population. |
| Guard condition | `feature_type_id.startswith("feature:")` | Matches existing pattern in codebase. Non-feature entities use ENTITY_MACHINES path. |

## Risks

| Risk | Likelihood | Impact | Mitigation |
|---|---|---|---|
| Feature transition updates kanban but fails mid-transaction | Low | Medium — kanban out of sync | Both `update_entity` and `update_workflow_phase` use same SQLite connection (implicit transaction). Reconciliation catches any drift. |
| Unknown phase in FEATURE_PHASE_TO_KANBAN lookup | Very Low | Low — kanban unchanged | `.get()` returns None, code skips update with log warning. |
| Reconciliation derives wrong expected kanban | Low | Medium — overwrites correct value | `_derive_expected_kanban` logic is simple and tested. Same mapping used everywhere. |
