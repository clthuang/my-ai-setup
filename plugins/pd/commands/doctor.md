---
description: Run pd workspace health checks, optionally applying safe fixes
argument-hint: "[--fix] [--dry-run]"
---

# /pd:doctor

Runs the `doctor` module and renders its report. The check roster lives in the module (`CHECK_ORDER`); this command never restates the checks or their count.

**Modes:** no flag → diagnose only. `--fix` → apply safe fixes, then re-run to verify. `--fix --dry-run` → show what would be fixed, write nothing.

**Steps:**
1. Run the module, appending the requested flags:

```bash
PLUGIN_ROOT=$(ls -d ~/.claude/plugins/cache/*/pd*/*/hooks 2>/dev/null | head -1 | xargs dirname)
if [ -z "$PLUGIN_ROOT" ]; then PLUGIN_ROOT="plugins/pd"; fi  # Fallback (dev workspace)
PYTHONPATH="$PLUGIN_ROOT/hooks/lib" "$PLUGIN_ROOT/.venv/bin/python" -m doctor \
  --entities-db ~/.claude/pd/entities/entities.db \
  --artifacts-root {pd_artifacts_root} \
  --project-root . 2>/dev/null
```

   No venv at either location → report `No pd venv found. Run: cd plugins/pd && uv sync` and stop.

2. Parse the `diagnostic` key. One table row per reported check: name, PASS/FAIL, issue count. Under each failing check, list its issues errors-first with their `fix_hint`.
3. `fixes` key present → report fixed / manual / failed counts, then each manual fix with its `fix_hint`. `post_fix` key present → show before/after error and warning counts.
4. Close with `Workspace healthy` or `{N} issues ({E} errors, {W} warnings)`.

**Constraints:** read-only unless `--fix` was asked for; doctor also runs at session start, so anything here survived auto-repair.
