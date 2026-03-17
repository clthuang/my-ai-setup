# Plan: MCP Bootstrap Race Fix

## Implementation Order

The implementation interleaves tests with production code (TDD): test scaffold first, then shared library, then thin wrappers with verification, then integration tests. A spec amendment is included to formalize the design deviation.

```
Phase 1: Test Scaffold + Foundation (sequential)
  ├─ Task 1.1: Create test_bootstrap_venv.sh with unit test cases (RED)
  └─ Task 1.2: Create bootstrap-venv.sh shared library (GREEN)

Phase 2: Integration (parallel — each script independent)
  ├─ Task 2.1: Refactor run-memory-server.sh to thin wrapper
  ├─ Task 2.2: Refactor run-entity-server.sh to thin wrapper
  ├─ Task 2.3: Refactor run-workflow-server.sh to thin wrapper
  ├─ Task 2.4: Refactor run-ui-server.sh to thin wrapper
  └─ Task 2.5: Verify existing test scripts still pass

Phase 3: Integration Tests (depends on Phase 1+2)
  └─ Task 3.1: Add integration tests to test_bootstrap_venv.sh

Phase 4: Spec Amendment (no deps — documentation only)
  └─ Task 4.1: Amend spec.md Design Notes
```

## Phase 1: Test Scaffold + Foundation

### Task 1.1: Create Test Scaffold (RED)

**Goal:** Write failing test cases BEFORE implementing bootstrap-venv.sh.

**File:** `plugins/iflow/mcp/test_bootstrap_venv.sh`

**Unit test cases to write first:**

1. **check_python_version test:** Create a mock `python3` reporting 3.10 in a subshell `(PATH=/mock:$PATH; check_python_version)` to isolate PATH. Assert exit 1 with error containing required and detected versions.

2. **check_venv_deps test (all present):** Create a venv with all deps, assert returns 0.

3. **check_venv_deps test (missing):** Create a venv with only `mcp`, assert returns 1.

4. **Dep array alignment test:** Parse `pyproject.toml` for `[project].dependencies`, compare with `DEP_PIP_NAMES` array to ensure they stay in sync.

5. **Bash 3.2 compatibility test:** Run under `/bin/bash` (macOS 3.2) — verify array declaration, `[@]` iteration, and `+=` string concatenation all work correctly. This validates TD-5 assumptions.

All tests run in subshells for isolation. Each test uses `(subshell)` to prevent PATH/env leaks between tests.

### Task 1.2: Create `bootstrap-venv.sh` (GREEN)

**Goal:** Implement the shared bootstrap library. Make tests from Task 1.1 pass.

**File:** `plugins/iflow/mcp/bootstrap-venv.sh`

**What to implement (in order within the file):**

1. **Canonical dependency arrays (I7):** Two index-aligned bash arrays at top of file:
   - `DEP_PIP_NAMES` — pip install specifiers with version constraints from pyproject.toml
   - `DEP_IMPORT_NAMES` — Python import names (note: `python-dotenv` → `dotenv`, `pydantic-settings` → `pydantic_settings`)
   - All 8 deps: fastapi, jinja2, mcp, numpy, pydantic, pydantic-settings, python-dotenv, uvicorn

2. **`check_python_version` (I2, FR-3):**
   - Run `python3 -c` to extract major.minor
   - Compare with bash arithmetic: major < 3 OR (major == 3 AND minor < 12)
   - Exit 1 with stderr message including required and detected versions (AC-3.2)

3. **`check_system_python` (design C1):**
   - Build import string from `DEP_IMPORT_NAMES` array
   - Run `python3 -c "$imports"` to test ALL canonical deps (unified, not per-server)
   - Return 0 if all importable, 1 otherwise
   - If 0: export `PYTHON=python3`

4. **`check_venv_deps` (I3, FR-2):**
   - Takes `python_path` argument
   - Builds import chain from `DEP_IMPORT_NAMES`
   - Returns 0 if all importable, 1 if any missing

