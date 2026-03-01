# Spec: Entity UUID Primary Key Migration

## Problem Statement

The entity registry uses `type_id` (format `"{entity_type}:{entity_id}"`) as its PRIMARY KEY. This text-based composite key couples identity to display semantics — if naming conventions change, the key changes. UUID v4 provides a stable, opaque primary key that decouples identity from display, enabling downstream features (002, 005, 012, 013, 018) to reference entities by immutable identifier.

**PRD Traceability:** This feature implements PRD Section "M0: Identity and Taxonomy Foundations" — specifically the "UUID canonical identity" cross-cutting concern (roadmap.md line 116) and the F001 root node in the dependency graph.

## Goals

1. Make UUID v4 the canonical primary key for the `entities` table
2. Retain `type_id` as a UNIQUE indexed column for human-readable lookups
3. Provide dual-read compatibility so all existing callers continue working
4. Migrate existing data with zero data loss
5. Maintain all existing immutability and safety invariants

## Non-Goals

- Changing entity_type vocabulary (handled by feature 005)
- Adding new entity types
- Modifying the MCP server transport or protocol
- UI changes (handled by later features)
- Changing the backfill scanner's artifact discovery logic

## Requirements

### Schema Migration (Migration 2)

- R1: Add `uuid` column of type `TEXT NOT NULL` containing UUID v4 values
- R2: `uuid` becomes the PRIMARY KEY of the `entities` table
- R3: `type_id` becomes `TEXT NOT NULL UNIQUE` (no longer PRIMARY KEY, but still uniquely indexed)
- R4: `parent_type_id` column is retained for backward-compatible lookups
- R5: Add `parent_uuid` column of type `TEXT REFERENCES entities(uuid)` as the canonical parent foreign key
- R6: Populate all existing rows with generated UUID v4 values during migration
- R7: Populate `parent_uuid` from existing `parent_type_id` references during migration
- R8: SQLite requires table recreation for PK changes — use CREATE-COPY-DROP-RENAME pattern wrapped in an explicit transaction via `conn.execute("BEGIN IMMEDIATE")` before the first DDL statement. The `_migrate()` method's existing `conn.commit()` commits the transaction. If any step fails, `conn.rollback()` undoes all DDL and DML. Do NOT use `conn.executescript()` (which auto-commits each statement). Note: under Python sqlite3's legacy transaction control, DDL statements do not start implicit transactions — only DML does — hence the explicit BEGIN is required.
- R9: Migration version increments from 1 to 2 in the MIGRATIONS dict

### Immutability Triggers

- R10: Add trigger `enforce_immutable_uuid` — BEFORE UPDATE OF uuid on entities → RAISE ABORT with message "uuid is immutable"
- R11: Retain existing triggers for `type_id`, `entity_type`, `created_at`
- R12: Add trigger `enforce_no_self_parent_uuid` — two separate triggers:
  - BEFORE INSERT on entities: `WHEN NEW.parent_uuid IS NOT NULL AND NEW.parent_uuid = NEW.uuid` → RAISE ABORT "entity cannot be its own parent"
  - BEFORE UPDATE OF parent_uuid on entities: `WHEN NEW.parent_uuid IS NOT NULL AND NEW.parent_uuid = NEW.uuid` → RAISE ABORT "entity cannot be its own parent"

### EntityDatabase API Changes

- R13: `register_entity()` auto-generates UUID v4 via `uuid.uuid4()` and returns the UUID string
- R14: `register_entity()` still constructs `type_id` from `entity_type:entity_id` for the UNIQUE column
- R15: `get_entity()` accepts either UUID or type_id as lookup key (dual-read via `_resolve_identifier`)
- R16: `set_parent()` accepts either UUID or type_id for both `type_id` and `parent_type_id` parameters; updates BOTH `parent_type_id` and `parent_uuid` columns atomically in the same UPDATE statement
- R17: `get_lineage()` accepts either UUID or type_id as starting entity
- R18: `update_entity()` accepts either UUID or type_id as the entity identifier
- R19: `export_lineage_markdown()` accepts either UUID or type_id
- R20: Methods that change return type from type_id to UUID:
  - `register_entity()` → returns UUID (was type_id)
  - `set_parent()` → returns UUID (was None/implicit)
  - `update_entity()` remains unchanged (returns None)
  - `get_entity()` returns dict with both `uuid` and `type_id` fields (dict shape change, not return type change)
  - `get_lineage()` returns list of dicts, each with both `uuid` and `type_id` fields
  - `export_lineage_markdown()` return type unchanged (returns markdown string)
