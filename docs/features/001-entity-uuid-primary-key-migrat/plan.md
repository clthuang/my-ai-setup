# Plan: Entity UUID Primary Key Migration

## Implementation Order

The migration follows the design's 4-layer architecture bottom-up. Each phase builds on the one below. TDD order: write/update tests first, then implement, verify green.

```
Phase 1: Schema Foundation
  Migration 2 function + triggers + indexes
      ↓
Phase 2: Core Database API
  _resolve_identifier + register_entity (parallel)
  then set_parent → get_entity → get_lineage/update_entity → export
      ↓
Phase 3: Server Helpers
  render_tree internals → process handlers (sequential)
      ↓
Phase 4: MCP Server
  Tool handler message updates
      ↓
Phase 5: Test Finalization & Verification
  Existing test updates + full suite run
```

## Dependency Graph

```
[1.1 Migration 2 schema DDL]
    ↓
[1.2 Migration 2 data copy + parent_uuid population]
    ↓
[1.3 Trigger + index recreation] ──→ [1.4 Migration 2 error handling + idempotency]
    ↓
[2.1 _resolve_identifier method] ──┐
                                   ├──→ [2.3 set_parent]
[2.2 register_entity (parallel)] ──┘         ↓
                                      [2.4 get_entity]
                                             ↓
                                      [2.5 get_lineage + update_entity]
                                             ↓
                                      [2.6 export_lineage_markdown + _export_tree]
    ↓
[3.1 render_tree internals]
    ↓
[3.2 _process_register_entity + _process_get_lineage]
    ↓
[4.1 MCP tool handler messages]
    ↓
[5.1 Existing test assertion updates] ──→ [5.2 Full suite verification]
```

**Parallel groups:**
- Within Phase 2: `_resolve_identifier` (2.1) and `register_entity` (2.2) are independent — 2.2 does not use `_resolve_identifier`
- Within Phase 2: `get_entity` (2.4) and `get_lineage/update_entity` (2.5) are independent after `set_parent` (2.3)
- Phase 3 is sequential: `render_tree` (3.1) must complete before process handlers (3.2), since 3.2 passes uuid values to render_tree
- Phase 5 tasks are sequential (update assertions before running suite)

## Phase 1: Schema Foundation

**File:** `plugins/iflow/hooks/lib/entity_registry/database.py`

### 1.1 Migration 2 Schema DDL

**Tests first:** Write `test_migration_fresh_db` — verify fresh DB produces 12-column schema with uuid PK, type_id UNIQUE, parent_uuid FK, 8 triggers, 4 indexes.

**Implementation:**
1. Add `import uuid as uuid_mod` and `import re` at module top
2. Add module-level `_UUID_V4_RE = re.compile(r'^[0-9a-f]{8}-[0-9a-f]{4}-4[0-9a-f]{3}-[89ab][0-9a-f]{3}-[0-9a-f]{12}$')` (TD-6)
3. Create `_migrate_to_uuid_pk(conn)` function with docstring per I1
4. Step 1: `PRAGMA foreign_keys = OFF` (must execute OUTSIDE any transaction)
5. Step 1b: Verify `PRAGMA foreign_keys` returns 0 — abort if not (C1)
6. Step 2: `conn.execute("BEGIN IMMEDIATE")` (starts transaction AFTER pragma is set)
7. Step 3: `PRAGMA foreign_key_check` pre-migration validation (Risk 2a)
8. Step 4: `CREATE TABLE entities_new` with exact DDL from I9

**Note on step ordering:** Steps 1-1b (PRAGMA OFF + verify) execute before BEGIN IMMEDIATE because PRAGMA foreign_keys cannot be changed inside a transaction. Steps 2+ execute inside the transaction. The finally block (see 1.4) re-enables PRAGMA foreign_keys = ON regardless of success/failure.

**Done criteria:** Fresh DB has correct schema (uuid PK, type_id UNIQUE, 12 columns).

### 1.2 Migration 2 Data Copy

**Tests first:** Write `test_migration_populated_db_preserves_data` and `test_migration_populates_parent_uuid`.

