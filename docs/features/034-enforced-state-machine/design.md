# Design: Enforced State Machine (Phase 1)

## Prior Art Research

### Codebase Patterns

- **PreToolUse deny pattern:** `pre-commit-guard.sh` reads stdin JSON, extracts tool_input via python3, uses `output_block()`/`output_allow()` helpers from `common.sh`. The `yolo-guard.sh` hook adds a fast-path string check (`*".meta.json"*`) before JSON parsing — apply this optimization.
- **MCP tool registration:** `workflow_state_server.py` uses `@mcp.tool()` decorator + `_process_*()` functions + `@_with_error_handling` + `@_catch_value_error` decorator stack. Module globals `_db`, `_engine`, `_artifacts_root` set during `lifespan()`.
- **Atomic file writes:** `_write_meta_json_fallback()` uses `NamedTemporaryFile` + `os.replace()` for crash safety. Reuse this pattern for `_project_meta_json()`.
- **Path validation:** `_validate_feature_type_id()` defends against path traversal (null bytes, realpath check). All new tools accepting `feature_type_id` must call this.
- **Entity metadata storage:** `db.update_entity(type_id, metadata={...})` shallow-merges metadata dict. Phase timing stored under `metadata.phase_timing` key.

### External Research

- **Hook exit semantics:** exit 0 + `permissionDecision: "deny"` is the canonical block path. Exit 2 is a hard-block alternative (stderr shown to Claude). Stick with exit 0 + deny JSON for consistency with existing hooks.
- **Known issue #4362:** `approve: false` was ignored in some CC versions — use `permissionDecision` field, not `approve`. Our existing hooks already use the correct field.
- **CQRS synchronous projection:** Update both write model and read model within the same operation. Projection called inline after DB commit, before returning to caller. No eventual consistency concerns.

## Architecture Overview

### Component Diagram

```
┌─────────────────────────────────────────────────────────┐
│                    LLM Agent Layer                       │
│  (skills, commands — 9 write sites updated)             │
│                                                         │
│  create-feature.md ──┐                                  │
│  decomposing/SKILL ──┤  Call MCP tools                  │
│  workflow-state/SKILL─┤  instead of                     │
│  workflow-trans/SKILL─┤  Write/Edit                     │
│  finish-feature.md ──┤                                  │
│  create-project.md ──┘                                  │
└────────┬────────────────────────┬───────────────────────┘
         │ MCP tool calls         │ Write/Edit tool calls
         │                        │
         ▼                        ▼
┌─────────────────┐    ┌─────────────────────────┐
│  workflow_state  │    │  meta-json-guard.sh     │
│  _server.py     │    │  (PreToolUse hook)       │
│                  │    │                          │
│  New tools:      │    │  *.meta.json? → DENY    │
│  • init_feature  │    │  + log to JSONL          │
│  • init_project  │    │  other files? → ALLOW    │
│  • activate      │    └─────────────────────────┘
│                  │
│  Extended:       │
│  • transition    │
│  • complete      │
│                  │
│  Shared:         │
│  • _project_     │
│    meta_json()   │
└────────┬─────────┘
         │
    ┌────┴────┐
    ▼         ▼
┌────────┐ ┌──────────────┐
│ SQLite │ │ .meta.json   │
│ DB     │ │ (projection) │
│(write) │ │ (read model) │
└────────┘ └──────────────┘
```

### Data Flow

**Normal path (all 9 write sites):**
```
LLM → MCP tool call → _process_*() → engine/db mutation → _project_meta_json() → .meta.json written → response to LLM
```

**Blocked path (any residual direct write):**
```
LLM → Write/Edit(.meta.json) → meta-json-guard.sh → DENY + log entry → LLM receives deny reason
```

**Degraded path (DB unavailable, unchanged):**
```
engine.transition_phase() → DB fails → _write_meta_json_fallback() → .meta.json written directly
```

## Components

### C1: `meta-json-guard.sh` (New File)

**Location:** `plugins/iflow/hooks/meta-json-guard.sh`

**Responsibility:** Block all LLM Write/Edit tool calls targeting `*.meta.json` files. Log blocked attempts.

