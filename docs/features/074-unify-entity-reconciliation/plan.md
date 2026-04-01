# Plan: Unify Entity Reconciliation

## Implementation Order

### Stage 1: Tests First, Then Implementation (TDD)

1. **Write unit tests for _sync_backlog_entities()** — Test-first
   - **Why this item:** TDD: define expected behavior before implementation
   - **Why this order:** Must precede item 2 (implementation)
   - **Deliverable:** Test cases in test_entity_status.py: parse row with (closed:)→dropped, (promoted→)→promoted, (fixed:)→dropped, no marker→open, junk ID deletion, same-project dedup, missing backlog.md returns empty
   - **Complexity:** Simple (test fixtures with mock DB)
   - **Files:** `reconciliation_orchestrator/test_entity_status.py`
   - **Verification:** Tests exist and fail (RED phase)

2. **Implement _sync_backlog_entities() helper** — Make tests pass
   - **Why this item:** Design C2/I2 — the core missing functionality
   - **Why this order:** After item 1 (TDD GREEN phase)
   - **Deliverable:** New private function in entity_status.py that reads backlog.md, parses rows with BACKLOG_ROW_RE, detects status markers, registers/updates entities. Includes junk cleanup (I3) and dedup (I4). Uses `db.list_entities()` (not search_entities). Uses `project_root` for brainstorm path resolution (not full_artifacts_path/..).
   - **Complexity:** Medium (regex parsing + DB operations + cleanup logic)
   - **Files:** `reconciliation_orchestrator/entity_status.py`
   - **Verification:** All item 1 tests pass (GREEN phase)

3. **Write tests + implement _sync_brainstorm_entities()** — Absorb brainstorm_registry + missing-file detection
   - **Why this item:** Design C1/I5 — merge existing code + add AC-9
   - **Why this order:** Independent of items 1-2, parallel
   - **Deliverable:** Tests for: register new brainstorm, skip existing, archive missing file. Implementation: copy brainstorm_registry.py logic + add missing-file detection using `os.path.join(project_root, artifact_path)` for path resolution (not full_artifacts_path/..)
   - **Complexity:** Simple
   - **Files:** `reconciliation_orchestrator/entity_status.py`, `reconciliation_orchestrator/test_entity_status.py`
   - **Verification:** Tests pass

### Stage 2: Integration (depends on Stage 1)

3. **Refactor sync_entity_statuses() to call all 4 helpers** — Unified entry point
   - **Why this item:** Design C1/I1 — single function handling all entity types
   - **Why this order:** After items 1-2 (helpers must exist)
   - **Deliverable:** Updated sync_entity_statuses with new `artifacts_root` parameter, calling _sync_meta_json_entities (features+projects), _sync_brainstorm_entities, _sync_backlog_entities. Aggregated return dict with registered/deleted counts.
   - **Complexity:** Simple (orchestration wrapper)
   - **Files:** `reconciliation_orchestrator/entity_status.py`
   - **Verification:** Integration test: full sync on test fixtures with all 4 entity types

4. **Update orchestrator __main__.py** — Remove Task 2, pass artifacts_root
   - **Why this item:** Design C3 — orchestrator calls unified function
   - **Why this order:** After item 3 (needs unified function)
   - **Deliverable:** Remove brainstorm_registry import and Task 2 call. Add artifacts_root parameter to Task 1 call. Remove brainstorm_sync key from results dict.
   - **Complexity:** Simple (4 lines changed)
   - **Files:** `reconciliation_orchestrator/__main__.py`
   - **Verification:** Run orchestrator CLI, verify single entity_sync output with registered/deleted counts

### Stage 3: Cleanup (depends on Stage 2) — atomic step

5. **Delete brainstorm_registry + update tests + regression** — Atomic cleanup
   - **Why this item:** Design C4 — module absorbed. Tests must be updated in the same step to avoid broken test window.
   - **Why this order:** After item 4 (no more imports). Done as one atomic commit.
   - **Deliverable:** (a) Update test_orchestrator.py: remove brainstorm_sync assertions, assert entity_sync includes registered/deleted counts. Also verify test_entity_status.py works with new `artifacts_root` parameter (default "docs" provides backward compat). (b) Delete brainstorm_registry.py and test_brainstorm_registry.py. (c) Run full regression.
   - **Complexity:** Simple (test updates + file deletion)
   - **Files:** `reconciliation_orchestrator/brainstorm_registry.py` (delete), `reconciliation_orchestrator/test_brainstorm_registry.py` (delete), `reconciliation_orchestrator/test_orchestrator.py` (update)
   - **Verification:** `plugins/pd/.venv/bin/python -m pytest plugins/pd/hooks/lib/reconciliation_orchestrator/ plugins/pd/hooks/lib/entity_registry/ -v` — all pass

6. **Regression test run** — Full test suite
   - **Why this item:** Zero regression verification
   - **Why this order:** After all changes
   - **Deliverable:** Clean test run
   - **Complexity:** Simple
   - **Files:** None
   - **Verification:** All entity_registry + reconciliation_orchestrator tests pass

## Dependency Graph

```
Item 1 (tests) ──→ Item 2 (backlog impl) ──→ Item 4 (unified fn) ──→ Item 5 (orchestrator) ──→ Item 6 (atomic cleanup + regression)
Item 3 (brainstorm tests+impl) ──→ Item 4
```

## Risk Areas

- **Item 1 (backlog parsing):** Regex must handle all backlog.md row variants. Mitigation: test against actual backlog.md content.
- **Item 5 (deletion):** Must verify no hidden imports before deleting. Mitigation: grep for brainstorm_registry across entire codebase.

## Testing Strategy

- **Unit tests:** Items 1-2 — test each helper independently with fixture data
- **Integration tests:** Item 3 — test unified function with all 4 entity types
- **Regression tests:** Item 7 — full test suite

## Definition of Done

- [ ] Backlog items in backlog.md are synced to entity registry with correct statuses
- [ ] Junk backlog entities (non-5-digit IDs) deleted from DB
- [ ] Same-project duplicate backlogs deduplicated
- [ ] Brainstorm registration absorbed from brainstorm_registry.py
- [ ] Missing brainstorm .prd.md files detected → entity status set to "archived"
- [ ] brainstorm_registry.py and its tests deleted
- [ ] Orchestrator outputs single entity_sync key
- [ ] All tests pass (zero regression)
