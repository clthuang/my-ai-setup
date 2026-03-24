# Spec: pd:doctor Phase 2 — Auto-Fix + Session-Start Integration

## Problem Statement

Phase 1 (feature 059) implemented 10 diagnostic checks that report issues with `fix_hint` fields. Currently, all fixes must be applied manually. The doctor tool also runs only when explicitly invoked — there is no automatic self-repair.

This feature adds: (1) auto-fix logic that applies fix_hints programmatically, (2) a `--fix` CLI flag, and (3) integration into the session-start hook for automatic self-repair every session.

## Scope

**In scope:**
- `apply_fixes(report: DiagnosticReport) -> FixReport` function that applies safe fixes
- `--fix` flag on CLI entry point (`python -m doctor --fix`)
- Fix safety classification: each fix_hint categorized as `safe` (auto-apply) or `manual` (report only)
- Session-start hook integration: run doctor with `--fix` after reconciliation
- Updated `/pd:doctor` command with `--fix` option

**Out of scope:**
- Phase 3 operational checks (cache cleanup, outdated MCP detection)
- Fixes requiring user judgment (e.g., "remove stale entity or restore directory" — ambiguous direction)
- Fixes requiring git operations (branch creation, merge)
- Fixes requiring MCP server restart

## Requirements

### FR-1: Fix Safety Classification

Each `fix_hint` from Phase 1 is classified as `safe` or `manual`:

| fix_hint pattern | Classification | Fix action |
|-----------------|----------------|------------|
| "Set lastCompletedPhase to..." | safe | Update .meta.json field |
| "Run reconcile_apply to sync..." | safe | Call `apply_workflow_reconciliation()` |
| "Run reconcile_apply to create DB entry" | safe | Call `apply_workflow_reconciliation()` |
| "Update brainstorm entity status to 'promoted'" | safe | `UPDATE entities SET status='promoted' WHERE type_id=...` |
| "Update entity status to 'promoted'" | safe | Same as above |
| "Add (promoted -> feature) annotation to backlog.md" | safe | Append annotation to backlog.md row |
| "Set PRAGMA journal_mode=WAL" | safe | Execute PRAGMA on DB |
| "Run migration to populate parent_uuid" | safe | Backfill parent_uuid from parent_type_id lookup |
| "Update parent_uuid to match parent entity's uuid" | safe | Set parent_uuid = lookup(parent_type_id).uuid |
| "Remove orphaned dependency row" | safe | DELETE FROM entity_dependencies WHERE ... |
| "Remove orphaned tag row" | safe | DELETE FROM entity_tags WHERE ... |
| "Remove orphaned workflow_phases row" | safe | DELETE FROM workflow_phases WHERE ... |
| "Remove self-referential parent_type_id" | safe | UPDATE entities SET parent_type_id=NULL, parent_uuid=NULL WHERE ... |
| "Rebuild FTS index" | safe | Call `rebuild_fts()` or equivalent |
| "Run keyword backfill" | manual | Requires LLM — cannot auto-apply |
| "Run embedding backfill" | manual | Requires API calls — cannot auto-apply |
| "Kill the process holding the lock" | manual | Dangerous — cannot auto-kill |
| "Create .meta.json or remove empty directory" | manual | Ambiguous direction |
| "Register entity or remove stale..." | manual | Ambiguous direction |
| "Create a new branch for rework" | manual | Requires git operations |
| "Update feature status to 'completed'..." | manual | Requires user judgment |
| "Fix JSON syntax in .meta.json" | manual | Cannot auto-fix syntax errors |
| "Check .claude/pd.local.md for syntax errors" | manual | Cannot auto-fix config |
| "Break the circular parent reference" | manual | Ambiguous which link to break |

### FR-2: Fix Engine

New module: `plugins/pd/hooks/lib/doctor/fixer.py`

```python
@dataclass
class FixResult:
    issue: Issue           # the original issue
    applied: bool          # True if fix was applied
    action: str            # description of what was done
    classification: str    # "safe" | "manual"

@dataclass
class FixReport:
    fixed_count: int
    skipped_count: int     # manual fixes that need human action
    failed_count: int      # safe fixes that failed to apply
    results: list[FixResult]
    elapsed_ms: int

def apply_fixes(
    report: DiagnosticReport,
    entities_db_path: str,
    memory_db_path: str,
    artifacts_root: str,
    project_root: str,
    dry_run: bool = False,
) -> FixReport:
```

**Fix application rules:**
1. Only attempt fixes for issues where `fix_hint is not None`
2. Classify each fix_hint using pattern matching (FR-1 table)
3. For `safe` fixes: apply the fix, verify it worked (re-check), record result
4. For `manual` fixes: record as skipped with `classification="manual"`
5. If a safe fix fails (exception): record as failed, continue to next fix
6. Fixes are applied in check order (same as CHECK_ORDER)
7. After all fixes, return FixReport