- R21: Internal queries use `uuid` for joins and foreign key lookups (the canonical path); specifically:
  - `set_parent()` circular reference detection CTE joins on `uuid`/`parent_uuid`
  - `get_lineage()` recursive CTEs (`_lineage_up`, `_lineage_down`) traverse via `uuid`/`parent_uuid`
  - `_export_tree()` recursive CTE uses `uuid`/`parent_uuid` for parent-child linkage
  - `export_lineage_markdown()` root-finding query (when `type_id=None`) selects `uuid` for use as CTE starting points in `_export_tree()`
- R35: `register_entity()` duplicate handling: when `INSERT OR IGNORE` fires (type_id already exists), query and return the existing row's UUID instead of returning the freshly generated (never-stored) UUID

### Dual-Read Resolution

- R22: Implement a `_resolve_identifier(identifier: str) -> tuple[str, str]` method that returns `(uuid, type_id)` given either form. Empty string and whitespace-only inputs are treated as type_id lookups and will raise ValueError (entity not found).
- R23: UUID format detection: normalize input to lowercase before matching against UUID v4 regex pattern `^[0-9a-f]{8}-[0-9a-f]{4}-4[0-9a-f]{3}-[89ab][0-9a-f]{3}-[0-9a-f]{12}$`
- R24: If identifier matches UUID pattern, look up by `uuid` column
- R25: If identifier does not match UUID pattern, look up by `type_id` column
- R26: `_resolve_identifier()` raises `ValueError` if identifier resolves to no entity. Callers handle this differently:
  - `get_entity()` catches `ValueError` and returns `None` (preserving current behavior where missing entities return None)
  - `set_parent()` lets `ValueError` propagate (invalid parent/child is an error)
  - `update_entity()` lets `ValueError` propagate (updating nonexistent entity is an error)
  - `get_lineage()` catches `ValueError` and returns `[]` (preserving current behavior where nonexistent entities return empty list; existing test `test_nonexistent_entity_returns_empty` must continue to pass)
  - `export_lineage_markdown()` lets `ValueError` propagate when a specific entity is requested

### MCP Server Tool Signatures

- R27: All MCP tool parameters currently named `type_id` and `parent_type_id` accept either UUID or type_id values (no parameter rename needed — the dual-read resolver handles disambiguation)
- R28: Tool return messages include both UUID and type_id for clarity (e.g., `"Registered entity: {uuid} ({type_id})"`)

### Backfill Compatibility

- R29: `backfill.py` continues to call `register_entity()` with `entity_type` and `entity_id` — UUID is auto-generated internally
- R30: `backfill.py` calls to `set_parent()` continue using `type_id` strings — dual-read resolver handles them
- R31: No changes required to backfill scanner logic. Analysis:
  - `register_entity()` signature (`entity_type`, `entity_id`, `name`, ...) is unchanged — only the return value changes from type_id to UUID. Backfill captures return value but only passes it to `set_parent()`, which accepts either UUID or type_id via dual-read.
  - `_safe_set_parent()` wrapper in backfill.py passes type_id strings to `set_parent()` — dual-read resolver handles this transparently.
  - The backfill_complete metadata guard and scan ordering are unaffected by the schema change.

### Server Helpers

- R32: `_format_entity_label()` in `server_helpers.py` displays `type_id` (human-readable) in tree output, not UUID
- R33: `render_tree()` changes its internal data structures to key on `uuid` instead of `type_id`: `by_id` dict keyed by `uuid`, `children` map built from `parent_uuid`, `root_type_id` parameter accepts UUID as the root identifier. Display labels continue to use `type_id` via `_format_entity_label()`. `_process_get_lineage()` passes `entities[0]["uuid"]` as the root identifier.
- R34: `_process_register_entity()` return message includes both UUID and type_id

## Acceptance Criteria

### Schema

- AC-1: After migration, `entities` table has `uuid TEXT PRIMARY KEY` and `type_id TEXT NOT NULL UNIQUE`
- AC-2: After migration, `entities` table has `parent_uuid TEXT REFERENCES entities(uuid)`
- AC-3: All existing entities have valid UUID v4 values in the `uuid` column
- AC-4: `_metadata.schema_version` equals `"2"` after migration
- AC-5: Foreign key constraint on `parent_uuid` is enforced (inserting invalid parent_uuid fails)

### Immutability

- AC-6: Attempting to UPDATE `uuid` column raises `"uuid is immutable"` error
- AC-7a: INSERTING entity where `parent_uuid = uuid` raises `"entity cannot be its own parent"` error
- AC-7b: UPDATING entity to set `parent_uuid = uuid` raises `"entity cannot be its own parent"` error
- AC-8: Existing immutability triggers for `type_id`, `entity_type`, `created_at` still fire

### Dual-Read

- AC-9: `get_entity("feature:001-slug")` returns the entity (type_id lookup)
- AC-10: `get_entity("<valid-uuid>")` returns the same entity (UUID lookup)
- AC-11: `get_entity("nonexistent")` returns `None` (get_entity catches ValueError from _resolve_identifier)
- AC-12: `set_parent("<uuid-of-child>", "<type_id-of-parent>")` succeeds (mixed identifiers) and updates both `parent_type_id` and `parent_uuid` columns
- AC-13: `get_lineage("<uuid>")` returns correct ancestry chain
- AC-14: `update_entity("<type_id>", name="New Name")` succeeds and updates correctly