5. **`create_venv` (design C1):**
   - Takes `venv_dir` and `server_name` arguments
   - Try `uv venv "$venv_dir"` first (DC-5), fall back to `python3 -m venv "$venv_dir"`
   - All output to stderr (DC-1)

6. **`install_all_deps` (I4):**
   - Takes `venv_dir` and `server_name`
   - Try `uv pip install --python "$venv_dir/bin/python" "${DEP_PIP_NAMES[@]}"` first
   - Fallback: `"$venv_dir/bin/pip" install -q "${DEP_PIP_NAMES[@]}"`
   - All output to stderr

7. **`acquire_lock` (I5, FR-1):**
   - Takes `lock_dir`, `sentinel`, `server_name`
   - Phase 1: `mkdir "$lock_dir"` — if succeeds return 0
   - Phase 2a: stale check via `find "$lock_dir" -maxdepth 0 -mmin +2` — if stale, `rmdir "$lock_dir"` + retry mkdir once; if retry fails, fall through to 2b
   - Phase 2b: spin-wait on sentinel file (1s sleep, 120 iterations) — return 1 if sentinel appears, exit 1 if timeout (AC-1.5)
   - **Constraint:** Lock directory must remain empty (no PID files or other contents). This ensures `rmdir` works reliably for both normal release and stale cleanup. PID-based debugging was considered (design) but rejected for simplicity.

8. **`release_lock` (I5):**
   - Takes `lock_dir`
   - `rmdir "$lock_dir" 2>/dev/null || true`

9. **`bootstrap_venv` (I1) — orchestrator:**
   - Takes `venv_dir` and `server_name`
   - Step 1: `check_python_version`
   - Step 2: `check_system_python` — if returns 0, return (PYTHON already exported)
   - Step 3: Fast-path — if `bin/python` exists AND sentinel (`.bootstrap-complete`) exists:
     - If `check_venv_deps` passes → export `PYTHON="$venv_dir/bin/python"`, return
     - If fails → fall through to Step 4 (acquire lock before installing, to avoid concurrent install race)
   - Step 4: `acquire_lock`
     - If returns 1 (another process bootstrapped) → re-check deps via `check_venv_deps`, self-heal if needed (install_all_deps under lock is already done by leader, so deps should be present; if still missing, log warning and install), export PYTHON, return
     - If returns 0 (lock acquired):
       - Set trap: `trap 'rmdir "$lock_dir" 2>/dev/null' EXIT`
       - Re-check: if sentinel exists AND `check_venv_deps` passes (double-checked locking) → `release_lock`, `trap - EXIT`, export PYTHON, return
       - `create_venv` → `install_all_deps` → write sentinel (`.bootstrap-complete`) → `release_lock` → `trap - EXIT`
       - export `PYTHON="$venv_dir/bin/python"`, return
   - **Trap lifecycle:** The `trap EXIT` is set immediately after `acquire_lock` returns 0 and cleared (`trap - EXIT`) before returning from `bootstrap_venv`. This prevents the trap from persisting into the calling script (trap EXIT is script-global, not function-scoped). Sequence: set trap → create/install → write sentinel → release_lock → clear trap → return.

**Fast-path self-heal race condition (addressed):** The fast-path (Step 3) does NOT call `install_all_deps` directly. If deps are missing, it falls through to Step 4 which acquires the lock first. This prevents concurrent `pip install` / `uv pip install` calls from multiple servers that all detect missing deps simultaneously. The lock serializes all install operations.

**`export PYTHON` (not just `set`):** All paths that resolve the Python interpreter use `export PYTHON=...` per design interface I1. This ensures `PYTHON` is visible to any subprocess if needed.

**Acceptance criteria addressed:** AC-1.1, AC-1.2, AC-1.3, AC-1.5, AC-2.1, AC-2.2, AC-2.3, AC-2.4, AC-3.1, AC-3.2, DC-1 through DC-5.

## Phase 2: Integration — Refactor Server Scripts to Thin Wrappers

**Goal:** Replace inline bootstrap logic in all 4 scripts with `source bootstrap-venv.sh`.

**Dependency:** Phase 1 must complete first.