**Implementation:**
1. Step 5: Read all rows, generate UUID per row (I10 Steps 1-2)
2. Step 6: INSERT into entities_new with uuid (I10 Step 3, parent_uuid intentionally omitted — populated in next step)
3. Step 7: UPDATE parent_uuid from parent_type_id mapping (I10 Step 4)
4. Step 8: DROP old entities table
5. Step 9: RENAME entities_new to entities

**Done criteria:** Populated DB migrates with zero data loss, parent_uuid correctly populated.

### 1.3 Trigger + Index Recreation

**Tests first:** Write `test_uuid_immutability_trigger`, `test_self_parent_uuid_insert_trigger`, `test_self_parent_uuid_update_trigger`.

**Implementation:**
1. Step 10: Recreate all 8 triggers — 5 existing + 3 new. **Existing 5 trigger DDL must be copied exactly from Migration 1** (type_id immutability, entity_type check on insert/update, self-parent type_id check on insert/update). New 3: uuid immutability per R10, self-parent-uuid check on insert per R11, self-parent-uuid check on update per R12.
2. Step 11: Recreate all 4 indexes (3 existing + idx_parent_uuid per I9)
3. Verify all 8 triggers fire correctly post-recreation (both existing and new)

**Done criteria:** 8 triggers fire correctly, 4 indexes exist. Verified via `SELECT name FROM sqlite_master WHERE type='trigger'`.

### 1.4 Migration Error Handling + Idempotency

**Tests first:** Write `test_migration_rollback_on_failure`.

**Implementation:**
1. Wrap steps 2-13 (BEGIN IMMEDIATE through schema_version UPDATE) in try/except:
   - try: steps 2-11 (DDL/DML), step 12 (UPDATE schema_version to '2'), step 13 (`conn.commit()`)
   - except: `conn.rollback()`, then re-raise
   - finally: re-enable `PRAGMA foreign_keys = ON` — this runs outside the transaction (after commit or rollback), which is correct because PRAGMA foreign_keys must be set outside transactions. If the connection is corrupted and the PRAGMA fails, the exception propagates naturally.
2. Step 14: Post-migration `PRAGMA foreign_key_check` (runs after transaction completes, outside try/except)
3. Register `2: _migrate_to_uuid_pk` in MIGRATIONS dict (R9)
4. Verify outer `_migrate()` loop completes cleanly — `EntityDatabase.__init__` succeeds with schema_version=2. **Safety note:** The outer `_migrate()` loop is safe because it checks schema_version before each migration; after Migration 2 commits schema_version='2', the loop will not re-enter Migration 2 on subsequent calls.

**Done criteria:** Failed migration rolls back cleanly. Idempotent on re-run. FK check passes post-migration. EntityDatabase initializes successfully.

## Phase 2: Core Database API

**File:** `plugins/iflow/hooks/lib/entity_registry/database.py`

### 2.1 `_resolve_identifier` Method

**Tests first:** Write `test_resolve_identifier_with_uuid`, `test_resolve_identifier_with_type_id`, `test_resolve_identifier_not_found`.

**Implementation:**
1. Add `_resolve_identifier(self, identifier) -> tuple[str, str]` method per I2
2. Returns `(uuid, type_id)` tuple — both values needed by callers like set_parent
3. Normalize to lowercase, match against `_UUID_V4_RE`
4. UUID match → SELECT by uuid; no match → SELECT by type_id
5. Raise `ValueError` if no row found

**Done criteria:** Returns (uuid, type_id) tuple for both UUID and type_id inputs. Raises ValueError on miss.

### 2.2 `register_entity` Update

**Note:** Independent of 2.1 — `register_entity` does not use `_resolve_identifier`. Can be implemented in parallel with 2.1.

**Tests first:** Write `test_register_returns_uuid_v4_format`, `test_register_duplicate_returns_existing_uuid`.