**Design decisions:**
- **Fast-path optimization:** Check `*".meta.json"*` via bash string match before any JSON parsing. ~99% of Write/Edit calls don't target `.meta.json`, so this avoids the python3/jq overhead. Borrowed from `yolo-guard.sh` pattern.
- **Path extraction:** Use python3 inline (same as `pre-commit-guard.sh`) to parse `tool_input.file_path` from stdin JSON. Suppress stderr (`2>/dev/null`) per hook safety convention.
- **Logging:** Append JSONL to `~/.claude/iflow/meta-json-guard.log` before returning deny. Use `date -u +%Y-%m-%dT%H:%M:%SZ` for timestamp. Extract feature_id via bash regex on path.
- **Source common.sh:** For `escape_json()`, `detect_project_root()`, `install_err_trap()`, `output_block()` pattern.

**Internal structure:**
```bash
#!/usr/bin/env bash
set -euo pipefail

SCRIPT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]:-$0}")" && pwd)"
source "${SCRIPT_DIR}/lib/common.sh"
install_err_trap

# Read all stdin once
INPUT=$(cat)

# Fast path: skip JSON parse if no .meta.json reference
if [[ "$INPUT" != *".meta.json"* ]]; then
    echo '{}'
    exit 0
fi

# Extract file_path from tool_input
FILE_PATH=$(echo "$INPUT" | python3 -c "
import json, sys
try:
    data = json.load(sys.stdin)
    print(data.get('tool_input', {}).get('file_path', ''))
except:
    print('')
" 2>/dev/null)

# Check if target is .meta.json
if [[ "$FILE_PATH" != *".meta.json" ]]; then
    echo '{}'
    exit 0
fi

# Log blocked attempt (FR-11)
log_blocked_attempt "$FILE_PATH"

# Deny
output_block "Direct .meta.json writes are blocked. Use MCP workflow tools instead: transition_phase() to enter a phase, complete_phase() to finish a phase, or init_feature_state() to create a new feature."
exit 0
```

**`log_blocked_attempt` function:**
```bash
log_blocked_attempt() {
    local file_path="$1"
    local log_dir="$HOME/.claude/iflow"
    local log_file="$log_dir/meta-json-guard.log"
    local timestamp tool_name feature_id

    mkdir -p "$log_dir"
    timestamp=$(date -u +%Y-%m-%dT%H:%M:%SZ)

    # Extract tool name from INPUT (already in scope)
    tool_name=$(echo "$INPUT" | python3 -c "
import json, sys
try:
    print(json.load(sys.stdin).get('tool_name', 'unknown'))
except:
    print('unknown')
" 2>/dev/null)

    # Extract feature_id from path
    if [[ "$file_path" =~ features/([^/]+)/\.meta\.json ]]; then
        feature_id="${BASH_REMATCH[1]}"
    elif [[ "$file_path" =~ projects/([^/]+)/\.meta\.json ]]; then
        feature_id="${BASH_REMATCH[1]}"
    else
        feature_id="unknown"
    fi

    # Append JSONL (>> is atomic for lines < PIPE_BUF on POSIX)
    echo "{\"timestamp\":\"$timestamp\",\"tool\":\"$tool_name\",\"path\":\"$(escape_json "$file_path")\",\"feature_id\":\"$feature_id\"}" >> "$log_file"
}
```

**Registration in `hooks.json`:** Insert at index 2 in `PreToolUse` array (after `Bash`/pre-commit-guard at index 1, before `.*`/yolo-guard at index 2).

### C2: `_project_meta_json()` (New Function)

**Location:** `plugins/iflow/mcp/workflow_state_server.py` (module-level function)

**Responsibility:** Regenerate `.meta.json` from current DB + entity state after every successful mutation.

**Design decisions:**
- **Placed in MCP server, not engine.** The engine is a state machine; file projection is a server-layer concern. Keeps engine testable without filesystem coupling.
- **Atomic write:** Reuse `NamedTemporaryFile` + `os.replace()` pattern from `_write_meta_json_fallback()`.
- **Fail-open for projection:** If projection fails (disk full, permissions), DB state is preserved. MCP tool returns success with a warning field. The LLM can still proceed; `.meta.json` will be stale until next successful projection.
- **Uses `_db` and `_engine` globals** — same as all other MCP server processing functions.

