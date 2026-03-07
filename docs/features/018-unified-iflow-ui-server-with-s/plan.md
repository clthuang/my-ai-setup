# Plan: iflow UI Server + Kanban Board

## Implementation Order

### Phase 0: Prerequisites (Sequential)

**0.1: Correct spec inaccuracies**
- Update spec.md SC-8 and AC-9 CDN URLs from `cdn.tailwindcss.com` to `cdn.jsdelivr.net/npm/@tailwindcss/browser@4`
- Fix spec Dependencies line 112: change "already available in plugin venv" to "added via `uv add jinja2`"
- Done when: `grep cdn.tailwindcss.com spec.md` returns zero matches; Jinja2 line corrected

**0.2: Install dependencies**
- Run `uv add fastapi>=0.128.3` and `uv add jinja2` in `plugins/iflow/`
- If FastAPI or Jinja2 version resolution fails: STOP and escalate
- Verify httpx is available (required by FastAPI TestClient): `uv pip list | grep httpx`. If missing, run `uv add httpx`
- Done when: `uv pip list | grep -i fastapi`, `uv pip list | grep -i jinja2`, and `uv pip list | grep -i httpx` all return installed versions

**0.3: PoC Validation Gate (pass/fail)**
- Create `agent_sandbox/018-poc/test_thread_safety.py` — 20-line script:
  - FastAPI app with sync route, `EntityDatabase(check_same_thread=False)` on temp DB
  - Seed 10 workflow_phases rows
  - Fire 10 concurrent GET requests via `asyncio.gather` + `httpx.AsyncClient`
- Pass: all 10 return HTTP 200, zero `ProgrammingError` in stderr, script exits 0
- **If pass → continue to Phase 1 (sync route as designed)**
- **If fail → apply async fallback:** convert C3 board route to `async def board()`, wrap DB calls with `asyncio.to_thread(db.list_workflow_phases)`. Continue to Phase 1 with async variant.
- **Async fallback impact analysis:** The fallback affects ONLY the route handler signature in 2.2 (`async def` instead of `def`). Templates are unaffected (same context contract). CLI and shell wrapper are unaffected (`create_app()` signature unchanged). All downstream items remain valid under both PoC outcomes.
- Done when: script runs and exits 0

### Phase 1: Foundation (Sequential)

**1.1: EntityDatabase modification (C4)**
- File: `plugins/iflow/hooks/lib/entity_registry/database.py`
- Add `check_same_thread` as keyword-only parameter (after `*` in signature): `def __init__(self, db_path: str, *, check_same_thread: bool = True)`
- Pass through to `sqlite3.connect(..., check_same_thread=check_same_thread)`
- Run existing entity registry tests: `plugins/iflow/.venv/bin/python -m pytest plugins/iflow/hooks/lib/entity_registry/ -v`
- If any existing test fails: revert the change and investigate before proceeding. The default=True preserves all existing behavior — a test failure indicates an unexpected interaction.
- Done when: all existing tests pass (no regressions)

**1.2: Create package structure**
- Create directories: `plugins/iflow/ui/`, `plugins/iflow/ui/routes/`, `plugins/iflow/ui/templates/`
- Create `__init__.py` files: `plugins/iflow/ui/__init__.py`, `plugins/iflow/ui/routes/__init__.py`
- Done when: `test -f plugins/iflow/ui/__init__.py && test -f plugins/iflow/ui/routes/__init__.py` succeeds

### Phase 2: Core Application (Sequential — each step builds on previous)

**2.1: App Factory (C1)**
- File: `plugins/iflow/ui/__init__.py`
- Implement `create_app(db_path: str | None = None) -> FastAPI`
- DB path resolution from `ENTITY_DB_PATH` env var or default `~/.claude/iflow/entities/entities.db`
- `app.state.db = EntityDatabase(path, check_same_thread=False)` if file exists, else `None`
- `app.state.db_path = resolved_path`
- `app.state.templates = Jinja2Templates(directory=templates_dir)`
- Register board router via `app.include_router()`
- Done when: `create_app()` returns a FastAPI instance with correct state attributes

**2.2: Board Route (C3)**
- File: `plugins/iflow/ui/routes/board.py`
- Implement `COLUMN_ORDER` list, `_group_by_column()` helper, `board()` route handler
- Route: sync `def board(request: Request)` (or `async def` if PoC failed)
- Use keyword arguments for TemplateResponse: `templates.TemplateResponse(request=request, name="board.html", context=context)`
- Handle: missing DB → error.html, DB error → error.html, HX-Request → partial, else → full page
- Done when: route function exists and handles all 4 code paths

**2.3: Tests for core application**
- File: `plugins/iflow/ui/tests/test_app.py`
- TestClient test for `create_app()`: returns FastAPI with `db`, `db_path`, `templates` state attrs
- TestClient test for `create_app()` with missing DB path: `app.state.db` is `None`
- Unit test for `_group_by_column()`: empty input, single-column, multi-column, unknown column → "new" default
- TestClient GET `/` full page: returns 200, contains 8 column headers
- TestClient GET `/` with `HX-Request: true` header: returns 200, partial HTML (no `<html>` wrapper)
- TestClient GET `/` with missing DB (`app.state.db = None`): returns error page with setup instructions
- TestClient GET `/` with DB error: returns error page with error message
- Run: `plugins/iflow/.venv/bin/python -m pytest plugins/iflow/ui/tests/ -v`
- Done when: all tests pass

### Phase 3: Templates (Parallel group)

All 5 templates can be written in parallel — they have no code dependencies on each other.

**3.1: base.html**
- CDN tags in correct order: daisyui.css → @tailwindcss/browser@4 → htmx.org
- Navbar with "iflow" title
- `{% block content %}{% endblock %}`

