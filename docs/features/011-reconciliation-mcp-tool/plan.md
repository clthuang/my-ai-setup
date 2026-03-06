# Plan: Reconciliation MCP Tool

## Plan-Phase Decision Resolution

### Handoff Review Carry-Over Items

**Item 1: ReconcileAction 'created' action vs spec R2 AC-8 test assertion**
- Decision: Tests for AC-8 (meta_json_only → create row) assert `action="created"`, not `action="reconciled"`. This is the design's intentional extension over spec R2 to differentiate updates from creates. Test comments reference the AC-8 → "created" mapping documented in design I1.

**Item 2: healthy flag error-count semantics**
- Decision: `error` status in either dimension sets `healthy=False`. This is the safe default — a parse error may mask real drift. Implementer must follow the unified zero-check pattern from design I4: healthy = every count except `in_sync` equals 0 in BOTH workflow and frontmatter dimensions. No special-casing for "error might still be in sync".

---

## Implementation Order

### Phase 1: Core Dataclasses and Helpers (No Dependencies)

Items in this phase have zero interdependencies and can be implemented in parallel.

**1.1 — Dataclasses (`reconciliation.py` — I1)**
- File: `plugins/iflow/hooks/lib/workflow_engine/reconciliation.py` (NEW)
- File: `plugins/iflow/hooks/lib/workflow_engine/test_reconciliation.py` (NEW — created here as TDD test file, extended incrementally through Phases 1-3)
- Create module with frozen dataclasses: `WorkflowMismatch`, `WorkflowDriftReport`, `WorkflowDriftResult`, `ReconcileAction`, `ReconciliationResult`
- Add imports: `from dataclasses import dataclass, field`
- Why first: All other components depend on these types; zero external dependencies
- Tests (in `test_reconciliation.py`): construction, frozen enforcement, field access, tuple fields

**1.2 — Phase comparison helpers (`reconciliation.py` — I3)**
- File: `plugins/iflow/hooks/lib/workflow_engine/reconciliation.py`
- Implement `_phase_index(phase)` → ordinal from `PHASE_SEQUENCE` or -1
- Implement `_compare_phases(meta_last, meta_current, db_last, db_current)` → status string
- Import: `from transition_gate.constants import PHASE_SEQUENCE`
- Derive `_PHASE_VALUES = tuple(p.value for p in PHASE_SEQUENCE)` at module level
- Why this order: Phase comparison is foundational for drift detection (Phase 2)
- Tests (in `test_reconciliation.py`): known phases → correct indices; None → -1; unknown phase → -1; all 8 spec R8 comparison steps (meta_json_ahead, db_ahead, in_sync, None-vs-non-None, both-None fallthrough to workflow_phase, terminal phase edge cases)