**Internal structure:**
```python
def _project_meta_json(
    db: EntityDatabase,
    feature_type_id: str,
    feature_dir: str | None = None,
) -> str | None:
    """Regenerate .meta.json from DB state. Returns warning string or None."""
    entity = db.get_entity(feature_type_id)
    if entity is None:
        return f"entity not found: {feature_type_id}"

    if feature_dir is None:
        feature_dir = entity.artifact_path
        if not feature_dir:
            return f"artifact_path not set for entity: {feature_type_id}"

    meta_path = os.path.join(feature_dir, ".meta.json")
    metadata = entity.metadata or {}
    phase_timing = metadata.get("phase_timing", {})

    # Build .meta.json structure
    meta = {
        "id": metadata.get("id", ""),
        "slug": metadata.get("slug", ""),
        "mode": metadata.get("mode", "standard"),
        "status": entity.status or "active",
        "created": entity.created_at or _iso_now(),
        "branch": metadata.get("branch", ""),
    }

    # Optional fields
    if metadata.get("brainstorm_source"):
        meta["brainstorm_source"] = metadata["brainstorm_source"]
    if metadata.get("backlog_source"):
        meta["backlog_source"] = metadata["backlog_source"]

    # Workflow state
    meta["lastCompletedPhase"] = metadata.get("last_completed_phase")

    # Phases from phase_timing metadata
    phases = {}
    for phase_name, timing in phase_timing.items():
        phase_entry = {}
        if timing.get("started"):
            phase_entry["started"] = timing["started"]
        if timing.get("completed"):
            phase_entry["completed"] = timing["completed"]
        if timing.get("iterations") is not None:
            phase_entry["iterations"] = timing["iterations"]
        if timing.get("reviewerNotes"):
            phase_entry["reviewerNotes"] = timing["reviewerNotes"]
        if phase_entry:
            phases[phase_name] = phase_entry
    meta["phases"] = phases

    # Skipped phases
    if metadata.get("skipped_phases"):
        meta["skippedPhases"] = metadata["skipped_phases"]

    # Atomic write
    try:
        tmp_name = None
        with tempfile.NamedTemporaryFile(
            mode="w",
            dir=os.path.dirname(meta_path),
            suffix=".tmp",
            delete=False,
            encoding="utf-8",
        ) as fd:
            tmp_name = fd.name
            json.dump(meta, fd, indent=2)
            fd.write("\n")
        os.replace(tmp_name, meta_path)
        return None  # success
    except BaseException as exc:
        if tmp_name is not None:
            try:
                os.unlink(tmp_name)
            except OSError:
                pass
        return f"projection failed: {exc}"
```

**Caller integration:** Each `_process_*()` function calls `_project_meta_json()` after DB mutation succeeds. If it returns a warning, include it in the MCP response JSON as `"projection_warning": "..."`.

### C3: `init_feature_state` (New MCP Tool)

**Location:** `plugins/iflow/mcp/workflow_state_server.py`

**Responsibility:** Create initial feature state in DB + entity registry, then project `.meta.json`.

**Design decisions:**
- **Registers entity first**, then creates workflow phase, then projects. If entity already exists, update metadata only (idempotent for retries).
- **No gate validation** — creation is not a transition.
- **Reuses `_validate_feature_type_id`** pattern for path safety, but relaxes the "directory must exist" check (directory is being created).

**Internal structure:**
```python
@_with_error_handling
def _process_init_feature_state(
    db: EntityDatabase,
    feature_dir: str,
    feature_id: str,
    slug: str,
    mode: str,
    branch: str,
    brainstorm_source: str | None,
    backlog_source: str | None,
    status: str,
) -> str:
    feature_type_id = f"feature:{feature_id}-{slug}"

    # Register or update entity
    metadata = {
        "id": feature_id,
        "slug": slug,
        "mode": mode,
        "branch": branch,
        "phase_timing": {},
    }
    if brainstorm_source:
        metadata["brainstorm_source"] = brainstorm_source
    if backlog_source:
        metadata["backlog_source"] = backlog_source

    existing = db.get_entity(feature_type_id)
    if existing is None:
        db.register_entity(
            entity_type="feature",
            entity_id=f"{feature_id}-{slug}",
            name=slug,
            artifact_path=feature_dir,
            status=status,
            metadata=metadata,
        )
    else:
        db.update_entity(feature_type_id, status=status, metadata=metadata)

    # Project .meta.json
    warning = _project_meta_json(db, feature_type_id, feature_dir)

    result = {
        "created": True,
        "feature_type_id": feature_type_id,
        "status": status,
        "meta_json_path": os.path.join(feature_dir, ".meta.json"),
    }
    if warning:
        result["projection_warning"] = warning
    return json.dumps(result)
```