**Idempotency:** All safe fixes must be idempotent — running twice produces the same result. This is critical for session-start integration.

### FR-3: CLI --fix Flag

Update `plugins/pd/hooks/lib/doctor/__main__.py`:

```bash
python -m doctor --entities-db PATH --memory-db PATH --project-root PATH [--fix] [--dry-run]
```

- `--fix`: After diagnostics, apply safe fixes and re-run diagnostics to verify
- `--dry-run`: Show what would be fixed without applying (implies --fix output format)
- Without `--fix`: Existing behavior (diagnostic only)

**Output with --fix:**
```json
{
  "diagnostic": { ... DiagnosticReport before fixes ... },
  "fixes": { ... FixReport ... },
  "post_fix": { ... DiagnosticReport after fixes ... }
}
```

### FR-4: Session-Start Hook Integration

Add doctor auto-fix to `plugins/pd/hooks/session-start.sh` after the existing reconciliation step:

```bash
# After run_reconciliation (line ~504):
run_doctor_autofix() {
    # Same PLUGIN_ROOT / PYTHONPATH resolution as other Python calls
    $python_cmd -m doctor \
        --entities-db ~/.claude/pd/entities/entities.db \
        --memory-db ~/.claude/pd/memory/memory.db \
        --project-root "$PROJECT_ROOT" \
        --fix 2>/dev/null
}
doctor_result=$(run_doctor_autofix)
# Parse JSON, extract fix counts, surface summary
```

**Session-start output format:** Single summary line appended to the reconciliation output:
- If healthy: `"Doctor: healthy"` (or omit entirely for silent success)
- If fixes applied: `"Doctor: fixed N issues (M remaining)"`
- If errors remain: `"Doctor: N issues need manual attention"`

**Failure tolerance:** If doctor crashes or returns invalid JSON, log warning and continue session start. Doctor must never block session initialization.

### FR-5: Updated Command File

Update `plugins/pd/commands/doctor.md` to support `--fix` mode:
- Default: diagnostic only (existing behavior)
- With user request to fix: add `--fix` flag to Bash invocation
- Show before/after comparison when fixes are applied
- List remaining manual fixes with instructions

## Non-Requirements

- **NR-1:** Fixes requiring user judgment — always classified as `manual`
- **NR-2:** Fixes requiring external services (embedding APIs, LLM) — `manual`
- **NR-3:** Fixes requiring git operations — `manual`
- **NR-4:** MCP server management (restart, kill) — `manual`
- **NR-5:** Performance optimization of fix application — sequential is fine

## Acceptance Criteria

### AC-1: Safe fixes are applied
Given a DiagnosticReport with issues that have safe fix_hints, when `apply_fixes()` is called, then the fixes are applied and the post-fix diagnostic shows fewer issues.

### AC-2: Manual fixes are skipped
Given issues with manual fix_hints, when `apply_fixes()` is called, then those issues are reported as `skipped` with `classification="manual"`.

### AC-3: Fixes are idempotent
Given `apply_fixes()` is called twice on the same report, then the second call produces `fixed_count=0` (everything already fixed).

### AC-4: --fix flag works via CLI
Given `python -m doctor --fix`, then output contains diagnostic, fixes, and post_fix sections.

### AC-5: --dry-run shows plan without applying
Given `python -m doctor --fix --dry-run`, then output shows what would be fixed but no changes are made.

### AC-6: Session-start integration runs silently
Given a session starts with pd plugin active, then doctor auto-fix runs after reconciliation and produces at most one summary line.

### AC-7: Session-start failure doesn't block
Given doctor crashes during session start, then session initialization continues normally with a warning logged.

### AC-8: Fix classification covers all existing fix_hints
Given all fix_hints from the 10 Phase 1 checks, then every fix_hint is classified as either `safe` or `manual`.

### AC-9: Failed fixes are reported
Given a safe fix that raises an exception, then it is recorded as `failed` in FixReport and does not prevent other fixes from running.

### AC-10: Post-fix diagnostic validates repairs
Given fixes were applied, then a re-run of diagnostics confirms the issues are resolved (the post_fix report has fewer error/warning issues than the pre-fix report).

## Dependencies

- Feature 059 (pd-doctor-diagnostic-tool) — Phase 1 checks and models
- `workflow_engine.reconciliation.apply_workflow_reconciliation()` — reused for reconcile fixes
- `entity_registry.database.EntityDatabase` — for entity status updates
- `semantic_memory.config.read_config()` — for config resolution

## Risks

| Risk | Likelihood | Impact | Mitigation |
|------|-----------|--------|------------|
| Safe fix corrupts data | Low | High | Idempotency requirement + post-fix verification |
| Session-start adds latency | Medium | Low | Doctor runs fast (<15s), skip if healthy |
| Fix classification wrong (manual labeled safe) | Low | High | Conservative default: ambiguous → manual |
| DB lock during fix application | Medium | Medium | busy_timeout + graceful failure per fix |
