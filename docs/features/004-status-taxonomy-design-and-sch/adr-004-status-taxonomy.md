# ADR-004: Status Taxonomy and Dual-Dimension Schema

## Status

**Accepted** -- 2026-03-01

Dual-dimension status model with separate `workflow_phases` table.

## Context and Problem Statement

iflow currently uses a single `status` field on features with four values (`planned`, `active`, `completed`, `abandoned`) and a separate `lastCompletedPhase` field to track workflow progress. These two fields evolved independently and conflate two distinct concerns: where the work item is in the development lifecycle (workflow phase) and where it sits in the human-agent collaboration process (kanban column).

There is no concept of kanban process state. A feature marked `active` could be in agent review, awaiting human input, blocked, or actively being worked on -- all collapsed into a single value. The `lastCompletedPhase` field tracks progress but carries no information about process state, ownership, or board position. This makes it impossible to build a kanban board view, to track handoffs between agent and human, or to distinguish a blocked feature from one in active development.

The new architecture requires two orthogonal status dimensions -- workflow phase (where the work is in the development lifecycle) and kanban column (where the work sits in the collaboration process) -- coexisting on each entity. This ADR records the taxonomy design, valid values, transition rules, schema DDL, and backward compatibility mapping needed before any implementation.

## Decision Drivers

- **Complete value enumeration required** -- the spec mandates a definitive list of valid values for both workflow_phase (7 phases) and kanban_column (8 columns) with no ambiguity (AC-2, AC-3)
- **Backward compatibility** -- existing `status` field and all `.meta.json` state must map cleanly to the new model without data loss; every field needs an explicit disposition (AC-7)
- **Simplicity over sophistication** -- CHECK constraints preferred over reference tables for small, stable enum sets; snapshot table preferred over event-sourced log (TD-2, TD-3)
- **Separate table, not ALTER TABLE** -- the entity registry's `entities` table already has 10 columns; adding workflow state columns would couple two independent concerns and affect all entity operations (TD-1)
- **Per-entity-type participation rules** -- different entity types (feature, brainstorm, backlog, project) have different relationships with workflow state; this variance must be explicitly documented (AC-5)
- **Enforcement delegation** -- SQLite CHECK constraints are row-local and cannot reference other tables; cross-table rules (entity type restrictions, conflict scenarios) must be delegated to application-level enforcement in feature 008 (TD-5)

## Considered Options

### Option 1: Single-dimension -- extend existing status field

Extend the existing `status` TEXT column on the `entities` table with additional values to capture both workflow progress and process state (e.g., `active-wip`, `active-review`, `active-blocked`).

- **Pros:**
  - Simplest change -- no new tables, no JOINs
  - No migration complexity
- **Cons:**
  - Conflates two independent dimensions into compound string values
  - Combinatorial explosion: 7 phases x 8 columns = 56 potential values
  - No independent tracking -- cannot query "all features in review" without string parsing
  - Violates Single Responsibility -- the entities table becomes coupled to workflow logic

### Option 2: Dual-dimension -- workflow_phase + kanban_column in separate table

Create a new `workflow_phases` table with FK to `entities(type_id)` containing two orthogonal columns: `workflow_phase` (lifecycle progress) and `kanban_column` (process state). One row per participating entity stores the current state snapshot.

- **Pros:**
  - Clean separation of concerns -- workflow progress and process state tracked independently
  - Independent schema evolution -- `workflow_phases` can be extended without touching `entities`
  - Preserves existing entity registry API surface
  - Simple queries for kanban board (indexed `kanban_column` column)
  - CHECK constraints enforce valid values at the database level
- **Cons:**
  - Requires JOIN for combined entity + workflow queries
  - Application-level enforcement needed for cross-table rules (entity type restrictions, conflict resolution)
  - No built-in history (deferred to feature 008 transition log)

### Option 3: Hierarchical state machine with transition tables

Full state machine implementation with a `transitions` table defining valid (source_state, event, target_state) triples, enforced by triggers.

- **Pros:**
  - Complete enforcement at the database level -- invalid transitions are impossible
  - Full audit trail built in
  - Formally verifiable
- **Cons:**
  - Overkill for current needs -- couples schema to transition logic that belongs in the application layer
  - Adds significant DDL complexity (transition tables, validation triggers with subqueries)
  - SQLite performance implications for triggers with cross-table lookups
  - Feature 008 (WorkflowStateEngine) already owns transition logic -- duplicating it in DDL creates two sources of truth

## Decision Outcome