### C4: `init_project_state` (New MCP Tool)

**Location:** `plugins/iflow/mcp/workflow_state_server.py`

**Responsibility:** Create initial project `.meta.json` with project-specific schema (features array, milestones).

**Design decisions:**
- **Does NOT use `_project_meta_json()`** — projects have a different schema (no `phases{}`, `lastCompletedPhase`, `branch`, `mode`). Writes directly.
- **Registers entity** in entity registry for lineage tracking.
- **Atomic write** via same `NamedTemporaryFile` + `os.replace()` pattern.

**Internal structure:**
```python
@_with_error_handling
def _process_init_project_state(
    db: EntityDatabase,
    project_dir: str,
    project_id: str,
    slug: str,
    features: str,  # JSON string
    milestones: str,  # JSON string
    brainstorm_source: str | None,
) -> str:
    project_type_id = f"project:{project_id}-{slug}"

    # Parse JSON params
    features_list = json.loads(features)
    milestones_list = json.loads(milestones)

    # Register entity
    existing = db.get_entity(project_type_id)
    if existing is None:
        db.register_entity(
            entity_type="project",
            entity_id=f"{project_id}-{slug}",
            name=slug,
            artifact_path=project_dir,
            status="active",
        )

    # Build project .meta.json
    meta = {
        "id": project_id,
        "slug": slug,
        "status": "active",
        "created": _iso_now(),
        "features": features_list,
        "milestones": milestones_list,
    }
    if brainstorm_source:
        meta["brainstorm_source"] = brainstorm_source

    # Atomic write
    meta_path = os.path.join(project_dir, ".meta.json")
    _atomic_json_write(meta_path, meta)

    return json.dumps({
        "created": True,
        "project_type_id": project_type_id,
        "meta_json_path": meta_path,
    })
```

### C5: `activate_feature` (New MCP Tool)

**Location:** `plugins/iflow/mcp/workflow_state_server.py`

**Responsibility:** Transition a planned feature to active status.

**Design decisions:**
- **Pre-condition check:** Must be in `"planned"` status. Reject otherwise.
- **Uses existing `db.update_entity(status="active")`** — no schema change needed.
- **Projects `.meta.json`** via `_project_meta_json()` after status update.

**Internal structure:**
```python
@_with_error_handling
@_catch_value_error
def _process_activate_feature(
    db: EntityDatabase,
    feature_type_id: str,
) -> str:
    entity = db.get_entity(feature_type_id)
    if entity is None:
        raise ValueError(f"feature_not_found: {feature_type_id}")
    if entity.status != "planned":
        raise ValueError(
            f"invalid_transition: feature status is '{entity.status}', "
            f"expected 'planned' for activation"
        )

    db.update_entity(feature_type_id, status="active")

    warning = _project_meta_json(db, feature_type_id)

    result = {
        "activated": True,
        "feature_type_id": feature_type_id,
        "previous_status": "planned",
        "new_status": "active",
    }
    if warning:
        result["projection_warning"] = warning
    return json.dumps(result)
```

### C6: Extended `transition_phase` (Modified)

**Location:** `plugins/iflow/mcp/workflow_state_server.py` — modify `_process_transition_phase` and `transition_phase` tool.

**Changes:**
1. Add `skipped_phases: str | None = None` parameter
2. If `skipped_phases` provided, parse JSON and store in entity metadata
3. Store phase started timestamp in `metadata.phase_timing`
4. Call `_project_meta_json()` after successful transition

