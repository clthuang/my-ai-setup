# Design: SQLite DB Locking Fixes

## Prior Art Research

### Codebase Patterns
- `semantic_memory/database.py` `_migrate()` (line ~780): no outer transaction, individual commits per migration, 4 `executescript` calls across migrations 1-3
- `entity_registry/database.py` `_in_transaction` flag + `_commit()` helper + `transaction()` context manager: well-designed transaction architecture, but `begin_immediate()` doesn't participate
- `entity_registry/database.py` migration 5: `SELECT * FROM workflow_phases` — fragile; migration 6 already uses explicit column lists (good pattern to follow)
- Migration 2 in entity_registry (line 152): also uses `SELECT *` from entities table for UUID migration — noted but lower risk since entities table structure is stable

### External Research
- SQLite `executescript()` issues implicit COMMIT — incompatible with outer `BEGIN IMMEDIATE`
- SQLite `in_transaction` property on Connection reflects actual transaction state
- `BEGIN IMMEDIATE` acquires write lock upfront — prevents concurrent migration race

---

## Architecture Overview

Three independent fixes, no shared state between them:

```
Fix 1: semantic_memory/database.py
  _migrate() → wrap in BEGIN IMMEDIATE
  Migrations 1-3 → convert executescript to execute

Fix 2: entity_registry/database.py
  begin_immediate() → set _in_transaction = True

Fix 3: entity_registry/database.py
  Migration 5 → explicit column lists in INSERT/SELECT
```

---

## Components

### C1: MemoryDatabase Migration Lock (FR-1)

**File:** `plugins/pd/hooks/lib/semantic_memory/database.py`

Two changes:
1. **`_migrate()` method**: Wrap the migration loop in `BEGIN IMMEDIATE` / `COMMIT` / `ROLLBACK`
2. **Migrations 1-3**: Convert all `executescript()` calls to sequential `execute()` calls

### C2: EntityDatabase begin_immediate Fix (FR-2)

**File:** `plugins/pd/hooks/lib/entity_registry/database.py`

Single change to `begin_immediate()`: set `self._in_transaction = True` before yield, reset in `finally`. Add nesting guard matching `transaction()`.

### C3: EntityDatabase Migration 5 Column Lists (FR-3)

**File:** `plugins/pd/hooks/lib/entity_registry/database.py`

Single change to `_expand_workflow_phase_check()`: replace `SELECT *` with explicit 7-column list.

---

## Technical Decisions

### TD-1: executescript conversion scope

**Decision:** Convert ALL `executescript` calls in migrations 1-3 to `execute()`. Do NOT convert `executescript` calls in `_create_fts5_objects` helper — instead, call FTS5 object creation AFTER the migration transaction commits (it was already conditional on FTS5 availability).

**Rationale:** `_create_fts5_objects` uses f-string interpolation for 3 CREATE TRIGGER statements and a CREATE VIRTUAL TABLE. These are complex DDL statements. Rather than splitting them into 4 separate `execute()` calls with f-strings, keep `_create_fts5_objects` as-is but call it outside the migration transaction. FTS5 creation is idempotent (uses IF NOT EXISTS patterns) and is not critical to migration correctness.

**Updated migration flow:**
```python
self._conn.execute("BEGIN IMMEDIATE")
try:
    # Run migrations (using execute(), not executescript)
    ...
    self._conn.commit()
except:
    self._conn.rollback()
    raise

# FTS5 setup runs outside transaction (idempotent, uses executescript)
if self._fts5_available:
    _create_fts5_objects(self._conn)
```

### TD-2: begin_immediate nesting guard

**Decision:** Add `RuntimeError` on nesting, matching `transaction()` pattern.
**Rationale:** `transaction()` already raises on nesting (line 1157). `begin_immediate()` should be consistent.

### TD-3: Migration 2 SELECT * in entity_registry

**Decision:** Leave migration 2's `SELECT * FROM entities` (line 152) unchanged.
**Rationale:** Migration 2 reads rows into Python, generates UUIDs per row, then inserts into a new table with explicit column mapping. The `SELECT *` is used to read data into `Row` objects accessed by column name, not as a bulk INSERT. The pattern is safe — the Python code adapts to whatever columns exist.

---

## Interfaces

### I1: Updated `_migrate()` — semantic_memory/database.py