**Chosen option: Dual-dimension model (Option 2).**

The key aspects of this decision:

- **Separate `workflow_phases` table** with FK to `entities(type_id)` -- new table rather than altering the existing entities table (TD-1)
- **`workflow_phase` is the source of truth** -- it determines actual progress through the development lifecycle. This primacy is an application-level invariant enforced by the state engine (feature 008), not expressible in DDL
- **`kanban_column` is the derived/overridable view** -- automatically set by workflow events but can be manually overridden by a human (e.g., dragging a card on the board)
- **One row per participating entity** -- current state snapshot only; no history in this table (TD-3). Phase history (per-phase timestamps, iterations, reviewer notes) is deferred to feature 008's transition log (Decision D-2)
- **CHECK constraints for enum enforcement** -- `CHECK(col IN (...))` for workflow_phase, kanban_column, last_completed_phase, and mode (TD-2). This follows the existing pattern at `database.py:15`
- **Application-level enforcement for cross-table constraints** -- per-entity-type kanban restrictions and conflict scenario validation enforced by feature 008's state engine, not DDL (TD-5)

## Consequences

### Positive Consequences

- Clean separation of workflow progress and process state -- each dimension evolves independently
- Independent schema evolution -- `workflow_phases` can be extended (e.g., adding columns for feature 008) without touching the `entities` table
- Preserves the existing entity registry API surface -- no changes to entity CRUD operations
- Simple, indexed queries for kanban board views -- `SELECT * FROM workflow_phases WHERE kanban_column = 'wip'` is a single-table indexed scan
- Database-level enum enforcement via CHECK constraints prevents invalid values even from direct SQL access

### Negative Consequences