**Modified `_process_transition_phase`:**
```python
@_with_error_handling
@_catch_value_error
def _process_transition_phase(
    engine: WorkflowStateEngine,
    db: EntityDatabase,
    feature_type_id: str,
    target_phase: str,
    yolo_active: bool,
    skipped_phases: str | None,
) -> str:
    response = engine.transition_phase(feature_type_id, target_phase, yolo_active)
    transitioned = all(r.allowed for r in response.results)

    if transitioned:
        # Store phase timing
        entity = db.get_entity(feature_type_id)
        metadata = (entity.metadata if entity else {}) or {}
        phase_timing = metadata.get("phase_timing", {})
        phase_timing.setdefault(target_phase, {})
        phase_timing[target_phase]["started"] = _iso_now()
        metadata["phase_timing"] = phase_timing

        # Store skipped phases if provided
        if skipped_phases:
            metadata["skipped_phases"] = json.loads(skipped_phases)

        # Store last_completed_phase for projection
        # (transition doesn't complete, but we need to track current state)
        db.update_entity(feature_type_id, metadata=metadata)

        # Project .meta.json
        warning = _project_meta_json(db, feature_type_id)

    result = {
        "transitioned": transitioned,
        "results": [_serialize_result(r) for r in response.results],
        "degraded": response.degraded,
    }
    if transitioned:
        result["started_at"] = phase_timing[target_phase]["started"]
        if skipped_phases:
            result["skipped_phases_stored"] = True
        if warning:
            result["projection_warning"] = warning
    return json.dumps(result)
```

### C7: Extended `complete_phase` (Modified)

**Location:** `plugins/iflow/mcp/workflow_state_server.py` — modify `_process_complete_phase` and `complete_phase` tool.

**Changes:**
1. Add `iterations: int | None = None` and `reviewer_notes: str | None = None` parameters
2. Store timing metadata in entity after engine completes phase
3. Call `_project_meta_json()` after successful completion

**Modified `_process_complete_phase`:**
```python
@_with_error_handling
@_catch_value_error
def _process_complete_phase(
    engine: WorkflowStateEngine,
    db: EntityDatabase,
    feature_type_id: str,
    phase: str,
    iterations: int | None,
    reviewer_notes: str | None,
) -> str:
    state = engine.complete_phase(feature_type_id, phase)

    # Store timing metadata
    entity = db.get_entity(feature_type_id)
    metadata = (entity.metadata if entity else {}) or {}
    phase_timing = metadata.get("phase_timing", {})
    phase_timing.setdefault(phase, {})
    phase_timing[phase]["completed"] = _iso_now()
    if iterations is not None:
        phase_timing[phase]["iterations"] = iterations
    if reviewer_notes:
        phase_timing[phase]["reviewerNotes"] = json.loads(reviewer_notes)
    metadata["phase_timing"] = phase_timing
    metadata["last_completed_phase"] = phase

    # Update terminal status
    if state.current_phase == phase:  # no next phase = terminal
        db.update_entity(feature_type_id, status="completed", metadata=metadata)
    else:
        db.update_entity(feature_type_id, metadata=metadata)

    # Project .meta.json
    warning = _project_meta_json(db, feature_type_id)

    result = _serialize_state(state)
    result["completed_at"] = phase_timing[phase]["completed"]
    if warning:
        result["projection_warning"] = warning
    return json.dumps(result)
```

### C8: Shared Utility — `_atomic_json_write()` (New Function)

**Location:** `plugins/iflow/mcp/workflow_state_server.py`

**Responsibility:** Atomic JSON file write via `NamedTemporaryFile` + `os.replace()`.

```python
def _atomic_json_write(path: str, data: dict) -> None:
    """Atomic JSON write: NamedTemporaryFile + os.replace()."""
    tmp_name = None
    try:
        with tempfile.NamedTemporaryFile(
            mode="w",
            dir=os.path.dirname(path),
            suffix=".tmp",
            delete=False,
            encoding="utf-8",
        ) as fd:
            tmp_name = fd.name
            json.dump(data, fd, indent=2)
            fd.write("\n")
        os.replace(tmp_name, path)
    except BaseException:
        if tmp_name is not None:
            try:
                os.unlink(tmp_name)
            except OSError:
                pass
        raise
```