**Implementation:**
1. Generate `entity_uuid = str(uuid_mod.uuid4())` before INSERT
2. Add uuid column to INSERT statement
3. After INSERT OR IGNORE, always SELECT uuid by type_id (TD-4, R35 — always-SELECT pattern). **Commit ordering:** INSERT and SELECT execute within the same connection's autocommit context — no explicit transaction management needed since the existing method already uses autocommit. The SELECT reads the authoritative uuid value regardless of whether INSERT succeeded or was ignored.
4. Return SELECT result (existing uuid on duplicate, new uuid on fresh insert)

**Done criteria:** Returns valid UUID v4. Duplicates return existing UUID.

### 2.3 `set_parent` Update

**Tests first:** Write `test_set_parent_mixed_identifiers`, `test_set_parent_updates_both_parent_columns`.

**Implementation:**
1. Resolve both params via `_resolve_identifier` — unpack `(child_uuid, child_type_id)` and `(parent_uuid, parent_type_id)` (I4)
2. Self-parent check using UUIDs
3. Circular reference CTE joins on uuid/parent_uuid
4. UPDATE sets both `parent_type_id = parent_type_id` (from `_resolve_identifier` result, NOT the raw input parameter) and `parent_uuid = parent_uuid` (from `_resolve_identifier` result) — this ensures normalized/resolved values are stored (R16, AC-28)
5. Return child_uuid

**Done criteria:** Mixed identifiers work. Both parent columns updated atomically with resolved (not raw) values.

### 2.4 `get_entity` Update

**Tests first:** Write `test_get_entity_by_uuid`, `test_get_entity_by_type_id`, `test_get_entity_not_found_returns_none` — covering AC-9, AC-10, AC-11.

**Implementation:**
1. Try `_resolve_identifier`, catch ValueError → return None (R26)
2. SELECT by resolved uuid
3. Return dict(row) with uuid field included

**Done criteria:** Dual-read works. Missing entity returns None.

### 2.5 `get_lineage` + `update_entity` Updates

**Tests first:** Write `test_get_lineage_with_uuid`, `test_update_entity_with_uuid`.

**Implementation — get_lineage:**
1. Try `_resolve_identifier`, catch ValueError → return [] (R26)
2. Update `_lineage_up` CTE to join on uuid/parent_uuid (I6)
3. Update `_lineage_down` CTE to join on uuid/parent_uuid (I6)

**Implementation — update_entity:**
1. Resolve via `_resolve_identifier`, let ValueError propagate (R26)
2. WHERE clause uses resolved uuid

**Done criteria:** Lineage traversal uses uuid. Update works with either identifier.

### 2.6 `export_lineage_markdown` + `_export_tree` Updates

**Tests first:** Write `test_export_uses_uuid_internally` — verify export produces correct markdown with uuid-keyed internals while display still shows type_id (AC-25, capture-compare approach).

**Implementation:**
1. When type_id is None: root-finding query changes from `SELECT type_id` to `SELECT uuid` — roots are identified by uuid for CTE starting points (I6)
2. When type_id provided: resolve via `_resolve_identifier` to get uuid
3. Update `_export_tree` CTE to join on uuid/parent_uuid (I6)
4. Update truncation check: leaf_ids from `row['uuid']`, child check via `WHERE parent_uuid IN (...)` (I6)

**Done criteria:** Export uses uuid internally. Display still shows type_id.

## Phase 3: Server Helpers

**File:** `plugins/iflow/hooks/lib/entity_registry/server_helpers.py`

### 3.1 `render_tree` Internal Updates

**Tests first:** Update `_make_entity` helper in test_server_helpers.py to include `uuid` and `parent_uuid` fields. **Helper must generate internally consistent values:** each entity gets a deterministic uuid (e.g., `str(uuid.uuid5(uuid.NAMESPACE_DNS, type_id))`), and `parent_uuid` references the uuid of an existing entity in the test fixture (not a random value). Existing render_tree tests will crash with KeyError without this update.

**Implementation:**
1. Key `by_id` dict on `entity["uuid"]` (I7)
2. Build `children` map from `entity.get("parent_uuid")` (I7)
3. Root lookup uses uuid key
4. `_render_node` traverses uuid keys
5. `_format_entity_label` unchanged — still shows type_id

**Done criteria:** Tree renders correctly with uuid-keyed internals. Display unchanged.