### Return Values

- AC-15: `register_entity()` returns a UUID v4 string (not type_id)
- AC-15a: `register_entity()` with duplicate type_id returns the existing row's UUID (not a freshly generated one) (per R35)
- AC-16: `set_parent()` returns UUID of the updated entity
- AC-17: `get_entity()` result dict includes both `uuid` and `type_id` fields

### Migration Safety

- AC-18: Migration 2 runs within an explicit `BEGIN IMMEDIATE` transaction — failure rolls back all DDL and DML completely. Does NOT use `conn.executescript()` (which auto-commits) or rely on implicit transactions (which don't cover DDL).
- AC-19: Running migration on a fresh database (no existing data) produces correct schema
- AC-20: Running migration on a database with existing entities preserves all data (zero loss)
- AC-21: `parent_uuid` values correctly reference the UUID of the entity previously referenced by `parent_type_id`
- AC-22: Schema version 1 databases auto-migrate to version 2 on `EntityDatabase.__init__`

### Backward Compatibility

- AC-23: Existing MCP tool calls using `type_id` strings continue to work identically
- AC-24: Backfill runs successfully against the new schema without code changes to `backfill.py`
- AC-25: `export_lineage_markdown()` output uses `type_id` for display (not UUID). Verification: capture output before and after migration on same dataset — tree labels must match.

### Set Parent Atomicity

- AC-28: `set_parent()` updates both `parent_type_id` and `parent_uuid` in a single UPDATE statement
- AC-29: After `set_parent(child, parent)`, querying the child entity shows consistent `parent_type_id` and `parent_uuid` values that both resolve to the same parent entity

### Test Coverage

- AC-26: All 184 existing entity registry tests pass after migration, with tests updated where behavioral changes (R20 return values, R16 set_parent atomicity) require new assertions. The number of test functions must not decrease (tests are updated, not deleted).
- AC-27: New tests cover these specific scenarios:
  - UUID generation: `register_entity()` returns valid UUID v4 format
  - Duplicate detection: `register_entity()` with same type_id returns existing UUID
  - Dual-read: `_resolve_identifier()` with UUID input, type_id input, and nonexistent input
  - Migration v1→v2: fresh DB, populated DB, parent_uuid population
  - Immutability: UUID update blocked, self-parent on INSERT, self-parent on UPDATE
  - Mixed identifiers: `set_parent(uuid, type_id)`, `get_lineage(uuid)`, `update_entity(type_id)`
  - Atomicity: `set_parent()` updates both parent columns
  - Minimum 10 new test functions covering these scenarios

## Constraints

- C1: SQLite does not support `ALTER TABLE ... ADD PRIMARY KEY` — must use table recreation
- C2: UUID generation uses Python's `uuid.uuid4()` — no external dependencies
- C3: UUID stored as lowercase hex with hyphens (standard format: `xxxxxxxx-xxxx-4xxx-yxxx-xxxxxxxxxxxx`). Input UUIDs are normalized to lowercase before regex matching.
- C4: Migration must be idempotent — running on an already-migrated database is a no-op (detected via `schema_version` metadata check before executing migration DDL)
- C5: WAL mode, foreign_keys=ON, busy_timeout=5000 pragmas must persist across migration. These are set in `__init__` before migration runs, and migration DDL does not alter PRAGMA state. After `ALTER TABLE RENAME`, SQLite automatically updates internal FK references to the new table name. Verify with `PRAGMA foreign_key_check` as part of migration validation.
- C6: The `INSERT OR IGNORE` semantics in `register_entity` use `type_id` UNIQUE constraint (not UUID) to detect duplicates — same entity_type:entity_id pair should not create a second row

## Dependencies

- **Depends on**: None (root feature in dependency graph)
- **Required by**: 002-markdown-entity-file-header-sc, 005-workflowphases-table-with-dual, 012-full-text-entity-search-mcp-to, 013-entity-context-export-mcp-tool, 018-unified-iflow-ui-server-with-s

## Scope Boundary

### In Scope

- Schema migration (v1 → v2)
- EntityDatabase API changes (dual-read, UUID return values)
- Trigger updates (uuid immutability, self-parent prevention)
- Server helper display adjustments
- MCP tool dual-read compatibility
- Test updates for all changed behavior

### Out of Scope

- Removing `type_id` column entirely (kept for human-readable lookups indefinitely)
- Removing `parent_type_id` column (kept alongside `parent_uuid` for backward compat)
- Adding new MCP tools
- Changing entity_type vocabulary
- Performance optimization beyond maintaining current levels