Used by: `_project_meta_json()`, `_process_init_project_state()`.

## Technical Decisions

| # | Decision | Rationale | Alternative Considered |
|---|----------|-----------|----------------------|
| D1 | Place `_project_meta_json()` in MCP server, not engine | Engine is a state machine; file I/O is server concern. Keeps engine unit-testable without filesystem. | In engine.py — rejected: couples engine to file format |
| D2 | Fast-path string check before JSON parse in hook | ~99% of Write/Edit calls don't target `.meta.json`. Avoids python3 subprocess for the common case. NFR-3 (< 50ms) requires this. | Always parse — rejected: adds ~30ms latency per non-.meta.json write |
| D3 | Store phase timing in entity metadata blob, not new DB columns | Phase 1 YAGNI — avoids schema migration. Metadata blob is flexible and already supports shallow merge. | New columns — deferred to Phase 2 |
| D4 | Atomic write via `NamedTemporaryFile` + `os.replace()` | Proven pattern from `_write_meta_json_fallback()`. Crash-safe on POSIX. | Direct `open().write()` — rejected: not atomic |
| D5 | `init_project_state` uses inline write, not `_project_meta_json()` | Project schema (features[], milestones[]) differs from feature schema (phases{}, lastCompletedPhase). Shared function would need branching that negates the benefit. | Shared function with mode param — rejected: adds complexity |
| D6 | No allowlist in hook | YAGNI per PRD. If legitimate `.meta.json` writes appear in instrumentation log, add allowlist then. | Pre-built allowlist — rejected: speculative |
| D7 | `_process_*` functions accept `db` param explicitly | Enables testing with mock DB. Consistent with existing pattern for `engine` param. | Use global `_db` directly — rejected: harder to test |

## Risks

| Risk | Likelihood | Impact | Mitigation |
|------|-----------|--------|------------|
| Hook latency > 50ms on slow machines | Low | Medium — slows every Write/Edit | Fast-path string check avoids python3 for 99% of calls |
| `artifact_path` not populated for some entities | Medium | Low — projection silently skips, DB state preserved | Warning in MCP response; backfill migration can fix existing entities |
| Stale `.meta.json` if projection fails | Low | Low — LLM reads stale data, next successful operation fixes it | Warning in MCP response; reconcile_check detects drift |
| Test suite disruption from 392 test references | High | Medium — many tests mock `.meta.json` writes | Incremental migration: convert one write site at a time, run suite after each |
| `_write_meta_json_fallback` creates unguarded state | Low | Low — only fires during DB degradation (rare) | Accepted Phase 1 limitation; Phase 2 removes fallback |

## Interfaces

### Hook Interface: `meta-json-guard.sh`

**Input (stdin):**
```json
{"tool_name": "Write", "tool_input": {"file_path": "/path/to/.meta.json", "content": "..."}}
```

**Output (stdout) — deny:**
```json
{
  "hookSpecificOutput": {
    "hookEventName": "PreToolUse",
    "permissionDecision": "deny",
    "permissionDecisionReason": "Direct .meta.json writes are blocked. Use MCP workflow tools instead: transition_phase() to enter a phase, complete_phase() to finish a phase, or init_feature_state() to create a new feature."
  }
}
```

**Output (stdout) — allow (non-.meta.json files):**
```json
{}
```

**Side effect:** Appends JSONL to `~/.claude/iflow/meta-json-guard.log`

### MCP Tool Interface: `init_feature_state`

**Parameters:**
| Param | Type | Required | Description |
|-------|------|----------|-------------|
| `feature_dir` | `str` | Yes | Absolute or project-relative path to feature dir |
| `feature_id` | `str` | Yes | Numeric feature ID (e.g., "034") |
| `slug` | `str` | Yes | Feature slug (e.g., "enforced-state-machine") |
| `mode` | `str` | Yes | "standard" or "full" |
| `branch` | `str` | Yes | Git branch name |
| `brainstorm_source` | `str` | No | Path to source brainstorm PRD |
| `backlog_source` | `str` | No | Backlog item reference |
| `status` | `str` | No | "active" (default) or "planned" |