**3.2: board.html**
- Extends base.html
- `<div id="board-content">` with `{% include "_board_content.html" %}`
- Refresh button: `hx-get="/" hx-target="#board-content" hx-swap="innerHTML"`

**3.3: _board_content.html**
- 8-column horizontal grid/flex layout
- Iterate `column_order`, render column headers with name + card count
- Include `_card.html` for each item in column
- Empty state: "No features yet" when all columns empty

**3.4: _card.html**
- Display: slug (split from type_id), type_id (small), workflow_phase (DaisyUI badge), mode (badge if not null), last_completed_phase
- Badge color mapping: wip→badge-primary, blocked→badge-error, completed→badge-success, others→badge-ghost

**3.5: error.html**
- Extends base.html
- Display: error_title, error_message, db_path with setup instructions

Done when: all templates render without Jinja2 syntax errors in FastAPI TestClient (verified by 2.3 tests)

### Phase 4: CLI and Shell Wrapper (Sequential)

**4.1: CLI Entry Point (C2)**
- File: `plugins/iflow/ui/__main__.py`
- argparse: `--port` (int, default 8718)
- Port conflict detection via `socket.bind()` attempt
- Print startup URL to stdout
- `uvicorn.run(create_app(), host="127.0.0.1", port=port)`
- Done when: `python -m plugins.iflow.ui` starts the server on default port

**4.2: Shell Bootstrap Wrapper (C2b)**
- File: `plugins/iflow/mcp/run-ui-server.sh` (co-located with sibling run-*-server.sh scripts)
- Adapt `run-workflow-server.sh` pattern: venv resolution, forward args
- PYTHONPATH must include BOTH `hooks/lib` (for entity_registry imports) AND the plugin parent directory (for `python -m plugins.iflow.ui` module resolution)
- Invocation: `exec "$VENV_DIR/bin/python" -m plugins.iflow.ui "$@"` (module invocation, not script path)
- Done when: `bash plugins/iflow/mcp/run-ui-server.sh` starts the server

### Phase 5: Verification (Sequential)

**5.1: Verify Uvicorn signal handling**
- Start server, send SIGINT — confirm exit code 0 and no traceback on stderr
- Start server, send SIGTERM — confirm exit code 0 and no traceback on stderr
- Verify DB integrity after shutdown: `sqlite3 <db_path> 'PRAGMA integrity_check'`
- Done when: both signals produce clean exit with no DB corruption

**5.2: Run existing test suites (AC-10 regression)**
- Entity registry tests: `plugins/iflow/.venv/bin/python -m pytest plugins/iflow/hooks/lib/entity_registry/ -v`
- Workflow engine tests: `plugins/iflow/.venv/bin/python -m pytest plugins/iflow/hooks/lib/workflow_engine/ -v`
- Transition gate tests: `plugins/iflow/.venv/bin/python -m pytest plugins/iflow/hooks/lib/transition_gate/ -v`
- MCP server tests: `plugins/iflow/.venv/bin/python -m pytest plugins/iflow/mcp/test_workflow_state_server.py -v`
- Done when: all test suites pass with zero failures

**5.3: Manual smoke test**
- Start server, open browser to `http://127.0.0.1:8718/`
- Verify: 8 columns rendered, cards display correct data, refresh button works (HTMX partial), empty state message shown when no data
- Done when: visual verification confirms AC-3, AC-4, AC-5, AC-6

## Dependency Graph

```
0.1 (spec fix) ──┐
0.2 (deps)    ───┤
                 ├──▶ 0.3 (PoC gate) ──▶ 1.1 (C4 DB mod) ──▶ 1.2 (package) ──▶ 2.1 (C1 app) ──▶ 2.2 (C3 route) ──▶ 2.3 (tests)
                                                                                                                          │
                                                                                                     ┌────────────────────┤
                                                                                                     ▼                    ▼
                                                                                               3.1-3.5 (templates)   4.1 (C2 CLI)
                                                                                                     │                    │
                                                                                                     ▼                    ▼
                                                                                               5.1-5.3 (verify)     4.2 (C2b wrapper)
                                                                                                                          │
                                                                                                                          ▼
                                                                                                                    5.1-5.3 (verify)
```

## Acceptance Criteria Coverage

| AC | Plan Item | Verification |
|----|-----------|-------------|
| AC-1 | 4.1 CLI Entry Point | Server binds, prints URL |
| AC-2 | 4.1 CLI Entry Point | Port conflict error message |
| AC-3 | 2.2 + 2.3 + 3.1-3.3 | Full page with 8 columns (TestClient + smoke) |
| AC-4 | 2.2 + 2.3 + 3.2-3.3 | HTMX partial refresh (TestClient + smoke) |
| AC-5 | 3.4 _card.html | Card displays correct fields |
| AC-6 | 2.3 + 3.3 _board_content.html | Empty state message (TestClient + smoke) |
| AC-7 | 2.1 + 2.3 + 3.5 | Error page with DB path (TestClient) |
| AC-8 | 0.3 PoC + 1.1 C4 | Concurrent requests pass |
| AC-9 | 3.1 base.html | 3 CDN tags load |
| AC-10 | 5.2 regression tests | All existing tests pass |

## Risk Mitigations

| Risk | Plan Response |
|------|--------------|
| FastAPI version conflict | 0.2 fails fast — escalate before proceeding |
| Jinja2 version conflict | 0.2 fails fast — escalate before proceeding |
| httpx missing | 0.2 verifies availability, adds if missing |
| SQLite thread safety | 0.3 PoC gate validates before implementation |
| PoC failure | Async fallback path defined in 0.3 with impact analysis |
| EntityDatabase regression | 1.1 revert-and-investigate clause |
| Signal handling | 5.1 explicit verification with PRAGMA integrity_check |