### 3.2 Process Handler Updates

**Depends on 3.1** — process handlers pass uuid values to render_tree; render_tree must be uuid-keyed first.

**Implementation:**
1. `_process_register_entity`: Capture UUID return, construct type_id from inputs (no extra DB call per C4, I8), format dual-identity message
2. `_process_get_lineage`: Pass `entities[0]["uuid"]` to `render_tree` (C4). **Directional note:** `entities[0]` is always the start entity regardless of traversal direction (up or down) — `get_lineage` returns the start entity first in both cases. Handle error messages for UUID input.

**Done criteria:** Messages show both UUID and type_id.

## Phase 4: MCP Server

**File:** `plugins/iflow/mcp/entity_server.py`

### 4.1 Tool Handler Message Updates

**Tests first:** Write `test_set_parent_handler_dual_identity_message`, `test_update_entity_handler_dual_identity_message` — verify MCP tool handlers return messages containing both UUID and type_id in the response text. Test via the server helper functions that these handlers call.

**Implementation:**
1. `set_parent` handler: Capture UUID return, get_entity for both child and parent, format dual-identity message (C5, I8)
2. `update_entity` handler: Get entity after update for dual-identity message (I8). Error path messages remain unchanged.
3. `get_entity` handler: No changes needed (uuid field included automatically)

**Done criteria:** MCP responses include both UUID and type_id.

## Phase 5: Test Finalization & Verification

**Files:** `test_database.py`, `test_server_helpers.py`, `test_backfill.py`

### 5.1 Existing Test Assertion Updates

**Implementation per C6:**
1. `test_entities_has_10_columns` → assert 12 columns
2. `test_entities_column_names` → add uuid, parent_uuid
3. `test_type_id_is_primary_key` → assert uuid is PK, type_id is not
4. `test_schema_version_is_1` → assert schema_version == "2"
5. `test_has_five_triggers` → assert 8 triggers
6. Return value assertions → UUID format
7. Raw SQL INSERT tests — explicitly: `test_entity_type_check_constraint`, `test_valid_entity_types_accepted`, `test_self_parent_on_insert` → include uuid column via `str(uuid.uuid4())`. **Note:** `test_self_parent_on_insert` needs TWO test cases: one for the existing parent_type_id self-parent trigger and one for the new parent_uuid self-parent trigger (R11)
8. Server helper message assertions → dual-identity format

**Done criteria:** All 184+ existing tests pass with updated assertions.

### 5.2 Full Suite Verification

1. Run full entity registry test suite: `plugins/iflow/.venv/bin/python -m pytest plugins/iflow/hooks/lib/entity_registry/ -v`
2. Verify 0 failures
3. Verify new test count: target 15 new test functions, hard minimum 10 per AC-27
4. Run backfill test if available
5. Run entity server bootstrap test: `bash plugins/iflow/mcp/test_entity_server.sh`

**Done criteria:** All tests pass. No regressions. Minimum test count met.

## Risk Mitigation Checkpoints

| After Phase | Verify |
|-------------|--------|
| Phase 1 | Migration runs on fresh + populated DBs. Rollback works. FK check passes. EntityDatabase.__init__ completes. |
| Phase 2 | Dual-read resolves both identifier types. All API methods return UUIDs. _resolve_identifier returns (uuid, type_id) tuple. |
| Phase 3 | Tree display unchanged. Messages show dual identity. _make_entity helper updated. |
| Phase 4 | MCP tools accept both UUID and type_id. Responses formatted correctly. Error paths unchanged. |
| Phase 5 | 184+ tests pass. No regressions. 10+ new tests added (target 15). |

## Files Changed Summary

| File | Change Type |
|------|------------|
| `database.py` | Major modification — migration function, _resolve_identifier, all API methods |
| `server_helpers.py` | Moderate modification — render_tree internals, process handlers |
| `entity_server.py` | Minor modification — set_parent and update_entity message formats |
| `test_database.py` | Major modification — new migration/API tests, existing assertion updates |
| `test_server_helpers.py` | Minor modification — _make_entity helper, message assertions |
| `backfill.py` | No changes |