All 4 tasks follow the same pattern (I6 template). Each script becomes ~15 lines:

### Task 2.1: `run-memory-server.sh`

**Current:** 32 lines with inline pip-only bootstrap, per-server dep list (`mcp`, `numpy`, `python-dotenv`).
**After:** Source bootstrap-venv.sh, call `bootstrap_venv`, exec with `$PYTHON`.
**Key change:** Remove inline `python3 -m venv` + `pip install`. Remove per-server dep check (`import mcp.server.fastmcp; import numpy; import dotenv`).

### Task 2.2: `run-entity-server.sh`

**Current:** 41 lines with inline uv/pip bootstrap, only `mcp` dep.
**After:** Same thin wrapper pattern.
**Key change:** Remove all 4 step resolution (fast-path, system python, uv bootstrap, pip bootstrap).

### Task 2.3: `run-workflow-server.sh`

**Current:** Same structure as entity-server.
**After:** Same thin wrapper pattern.

### Task 2.4: `run-ui-server.sh`

**Current:** Uses `uv sync --no-dev` (different from other 3 scripts).
**After:** Same thin wrapper pattern but with different PYTHONPATH (adds `$PLUGIN_DIR` for `ui` module) and SERVER_SCRIPT (`$PLUGIN_DIR/ui/__main__.py`).
**Key difference:** `PYTHONPATH="$PLUGIN_DIR/hooks/lib:$PLUGIN_DIR${PYTHONPATH:+:$PYTHONPATH}"` per I6 note.

### Task 2.5: Verify Existing Test Scripts

**Goal:** Run existing bootstrap wrapper tests to confirm no regression.

**Files to run:**
- `bash plugins/iflow/mcp/test_run_memory_server.sh`
- `bash plugins/iflow/mcp/test_run_workflow_server.sh`
- `bash plugins/iflow/mcp/test_entity_server.sh` (if exists)

**If tests fail:** Fix the test scripts to match the new thin-wrapper interface (they may expect the old inline bootstrap output patterns). Document changes.

**If tests are fully superseded** by Phase 3's comprehensive test: note that in the implementation log and keep them as smoke tests.

## Phase 3: Integration Tests

**Goal:** Add integration test cases that require both bootstrap-venv.sh and the refactored server scripts.

**File:** `plugins/iflow/mcp/test_bootstrap_venv.sh` (append to existing from Task 1.1)

**Integration test cases:**

1. **Concurrent launch test (AC-1.1):** Spawn 4 bootstrap_venv calls as background processes in a temp dir (fresh install simulation), wait for all, assert venv exists and all deps importable. Use a barrier file (`touch /tmp/barrier`) so all 4 processes start simultaneously.

2. **Stale lock test (AC-1.3):** Pre-create a lock directory, backdate its mtime with `touch -t`, launch a bootstrap, assert stale detection removes the lock and bootstrap succeeds.

3. **Missing dep self-heal test (AC-2.4):** Create a venv with all deps, write sentinel, then remove one dep (`pip uninstall numpy`). Launch bootstrap — sentinel exists but deps fail. Assert it falls through to locked install and restores all deps.

4. **uv-absent fallback test (DC-5):** Run bootstrap in a subshell with `uv` removed from PATH. Assert pip fallback is used and all deps installed.

5. **Fast-path test:** Create venv with all deps + sentinel, run bootstrap, assert it takes fast-path (no lock directory created).

## Phase 4: Spec Amendment

**Goal:** Formalize the design deviation in spec.md.

**File:** `docs/features/039-mcp-bootstrap-race-fix/spec.md`

**Change:** Replace Design Notes bullet about "system python3" fallback being "preserved as-is" with:
> The existing "system python3" fallback path is unified to check ALL canonical deps (not per-server subsets). This eliminates the RC-2 dependency gap at the system-python level. The path runs before venv bootstrap and does not participate in the locking protocol.

Also add `pydantic`→`pydantic` and `pydantic-settings`→`pydantic_settings` to the AC-2.2 known deps list to match the 8-dep canonical list from pyproject.toml.