**Response:**
```json
{
  "created": true,
  "feature_type_id": "feature:034-enforced-state-machine",
  "status": "active",
  "meta_json_path": "docs/features/034-enforced-state-machine/.meta.json",
  "projection_warning": null
}
```

### MCP Tool Interface: `init_project_state`

**Parameters:**
| Param | Type | Required | Description |
|-------|------|----------|-------------|
| `project_dir` | `str` | Yes | Absolute or project-relative path to project dir |
| `project_id` | `str` | Yes | Project ID |
| `slug` | `str` | Yes | Project slug |
| `features` | `str` | Yes | JSON array of feature ID strings |
| `milestones` | `str` | Yes | JSON array of milestone objects |
| `brainstorm_source` | `str` | No | Path to source brainstorm PRD |

**Response:**
```json
{
  "created": true,
  "project_type_id": "project:001-my-project",
  "meta_json_path": "docs/projects/001-my-project/.meta.json"
}
```

### MCP Tool Interface: `activate_feature`

**Parameters:**
| Param | Type | Required | Description |
|-------|------|----------|-------------|
| `feature_type_id` | `str` | Yes | e.g., "feature:034-enforced-state-machine" |

**Pre-condition:** Entity status must be "planned".

**Response:**
```json
{
  "activated": true,
  "feature_type_id": "feature:034-enforced-state-machine",
  "previous_status": "planned",
  "new_status": "active",
  "projection_warning": null
}
```

### Extended MCP Tool: `transition_phase`

**New parameter:**
| Param | Type | Required | Description |
|-------|------|----------|-------------|
| `skipped_phases` | `str` | No | JSON array of `{"phase": "...", "reason": "..."}` |

**Response additions:**
```json
{
  "transitioned": true,
  "results": [...],
  "degraded": false,
  "started_at": "2026-03-08T22:46:00Z",
  "skipped_phases_stored": true,
  "projection_warning": null
}
```

### Extended MCP Tool: `complete_phase`

**New parameters:**
| Param | Type | Required | Description |
|-------|------|----------|-------------|
| `iterations` | `int` | No | Number of review iterations for this phase |
| `reviewer_notes` | `str` | No | JSON array of reviewer note strings |

**Response additions:**
```json
{
  "feature_type_id": "...",
  "current_phase": "design",
  "last_completed_phase": "specify",
  "completed_at": "2026-03-08T22:45:00Z",
  "projection_warning": null
}
```

### Internal Interface: `_project_meta_json()`

```python
def _project_meta_json(
    db: EntityDatabase,
    feature_type_id: str,
    feature_dir: str | None = None,
) -> str | None:
    """Returns None on success, warning string on failure."""
```

Called by: `_process_init_feature_state`, `_process_activate_feature`, `_process_transition_phase`, `_process_complete_phase`.

### Internal Interface: `_atomic_json_write()`

```python
def _atomic_json_write(path: str, data: dict) -> None:
    """Raises on failure (caller handles)."""
```

Called by: `_project_meta_json`, `_process_init_project_state`.

## Dependencies

### Build Order

```
1. _atomic_json_write()           — no dependencies
2. _project_meta_json()           — depends on _atomic_json_write, EntityDatabase
3. meta-json-guard.sh             — depends on lib/common.sh (existing)
4. init_feature_state             — depends on _project_meta_json
5. init_project_state             — depends on _atomic_json_write
6. activate_feature               — depends on _project_meta_json
7. Extended transition_phase      — depends on _project_meta_json
8. Extended complete_phase        — depends on _project_meta_json
9. Skill/command write site edits — depends on all MCP tools being deployed
10. hooks.json registration       — last: enables enforcement after all sites updated
```

**Critical ordering constraint:** Hook registration (step 10) must be LAST. If the hook is enabled before all 9 write sites are updated, legitimate `.meta.json` writes will be blocked. Deploy atomically in a single commit.

### External Dependencies

- No new pip packages required
- `common.sh` helper functions (existing)
- `EntityDatabase` API (existing, no schema changes)
- `WorkflowStateEngine` API (existing)
- `tempfile`, `os` stdlib (existing imports in workflow_state_server.py)