**1.3 — Path-traversal validation (`workflow_state_server.py` — I7)**
- File: `plugins/iflow/mcp/workflow_state_server.py`
- Add module-level helper `_validate_feature_type_id(feature_type_id, artifacts_root) -> str`
- Logic: split on ':', ValueError if no colon; extract slug; realpath resolve; verify resolved path starts with `realpath(artifacts_root) + os.sep` (matches engine's `root + os.sep` pattern to prevent prefix collisions like `/docs/features` matching `/docs/features-extra`); return slug
- Used by all three `_process_reconcile_*` that accept `feature_type_id` (module-level helper)
- Note: This deliberately duplicates validation that the engine layer also performs. The MCP boundary validation is intentional defense-in-depth — untrusted input from MCP callers is validated before reaching engine internals. Both layers use realpath-based defense.
- Why this order: Parallel with 1.1/1.2 — no cross-dependency; needed by Phase 5 processing functions
- Tests (in `test_workflow_state_server.py`): valid `"feature:010-slug"` → returns slug; no colon → ValueError; `".."` in slug → ValueError; null bytes → ValueError; symlink traversal → ValueError; prefix collision (slug that is a prefix of another directory) → ValueError

### Phase 2: Drift Detection (Depends on Phase 1)

**2.1 — Single-feature meta reader (`reconciliation.py` — I3)**
- File: `plugins/iflow/hooks/lib/workflow_engine/reconciliation.py`
- Depends on: 1.2 (phase helpers)
- Implement `_read_single_meta_json(engine, artifacts_root, feature_type_id)` → `dict | None`
- Uses `engine._extract_slug()` for path construction, reads/parses JSON
- Returns None on missing file or parse error
- Why this order: Needed by 2.2 single-feature check; no dependency on 1.1 dataclasses
- Tests (in `test_reconciliation.py`): valid file → dict; missing file → None; corrupt JSON → None

**2.2 — Single-feature drift check (`reconciliation.py` — I3)**
- File: `plugins/iflow/hooks/lib/workflow_engine/reconciliation.py`
- Depends on: 1.1 (dataclasses), 1.2 (phase comparison), 2.1 (meta reader)
- Implement `_check_single_feature(engine, db, feature_type_id, meta)` → `WorkflowDriftReport`
- Derives state from meta via `engine._derive_state_from_meta(meta, feature_type_id)`
- **None guard:** If `_derive_state_from_meta()` returns None (corrupt/unparseable meta), return `WorkflowDriftReport` with `status="error"`, `message="Failed to derive state from .meta.json"`
- Reads DB via `db.get_workflow_phase(feature_type_id)`
- Field name mapping: `state.current_phase` → `workflow_phase`, `state.last_completed_phase` → `last_completed_phase`
- Builds `meta_json` and `db` dicts for output, detects mismatches including mode
- Mode mismatch: reported in `mismatches` but does NOT affect `status` (status determined solely by phase comparison)
- Why this order: Builds on 2.1 meta reader; required by 2.3 public API
- Tests (in `test_reconciliation.py`): in_sync (all fields match); meta_json_ahead; db_ahead; db_only (no meta); mode mismatch with phase sync → status still "in_sync" but mismatch present; `_derive_state_from_meta` returns None → status="error"; explicitly verify output dict key is `workflow_phase` (not `current_phase`) from field name mapping

**2.3 — Public drift detection (`reconciliation.py` — I2)**
- File: `plugins/iflow/hooks/lib/workflow_engine/reconciliation.py`
- Depends on: 2.1, 2.2
- Implement `check_workflow_drift(engine, db, artifacts_root, feature_type_id=None)` → `WorkflowDriftResult`
- Single-feature path: `_read_single_meta_json()` → if None, check DB for row via `db.get_workflow_phase(feature_type_id)` → row exists: `db_only`, no row: `error` (feature_not_found)
- Bulk path: `engine._iter_meta_jsons()` → `_check_single_feature()` per feature; detect `db_only` features by: (1) call `db.list_workflow_phases()`, (2) extract `type_id` field from each returned dict, (3) filter to entries where `type_id.startswith("feature:")` (exclude non-feature rows), (4) set-difference against meta-derived type_ids → remaining are `db_only` features
- Summary aggregation: count features by status
- Never raises — all exceptions caught → `status="error"` per feature
- Why this order: Public API entry point for drift detection; required by Phase 3 reconciliation
- Tests (in `test_reconciliation.py`): single feature all statuses (AC-1 through AC-4); bulk scan multiple features (AC-5); exception handling → error status; summary counts correct; db_only detection via list_workflow_phases set difference (filtered to `feature:` type_ids only); non-feature type_ids in DB excluded from db_only detection

### Phase 3: Reconciliation Apply (Depends on Phase 2)

**3.1 — Single-feature reconcile (`reconciliation.py` — I3)**
- File: `plugins/iflow/hooks/lib/workflow_engine/reconciliation.py`
- Depends on: 2.2 (single feature check)
- Implement `_reconcile_single_feature(engine, db, report, dry_run)` → `ReconcileAction`
- Note: `report` (a `WorkflowDriftReport`) contains all needed data — `report.meta_json` dict has the derived field values, `report.feature_type_id` identifies the entity. No separate `meta` parameter needed.
- **Defensive guard:** If `report.status == "meta_json_only"` and `report.meta_json is None`, return `action="error"`, message "meta_json_only status but no meta_json data available" (should not happen if drift detection is correct, but prevents KeyError on corrupt report)
- Status-based branching (mutually exclusive):
  - `meta_json_ahead` → `db.update_workflow_phase()` with `workflow_phase`, `last_completed_phase`, `mode`; `kanban_column` left unchanged via `_UNSET` sentinel; `action="reconciled"`. **Race condition:** catch ALL `ValueError` from `db.update_workflow_phase()` uniformly (covers row-deleted, constraint violation, or any other DB-level ValueError) → `action="error"`, message includes original ValueError text
  - `meta_json_only` → entity-existence check via `db.get_entity(report.feature_type_id)`:
    - Entity found → `db.create_workflow_phase()` using fields from `report.meta_json` dict: `workflow_phase=report.meta_json["workflow_phase"]`, `last_completed_phase=report.meta_json["last_completed_phase"]`, `mode=report.meta_json["mode"]`; `kanban_column` uses DB default; `action="created"` (design enhancement, AC-8 mapping). **Race condition:** catch ALL `ValueError` from `db.create_workflow_phase()` uniformly (covers duplicate row, entity-deleted-between-get-and-create, constraint violation) → `action="error"`, message includes original ValueError text
    - Entity not found → `action="error"`, message "Entity not found in DB"
  - `in_sync`, `db_ahead` → `action="skipped"`
  - `db_only` → `action="skipped"`, message "No .meta.json to reconcile from"
  - `error` → `action="error"`, propagate message
- `dry_run=True` → compute changes but skip DB writes
- Direction hardcoded as `"meta_json_to_db"` in output
- Why this order: Core reconciliation logic; requires drift reports from Phase 2
- Tests (in `test_reconciliation.py`): meta_json_ahead → update (AC-6); in_sync → skip (AC-7); meta_json_only + entity exists → create (AC-8); meta_json_only + no entity → error; meta_json_only + meta_json is None → error; db_ahead → skip; dry_run → no DB writes (AC-9); idempotency (AC-10); ValueError from update_workflow_phase → action="error"; ValueError from create_workflow_phase → action="error" (covers duplicate row AND entity-deleted races)

**3.2 — Public reconciliation (`reconciliation.py` — I2)**
- File: `plugins/iflow/hooks/lib/workflow_engine/reconciliation.py`
- Depends on: 2.3 (drift check), 3.1 (single reconcile)
- Implement `apply_workflow_reconciliation(engine, db, artifacts_root, feature_type_id=None, dry_run=False)` → `ReconciliationResult`
- Calls `check_workflow_drift()` internally, then `_reconcile_single_feature(engine, db, report, dry_run)` per feature
- Summary aggregation: count by action type (reconciled, created, skipped, error); `dry_run` count
- Never raises
- Why this order: Public API combining drift check + reconciliation; last piece of pure logic before MCP adapter
- Tests (in `test_reconciliation.py`): bulk reconcile multiple features; dry_run preview (AC-9); idempotency second run all skipped (AC-10)

### Phase 4: Serialization Helpers (Depends on Phase 1)

Can be implemented in parallel with Phases 2-3 since they only depend on dataclass definitions.

**4.1 — Workflow dataclass serializers (`workflow_state_server.py` — I9)**
- File: `plugins/iflow/mcp/workflow_state_server.py`
- Depends on: 1.1 (dataclasses)
- Implement `_serialize_workflow_drift_report(report)` → dict
- Implement `_serialize_reconcile_action(action)` → dict
- Serialization note: `action.changes` uses `WorkflowMismatch` but serialized as `old_value=c.db_value`, `new_value=c.meta_json_value` (design I9 convention for meta_json_to_db direction)
- Why this order: Only depends on 1.1 dataclass definitions; can be developed parallel with Phases 2-3
- Tests (in `test_workflow_state_server.py`): round-trip serialization; empty mismatches/changes; None values

**4.2 — Frontmatter DriftReport serializer (`workflow_state_server.py` — I8)**
- File: `plugins/iflow/mcp/workflow_state_server.py`
- Depends on: existing `DriftReport`/`FieldMismatch` from `frontmatter_sync`
- Implement `_serialize_drift_report(report)` → dict
- Why this order: Independent of Phases 2-3; only needs existing frontmatter_sync types
- Tests (in `test_workflow_state_server.py`): with mismatches; empty mismatches; all status values

### Phase 5: Processing Functions and MCP Adapter Layer (Depends on Phases 2-4)

**5.1 — `_process_reconcile_check` (`workflow_state_server.py` — I4)**
- File: `plugins/iflow/mcp/workflow_state_server.py`
- Depends on: 1.3 (validation), 2.3 (drift check), 4.1 (serializers)
- Decorated with `@_with_error_handling` and `@_catch_value_error`
- If `feature_type_id` provided: call `_validate_feature_type_id()` FIRST, then delegate to `check_workflow_drift()`
- Serialize result to JSON string
- Why this order: First processing function; simplest (check-only, no write side effects)
- Tests (in `test_workflow_state_server.py`): single feature → JSON with drift report; bulk → JSON with summary; validation error → structured error (AC-18)

**5.2 — `_process_reconcile_apply` (`workflow_state_server.py` — I4)**
- File: `plugins/iflow/mcp/workflow_state_server.py`
- Depends on: 1.3 (validation), 3.2 (reconciliation), 4.1 (serializers)
- Decorated with `@_with_error_handling` and `@_catch_value_error`
- Validates `direction` against `_SUPPORTED_DIRECTIONS = frozenset({"meta_json_to_db"})` → `_make_error("invalid_transition", ...)` for unsupported (AC-17)
- If `feature_type_id` provided: call `_validate_feature_type_id()` FIRST
- Delegate to `apply_workflow_reconciliation()`
- Why this order: Depends on 5.1 pattern; adds direction validation and write path
- Tests (in `test_workflow_state_server.py`): reconcile → JSON with actions; dry_run; invalid direction → error (AC-17); validation error (AC-18)

**5.3 — `_process_reconcile_frontmatter` (`workflow_state_server.py` — I4)**
- File: `plugins/iflow/mcp/workflow_state_server.py`
- Depends on: 1.3 (validation), 4.2 (frontmatter serializer)
- Decorated with `@_with_error_handling` and `@_catch_value_error`
- If `feature_type_id` provided: call `_validate_feature_type_id()` FIRST; extract slug; construct directory path; iterate `ARTIFACT_BASENAME_MAP` files; call `detect_drift(db, filepath, type_id=feature_type_id)` per existing file
- If `feature_type_id` omitted: call `scan_all(db, artifacts_root)`
- Non-existent feature directory → empty reports list, zero counts
- Serialize results to JSON string
- New imports: `from entity_registry.frontmatter_sync import detect_drift, scan_all, DriftReport, FieldMismatch, ARTIFACT_BASENAME_MAP`
- Why this order: Pass-through to frontmatter_sync; different import set from 5.1/5.2
- Tests (in `test_workflow_state_server.py`): single feature with valid frontmatter (AC-11); no frontmatter (AC-12); bulk scan (AC-13); non-existent directory → empty; validation error (AC-18)

**5.4 — `_process_reconcile_status` (`workflow_state_server.py` — I4)**
- File: `plugins/iflow/mcp/workflow_state_server.py`
- Depends on: 2.3 (drift check), 4.1 + 4.2 (both serializers)
- Decorated with `@_with_error_handling` only (no `_catch_value_error` — no feature_type_id param)
- Delegates directly to `check_workflow_drift()` and `scan_all()` (not via `_process_*` wrappers to avoid double-serialization)
- Computes `healthy` flag: True when BOTH dimensions have all counts except `in_sync` equal to 0
- `total_features_checked` = len(workflow features), `total_files_checked` = len(frontmatter reports)
- **Partial failure behavior:** All-or-nothing within `@_with_error_handling`. If either `check_workflow_drift()` or `scan_all()` raises an unexpected exception, the decorator catches it and returns a structured error. `check_workflow_drift()` is designed never-raise. `scan_all()` delegates to `db.list_entities()` which could raise `sqlite3.Error` on DB corruption — this is an accepted trade-off: DB corruption is a system-level failure that should surface as an error, not be silently swallowed. No per-dimension try/except — partial results (one dimension succeeds, the other fails) would be misleading since `healthy` requires both dimensions.
- Why this order: Final processing function; depends on both serializer sets + drift detection
- Tests (in `test_workflow_state_server.py`): all in sync → healthy=true (AC-14); any drift → healthy=false (AC-15); error status in either dimension → healthy=false; scan_all raises sqlite3.Error → decorator returns structured error (accepted trade-off test)

### Phase 6: MCP Tool Handlers (Depends on Phase 5)

**6.1 — MCP tool registration (`workflow_state_server.py` — I5)**
- File: `plugins/iflow/mcp/workflow_state_server.py`
- Depends on: 5.1-5.4 (all processing functions)
- Add 4 `@mcp.tool()` async handlers per design I5:
  - `reconcile_check(feature_type_id=None)` → guards `_engine`/`_db` for None → delegates to `_process_reconcile_check`
  - `reconcile_apply(feature_type_id=None, direction="meta_json_to_db", dry_run=False)` → guards → delegates to `_process_reconcile_apply`
  - `reconcile_frontmatter(feature_type_id=None)` → guards `_db` for None → delegates to `_process_reconcile_frontmatter`
  - `reconcile_status()` → guards `_engine`/`_db` for None → delegates to `_process_reconcile_status`
- New imports (design I10):
  - `from workflow_engine.reconciliation import check_workflow_drift, apply_workflow_reconciliation, WorkflowDriftResult, ReconciliationResult`
  - `from entity_registry.frontmatter_sync import detect_drift, scan_all, DriftReport, FieldMismatch, ARTIFACT_BASENAME_MAP`
- Why this order: Thin wrappers around processing functions; last production code before integration tests
- Tests (in `test_workflow_state_server.py`): handler returns structured JSON (SC-6); None guards return `_NOT_INITIALIZED`; all AC verification via processing functions (already tested in Phase 5)

### Phase 7: End-to-End Integration Tests (Depends on Phase 6)

Note: Unit tests for `test_reconciliation.py` are created incrementally starting from Phase 1.1 (TDD RED steps). `test_workflow_state_server.py` is extended starting from Phase 4. Phase 7 adds only true end-to-end integration tests that exercise the full stack.

**7.1 — Full-cycle integration tests (`test_reconciliation.py`)**
- File: `plugins/iflow/hooks/lib/workflow_engine/test_reconciliation.py` (EXTEND — file exists from Phase 1.1)
- Covers: full drift detection → reconciliation → verify in_sync cycle (multi-feature scenario with mixed statuses)
- Uses in-memory SQLite DB, temp directories with real .meta.json files
- Scenarios: bulk scan with 3+ features in different drift states → reconcile all → re-check all in_sync; idempotency verification (second reconcile produces all-skipped)
- Edge cases: both-None phases, terminal phases, empty feature set

**7.2 — MCP end-to-end integration tests (`test_workflow_state_server.py`)**
- File: `plugins/iflow/mcp/test_workflow_state_server.py` (EXTEND — file exists from Phase 4)
- Covers: full processing function → handler → response chain for all 4 tools (SC-6, AC-16)
- Uses same test fixtures as existing processing function tests
- Scenarios: reconcile_status returning healthy=true after reconcile_apply; reconcile_frontmatter with real temp files containing frontmatter headers
- Error paths: uninitialized guards (AC-16), invalid direction (AC-17), invalid feature_type_id (AC-18)

---

## Dependency Graph

```
Phase 1 (parallel):
  1.1 Dataclasses ─────────────────────────────┐
  1.2 Phase comparison helpers ───────────────┐│
  1.3 _validate_feature_type_id ────────────┐││
                                            │││
Phase 2 (depends on 1.1, 1.2):             │││
  2.1 _read_single_meta_json ◄─────────────┘││
  2.2 _check_single_feature ◄────────────────┘│
  2.3 check_workflow_drift (public)            │
                                               │
Phase 3 (depends on 2):                       │
  3.1 _reconcile_single_feature                │
  3.2 apply_workflow_reconciliation (public)    │
                                               │
Phase 4 (depends on 1.1 only — parallel w/ 2-3):
  4.1 Workflow serializers ◄───────────────────┘
  4.2 Frontmatter serializer

Phase 5 (depends on 2-4):
  5.1 _process_reconcile_check
  5.2 _process_reconcile_apply
  5.3 _process_reconcile_frontmatter
  5.4 _process_reconcile_status

Phase 6 (depends on 5):
  6.1 MCP tool handlers (4 @mcp.tool() registrations)

Phase 7 (depends on 6):
  7.1 Full-cycle integration tests (test_reconciliation.py — extends file from 1.1)
  7.2 MCP end-to-end integration tests (test_workflow_state_server.py — extends file from 4)
```

## TDD Order

Each item is implemented RED → GREEN → REFACTOR.

**Phase 1 items can be done in parallel — no cross-dependencies:**
1. Create `test_reconciliation.py`, write `WorkflowMismatch`, `WorkflowDriftReport`, `WorkflowDriftResult`, `ReconcileAction`, `ReconciliationResult` tests → implement dataclasses (1.1)
2. Write `_phase_index` and `_compare_phases` tests in `test_reconciliation.py` → implement helpers (1.2)
3. Write `_validate_feature_type_id` tests in `test_workflow_state_server.py` → implement helper (1.3)

**Phase 2 must be sequential:**
4. Write `_read_single_meta_json` tests → implement reader (2.1)
5. Write `_check_single_feature` tests → implement checker (2.2)
6. Write `check_workflow_drift` tests → implement public function (2.3) — covers AC-1 through AC-5

**Phase 3 sequential:**
7. Write `_reconcile_single_feature` tests → implement reconciler (3.1) — covers AC-6 through AC-10
8. Write `apply_workflow_reconciliation` tests → implement public function (3.2)

**Phase 4 (TDD steps 9-10) can run in parallel with TDD steps 4-8 (Phases 2-3):**
9. Write serializer tests → implement `_serialize_workflow_drift_report` and `_serialize_reconcile_action` (4.1)
10. Write frontmatter serializer tests → implement `_serialize_drift_report` (4.2)

**Phase 5 sequential (depends on 2-4 complete):**
11. Write `_process_reconcile_check` tests → implement (5.1) — AC-18 validation error path
12. Write `_process_reconcile_apply` tests → implement (5.2) — AC-17 direction validation
13. Write `_process_reconcile_frontmatter` tests → implement (5.3) — AC-11 through AC-13
14. Write `_process_reconcile_status` tests → implement (5.4) — AC-14, AC-15

**Phase 6:**
15. Write MCP handler tests → implement 4 `@mcp.tool()` handlers (6.1) — SC-6, AC-16

**Phase 7 (end-to-end only — unit tests already exist from Phases 1-6):**
16. Write full-cycle integration tests (7.1) — multi-feature drift detection → reconciliation → verify in_sync cycle
17. Write MCP end-to-end integration tests (7.2) — full processing function + handler chain

## Files Modified

| File | Phase | Change Type |
|------|-------|-------------|
| `plugins/iflow/hooks/lib/workflow_engine/reconciliation.py` | 1-3 | NEW — dataclasses, phase helpers, drift detection, reconciliation logic |
| `plugins/iflow/hooks/lib/workflow_engine/test_reconciliation.py` | 1.1 (created), 1-3, 7 | NEW — created in 1.1 TDD RED step, extended incrementally through Phases 1-3, integration tests in Phase 7 |
| `plugins/iflow/mcp/workflow_state_server.py` | 1.3, 4-6 | ADD — validation helper, serializers, processing functions, MCP handlers, imports |
| `plugins/iflow/mcp/test_workflow_state_server.py` | 1.3 (first), 4-7 | EXTEND — validation tests in 1.3, serializer/processing/handler tests in 4-6, integration tests in 7 |

## Risk Mitigations During Implementation

1. **Private API access (2.1, 2.2, 2.3):** `_derive_state_from_meta`, `_iter_meta_jsons`, and `_extract_slug` are private engine methods. Tests for reconciliation cover these code paths, so breakage is detected immediately. Both modules are in the same `workflow_engine` package (TD-2).

2. **Serialization inversion (4.1):** `ReconcileAction.changes` uses `WorkflowMismatch` with `meta_json_value`/`db_value` but serialization maps to `old_value=db_value`, `new_value=meta_json_value`. Tests must verify the correct mapping direction for meta_json_to_db.

3. **Frontmatter pass-through (5.3):** `_process_reconcile_frontmatter` calls `detect_drift`/`scan_all` directly from `frontmatter_sync` — no reconciliation.py wrapper. Tests must verify `type_id` is passed correctly in per-feature mode to avoid `no_header` results vs `db_only`.

4. **healthy flag computation (5.4):** Both dimensions must use the same zero-check pattern. Tests must cover edge cases: one dimension clean + other dirty → unhealthy; both clean → healthy; error in either → unhealthy.

5. **No existing test modifications:** This feature only adds new code. No existing test file assertions need updating. All existing tests must pass unchanged after implementation.