- Application-level enforcement needed for cross-table rules -- entity type restrictions (brainstorm limited to backlog/prioritised) and conflict scenarios (#2, #3, #6) cannot be enforced by DDL alone because SQLite CHECK constraints are row-local
- JOIN required for combined entity + workflow queries -- `SELECT e.*, wp.* FROM entities e JOIN workflow_phases wp ON e.type_id = wp.type_id` adds complexity to queries that need both entity identity and workflow state
- No built-in history -- phase transition audit trail is deferred to feature 008's transition log; until that feature ships, there is no record of state changes over time
- Direct SQL access can bypass application-level constraints -- mitigated by the convention that only the state engine (feature 008) writes to `workflow_phases`

## Appendices

### Appendix A: Workflow Phase Definitions

| Phase | Definition |
|-------|-----------|
| `brainstorm` | Exploring problem space and generating a PRD |
| `specify` | Writing precise requirements and acceptance criteria |
| `design` | Creating technical architecture and interface contracts |
| `create-plan` | Breaking design into ordered implementation steps |
| `create-tasks` | Decomposing plan into individual actionable tasks |
| `implement` | Writing code, tests, and executing tasks |
| `finish` | Final review, documentation, merge, and retrospective |

`workflow_phase` is nullable -- NULL means "not started" (no sentinel value). Brainstorm and backlog entities always have NULL workflow_phase (they do not progress through workflow phases).

SQLite CHECK constraint form: `CHECK(workflow_phase IN ('brainstorm','specify','design','create-plan','create-tasks','implement','finish') OR workflow_phase IS NULL)`.

### Appendix B: Kanban Column Definitions

| Column | Definition | Who Moves Cards Here |
|--------|-----------|---------------------|
| `backlog` | Work item identified but not yet prioritised for action | System (default) or Human |
| `prioritised` | Selected for upcoming work, awaiting start | Human |
| `wip` | Active work in progress by agent or human | Agent (on phase_start) |
| `agent_review` | Agent has dispatched a reviewer subagent | Agent (on reviewer_dispatch) |
| `human_review` | Awaiting human input or decision | Agent (on human_input_requested) |
| `blocked` | Cannot proceed due to missing prerequisite or error | Agent (on phase_blocked) |
| `documenting` | In documentation/wrap-up phase | Agent (on documentation_started) |
| `completed` | Work finished (completed normally or cancelled) | Agent (on feature_completed or feature_cancelled) |

These are DB-stored values (lowercase, underscore-separated). Display labels (e.g., "WIP", "Agent Review") are a UI concern (feature 019).

### Appendix C: Event-to-Column Transition Map

| Event | Target kanban_column | Triggered By |
|-------|---------------------|--------------|
| `phase_start` | `wip` | Agent begins phase execution |
| `reviewer_dispatch` | `agent_review` | Agent spawns reviewer subagent |
| `human_input_requested` | `human_review` | AskUserQuestion invoked |
| `phase_complete` | `wip` (if next phase auto-starts) | Phase marked completed; does not apply to `finish` phase (finish completion triggers `feature_completed` instead) |
| `phase_blocked` | `blocked` | Prerequisite missing or error |
| `phase_unblocked` | `wip` | Blocker resolved |
| `feature_cancelled` | `completed` | Feature abandoned |
| `feature_completed` | `completed` | finish-feature completed |
| `documentation_started` | `documenting` | finish-feature doc phase begins |
| `manual_override` | (any valid column) | Human drags card in UI |

**Auto-start semantics:** All phase transitions auto-start the next phase in sequence (brainstorm -> specify -> design -> create-plan -> create-tasks -> implement -> finish). When a phase completes and the next phase auto-starts, the kanban_column moves to `wip`. No manual pause points exist in the current workflow.

**Finish phase note:** Finish phase completion triggers `feature_completed`, not `phase_complete`. The `phase_complete` event applies only to non-terminal phases.

**Backward transitions:** Backward transitions (which populate `backward_transition_reason`) are triggered by the state engine (feature 008) and are not distinct kanban-column-changing events -- the kanban column change follows the target phase's normal mapping (i.e., backward transition to `design` would set kanban_column to `wip` via the `phase_start` event).

### Appendix D: Entity Type Participation Matrix

| Entity Type | Has workflow_phases Row? | workflow_phase Values | kanban_column Values |
|------------|------------------------|----------------------|---------------------|
| `feature` | Yes | All 7 phases + NULL | All 8 columns |
| `brainstorm` | Yes | NULL only (brainstorms do not have workflow phases) | `backlog`, `prioritised` only |
| `backlog` | Yes | NULL only | `backlog`, `prioritised` only |
| `project` | No | N/A | N/A |

**Enforcement delegation:** Per-entity-type kanban column restrictions are enforced by the state engine (feature 008) at the application level, NOT by DDL constraints. SQLite CHECK constraints cannot reference other tables to determine entity_type. The DDL in Appendix E intentionally allows all 8 kanban_column values for all entity types; column-restriction enforcement is entirely delegated to feature 008.

### Appendix E: Schema DDL

The following DDL defines the `workflow_phases` table as migration version 2 in the entity registry.

```sql
CREATE TABLE IF NOT EXISTS workflow_phases (
    -- FK uses implicit ON DELETE RESTRICT (SQLite default). Deleting an entity
    -- while its workflow_phases row exists will fail, which is the desired behavior —
    -- workflow state should be explicitly cleaned up before entity deletion.
    type_id                    TEXT PRIMARY KEY REFERENCES entities(type_id),
    workflow_phase             TEXT CHECK(workflow_phase IN (
                                   'brainstorm','specify','design',
                                   'create-plan','create-tasks',
                                   'implement','finish'
                               ) OR workflow_phase IS NULL),
    kanban_column              TEXT NOT NULL DEFAULT 'backlog'
                               CHECK(kanban_column IN (
                                   'backlog','prioritised','wip',
                                   'agent_review','human_review',
                                   'blocked','documenting','completed'
                               )),
    last_completed_phase       TEXT CHECK(last_completed_phase IN (
                                   'brainstorm','specify','design',
                                   'create-plan','create-tasks',
                                   'implement','finish'
                               ) OR last_completed_phase IS NULL),
    mode                       TEXT CHECK(mode IN ('standard', 'full')
                                   OR mode IS NULL),
    backward_transition_reason TEXT,
    updated_at                 TEXT NOT NULL
);

-- Immutability trigger for type_id (FK, should not change)
CREATE TRIGGER IF NOT EXISTS enforce_immutable_wp_type_id
BEFORE UPDATE OF type_id ON workflow_phases
BEGIN
    SELECT RAISE(ABORT, 'workflow_phases.type_id is immutable');
END;

-- Indexes for common query patterns
CREATE INDEX IF NOT EXISTS idx_wp_kanban_column ON workflow_phases(kanban_column);
CREATE INDEX IF NOT EXISTS idx_wp_workflow_phase ON workflow_phases(workflow_phase);
```

**Notes:**

- Per-phase timestamps (started, completed, iterations, reviewerNotes, skippedPhases) are NOT in this table -- deferred to feature 008 transition log (Decision D-2).
- The FK references `entities(type_id)` per current schema v1. If feature 001 (UUID migration) changes the PK before this DDL is executed, the FK column and type must be updated accordingly. This ADR records the design intent; the implementing feature (005) will use the PK that exists at implementation time.
- `updated_at` uses UTC in ISO-8601 format (e.g., `2026-03-01T12:00:00Z`) -- avoids mixed-timezone inconsistency from .meta.json.

### Appendix F: Conflict Resolution Scenarios

| # | Scenario | workflow_phase | kanban_column | Valid? | Resolution | Enforcement |
|---|----------|---------------|---------------|--------|------------|-------------|
| 1 | Active work demoted to backlog | `design` | `backlog` | Valid | Human override -- feature deprioritised mid-work | N/A (valid state) |
| 2 | Working on nothing | NULL | `wip` | Invalid | Constraint: if kanban_column is `wip`/`agent_review`/`human_review`, workflow_phase must not be NULL for feature entities | Application-level (feature 008 state engine) -- requires entity_type lookup |
| 3 | Premature completion | `implement` | `completed` | Invalid | Constraint: kanban_column=`completed` requires workflow_phase=`finish` OR `feature_cancelled` event was triggered (see scenario #6 for the valid abandoned case) | Application-level (feature 008 state engine) -- requires event context |
| 4 | Orphaned row -- both NULL | NULL | (missing) | Invalid | kanban_column has NOT NULL + DEFAULT `backlog`, so this cannot occur | DDL-level (NOT NULL + DEFAULT constraint) |
| 5 | Agent review without reviewer | `design` | `agent_review` | Valid | Transitional -- the column is set before reviewer dispatch as a signal | N/A (valid state) |
| 6 | Distinguishing abandoned from completed | `implement` | `completed` | Valid | Abandoned inference rule: kanban_column=`completed` AND `(workflow_phase IS NULL OR workflow_phase != 'finish')` means the feature was cancelled/abandoned rather than completed normally. The `feature_cancelled` event triggers this state. | Application-level (feature 008 state engine reads workflow_phase to determine disposition) |

**Enforcement note:** Scenarios #2, #3, and #6 require application-level enforcement because SQLite CHECK constraints cannot reference other tables (for entity_type) or event context. The state engine (feature 008) validates these rules during transitions.

### Appendix G: Backward Compatibility Map

This table covers feature and brainstorm entity `.meta.json` fields. Project entity fields (e.g., `expected_lifetime`, `milestones` sub-fields) are excluded because projects do not participate in `workflow_phases` (AC-5).

#### Field Disposition Table

| .meta.json Field | Disposition | Target |
|-----------------|-------------|--------|
| `id` | Stays in .meta.json | Not migrated -- display identifier |
| `slug` | Stays in .meta.json | Not migrated -- display identifier |
| `status` | Maps to kanban_column | See status conversion table below |
| `created` | Already in entities table | `entities.created_at` |
| `completed` | Maps to workflow_phases | Captured via kanban_column=`completed` + `updated_at` |
| `mode` | Maps to workflow_phases | `workflow_phases.mode` |
| `branch` | Stays in .meta.json | Not migrated -- git concern, not workflow state |
| `project_id` | Already in entities table | Via `parent_type_id` (e.g., project:P001) |
| `module` | Already in entities metadata | `entities.metadata` JSON |
| `depends_on_features` | Already in entities metadata | `entities.metadata` JSON |
| `lastCompletedPhase` | Maps to workflow_phases | `workflow_phases.last_completed_phase` |
| `skippedPhases` | Deferred to feature 008 | Transition log responsibility |
| `phases.{name}.started` | Deferred to feature 008 | Per-phase timestamps in transition log |
| `phases.{name}.completed` | Deferred to feature 008 | Per-phase timestamps in transition log |
| `phases.{name}.iterations` | Deferred to feature 008 | Per-phase iteration count in transition log |
| `phases.{name}.reviewerNotes` | Deferred to feature 008 | Reviewer notes in transition log |
| `phases.{name}.taskReview.*` | Deferred to feature 008 | Task review sub-object (iterations, approved, concerns) in transition log |
| `phases.{name}.chainReview.*` | Deferred to feature 008 | Chain review sub-object (iterations, approved, concerns) in transition log |
| `phases.{name}.reviewIterations` | Deferred to feature 008 | Per-phase review iteration count in transition log |
| `phases.{name}.approved` | Deferred to feature 008 | Per-phase approval status in transition log |
| `phases.{name}.status` | Deferred to feature 008 | Phase-level status in transition log |
| `phases.design.stages.*` | Deferred to feature 008 | Design-specific sub-structure in transition log |
| `backlog_source` | Stays in .meta.json | Not migrated -- provenance metadata linking feature to backlog item |
| `brainstorm_source` | Stays in .meta.json | Not migrated -- provenance metadata |
| `abandoned_reason` | Stays in .meta.json | Contextual narrative; `backward_transition_reason` in workflow_phases captures structured reason |
| `retro_completed` | Stays in .meta.json | Process metadata, not workflow state |
| `lastCompletedMilestone` | Stays in .meta.json | Project-level, not feature workflow |
| `milestones` | Stays in .meta.json | Project-level, not feature workflow |
| `features` | Stays in .meta.json | Project-level, not feature workflow |

**Additional discovered fields (nested in phases):**

| .meta.json Field | Disposition | Target |
|-----------------|-------------|--------|
| `phases.{name}.skipped` | Deferred to feature 008 | Transition log (phase skip tracking) |
| `phases.{name}.concerns` | Deferred to feature 008 | Transition log (reviewer concerns) |
| `phases.{name}.capReached` | Deferred to feature 008 | Transition log (iteration cap tracking) |
| `phases.{name}.phaseReview.*` | Deferred to feature 008 | Phase review sub-object in transition log |
| `phases.{name}.planReview.*` | Deferred to feature 008 | Plan review sub-object in transition log |
| `phases.{name}.specReviewer.*` | Deferred to feature 008 | Spec reviewer sub-object in transition log |
| `phases.{name}.phaseReviewer.*` | Deferred to feature 008 | Phase reviewer sub-object in transition log |
| `phases.{name}.planReviewer.*` | Deferred to feature 008 | Plan reviewer sub-object in transition log |
| `phases.{name}.phaseReviewIterations` | Deferred to feature 008 | Phase-level review iteration count in transition log |
| `phases.{name}.planReviewIterations` | Deferred to feature 008 | Plan-level review iteration count in transition log |
| `phases.{name}.reviewResult` | Deferred to feature 008 | Review result in transition log |
| `phases.{name}.reworked` | Deferred to feature 008 | Rework tracking in transition log |
| `phases.{name}.reworkReason` | Deferred to feature 008 | Rework reason in transition log |
| `phases.{name}.revised` | Deferred to feature 008 | Revision tracking in transition log |
| `phases.{name}.verified` | Deferred to feature 008 | Verification status in transition log |
| `phases.{name}.notes` | Deferred to feature 008 | Phase notes in transition log |
| `phases.{name}.artifact` | Deferred to feature 008 | Artifact reference in transition log |
| `phases.{name}.artifacts` | Deferred to feature 008 | Artifact references in transition log |
| `phases.{name}.startedAt` | Deferred to feature 008 | Per-phase timestamp (alternate key) in transition log |
| `phases.{name}.completedAt` | Deferred to feature 008 | Per-phase timestamp (alternate key) in transition log |
| `phases.{name}.testsDeepenedCount` | Deferred to feature 008 | Test deepening count in transition log |
| `phases.{name}.result` | Deferred to feature 008 | Phase result in transition log |
| `phases.{name}.name` | Deferred to feature 008 | Phase name (redundant with key) in transition log |
| `phases.design.stages.research` | Deferred to feature 008 | Design research stage sub-object in transition log |
| `phases.design.stages.architecture` | Deferred to feature 008 | Design architecture stage sub-object in transition log |
| `phases.design.stages.interface` | Deferred to feature 008 | Design interface stage sub-object in transition log |
| `phases.design.stages.designReview` | Deferred to feature 008 | Design review stage sub-object in transition log |
| `phases.design.stages.handoffReview` | Deferred to feature 008 | Design handoff review stage sub-object in transition log |

#### Status to kanban_column Conversion Table

| Current status | kanban_column | Rationale |
|---------------|---------------|-----------|
| `planned` | `backlog` | Not yet started = backlog |
| `active` | `wip` | Active work (actual kanban column refined by workflow events) |
| `completed` | `completed` | Terminal state |
| `abandoned` | `completed` | Terminal state -- inferred as abandoned when kanban_column=`completed` AND `(workflow_phase IS NULL OR workflow_phase != 'finish')` (see Appendix F scenario #6) |

**Note:** `active` -> `wip` is the initial mapping. Once the state engine (feature 008) is running, the kanban column for active features is dynamically updated by workflow events (reviewer dispatch -> `agent_review`, AskUserQuestion -> `human_review`, etc.).
