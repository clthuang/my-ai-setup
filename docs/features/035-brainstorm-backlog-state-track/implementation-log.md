# Implementation Log: Brainstorm & Backlog State Tracking

## Phase 1: DB Foundation (Migration 5)
- **Files:** `database.py`, `test_database.py`
- **Tests:** 3 new (670 total pass)
- **Notes:** Added `_expand_workflow_phase_check` migration following Migration 3 pattern. Expanded CHECK constraint on `workflow_phase` and `last_completed_phase` to accept 7 new values. Created `_create_v4_db` test helper for before/after migration testing. Updated 5 existing tests that hardcoded schema_version=4.

## Phase 2: MCP Infrastructure
- **Files:** `workflow_state_server.py`, `test_workflow_state_server.py`
- **Tests:** 7 new (229 total pass)
- **Notes:** Added `ENTITY_MACHINES` constant with brainstorm/backlog state machines (transitions, columns, forward sets). Added `_ENTITY_RECOVERY_HINTS` dict and `_catch_entity_value_error` sync decorator following existing `_catch_value_error` pattern.

## Phase 3: MCP Tools
- **Files:** `workflow_state_server.py`, `test_workflow_state_server.py`
- **Tests:** 21 new (250 total pass)
- **Notes:** Implemented `_process_init_entity_workflow` and `_process_transition_entity_phase` with MCP tool wrappers. Feature/project entity types rejected. Forward transitions set `last_completed_phase`, backward do not.

## Phase 4: Backfill
- **Files:** `backfill.py`, `test_backfill.py`
- **Tests:** 7 new (677 total pass)
- **Notes:** Added early-exit guard BEFORE `STATUS_TO_KANBAN` for brainstorm/backlog entities. 3-case logic (no row→INSERT, non-null phase→skip, null phase→UPDATE). Child-completion override moved into guard. Added `updated` counter to return dict. Updated 4 existing tests reflecting new defaults.

## Phase 5: UI
- **Files:** `ui/__init__.py`, `_card.html`, `test_filters.py`, `test_deepened_app.py`
- **Tests:** 7 new (185 total pass)
- **Notes:** Added 7 new PHASE_COLORS entries. Made card template entity-type-aware: mode badge for features, type badge for brainstorm/backlog/project, last_completed_phase for features only, null phase hides badge.

## Phase 6: Skill/Command Updates
- **Files:** `brainstorming/SKILL.md`, `add-to-backlog.md`
- **Tests:** N/A (prompt files)
- **Notes:** Added `init_entity_workflow` call in Stage 3, `transition_entity_phase` in Stages 4 and 6. Added backlog 3-step sequence (register→init→transition). Added entity registration to add-to-backlog command. All MCP calls wrapped in warn-but-don't-block error handling.

## Phase 7: Integration Verification
- Entity registry: 677 passed
- Workflow state MCP: 250 passed
- UI: 185 passed
- Workflow engine: 289 passed
- Transition gate: 257 passed
- **Total: 1,658 tests, 0 failures**
- Hook audit: all 4 hooks confirmed entity-type-agnostic (AC-HOOK-1)
- Manual verification: all skill/command MCP calls verified

## Summary
- **Total new tests:** 45
- **Total files changed:** 12
- **Deviations:** None
- **Concerns:** SKILL.md exceeds 500-line guideline (596 lines, was 559 pre-edit)