```python
def _migrate(self) -> None:
    # Bootstrap _metadata (idempotent, outside transaction)
    self._conn.execute(
        "CREATE TABLE IF NOT EXISTS _metadata "
        "(key TEXT PRIMARY KEY, value TEXT NOT NULL)"
    )
    self._conn.commit()

    # Acquire write lock for entire migration chain
    self._conn.execute("BEGIN IMMEDIATE")
    try:
        current = self.get_schema_version()
        target = max(MIGRATIONS) if MIGRATIONS else 0
        for version in range(current + 1, target + 1):
            migration_fn = MIGRATIONS[version]
            migration_fn(self._conn, fts5_available=self._fts5_available)
            self._conn.execute(
                "INSERT INTO _metadata (key, value) VALUES (?, ?) "
                "ON CONFLICT(key) DO UPDATE SET value = excluded.value",
                ("schema_version", str(version)),
            )
        self._conn.commit()
    except Exception:
        self._conn.rollback()
        raise

    # FTS5 setup (idempotent, outside transaction)
    if self._fts5_available:
        _create_fts5_objects(self._conn)
```

### I2: Updated `_create_initial_schema()` — line 66

Convert `executescript` to sequential `execute()`:
```python
def _create_initial_schema(conn, **_kwargs):
    conn.execute("""CREATE TABLE IF NOT EXISTS entries (...)""")
    conn.execute("""CREATE TABLE IF NOT EXISTS _metadata (...)""")
    # FTS5 objects created separately in _migrate() after transaction
```

### I3: Updated `_add_source_hash_and_created_timestamp()` — line 153

```python
def _add_source_hash_and_created_timestamp(conn, **_kwargs):
    conn.execute("ALTER TABLE entries ADD COLUMN source_hash TEXT")
    conn.execute("ALTER TABLE entries ADD COLUMN created_timestamp_utc REAL")
    conn.execute(
        "UPDATE entries SET created_timestamp_utc = CAST(strftime('%s', created_at) AS REAL)"
    )
```

### I4: Updated `_enforce_not_null_columns()` — line 201

Convert the `executescript` (table rebuild DDL) to sequential `execute()` calls. Each statement in the multi-statement string becomes a separate `execute()` call.

### I5: Updated `begin_immediate()` — entity_registry/database.py

```python
@contextmanager
def begin_immediate(self):
    if self._in_transaction:
        raise RuntimeError("Nested transactions not supported")
    self._conn.execute("BEGIN IMMEDIATE")
    self._in_transaction = True
    try:
        yield self._conn
        self._conn.execute("COMMIT")
    except Exception:
        try:
            self._conn.execute("ROLLBACK")
        except sqlite3.Error:
            pass
        raise
    finally:
        self._in_transaction = False
```

### I6: Updated `_expand_workflow_phase_check()` — migration 5

```sql
-- Replace line 466:
INSERT INTO workflow_phases_new (type_id, workflow_phase, kanban_column,
    last_completed_phase, mode, backward_transition_reason, updated_at)
SELECT type_id, workflow_phase, kanban_column,
    last_completed_phase, mode, backward_transition_reason, updated_at
FROM workflow_phases
```

---

## Risks

| Risk | Likelihood | Impact | Mitigation |
|------|-----------|--------|------------|
| executescript → execute changes migration 1 DDL behavior | Low | Medium | Test schema matches after migration via PRAGMA table_info |
| FTS5 creation outside transaction fails | Low | Low | FTS5 uses IF NOT EXISTS, is retried on next DB open |
| begin_immediate nesting guard breaks callers | Low | Low | Only `transaction()` callers nest — they already check. `begin_immediate` callers use raw SQL. |

---

## File Change Summary

| File | Change Type | Description |
|------|-------------|-------------|
| `plugins/pd/hooks/lib/semantic_memory/database.py` | Modify | `_migrate()` wrapped in BEGIN IMMEDIATE; migrations 1-3 converted from executescript to execute; FTS5 creation moved outside transaction |
| `plugins/pd/hooks/lib/entity_registry/database.py` | Modify | `begin_immediate()` sets `_in_transaction` flag; migration 5 uses explicit column lists |
| `plugins/pd/hooks/lib/semantic_memory/test_database.py` | Modify | Add concurrent init test, migration atomicity test |
| `plugins/pd/hooks/lib/entity_registry/test_database.py` | Modify | Add begin_immediate + register_entity test |
