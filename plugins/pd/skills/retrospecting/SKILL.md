---
name: retrospecting
description: Evidence-driven retrospective contract — reads the engine's recorded phase events and produces retro.md. Use when closing out a feature, before branch cleanup.
---

# Retrospecting

Runs while the branch, worktrees, and review history still exist — they are the inputs.

## Build the bundle from the record, not from recollection
Never ask the user how the feature went. Assemble:

- **Engine phase events** (MCP read tools): per-phase timings, review iteration counts, reviewer notes on `completed` events (the review record — `.review-history.md` is retired), and every backward transition with its reason. A phase re-entered is the strongest signal in the bundle.
- **Git**: `git log --oneline {pd_base_branch}..HEAD` and `git diff --stat {pd_base_branch}..HEAD`.
- **Workaround candidates**, via the extractor — feed it the session texts (commit messages + event reviewer notes) as one temp file; it prints `[]` when there is nothing to report:
  ```bash
  PLUGIN_ROOT=$(ls -d ~/.claude/plugins/cache/*/pd*/*/hooks 2>/dev/null | head -1 | xargs dirname)
  if [ -z "$PLUGIN_ROOT" ]; then PLUGIN_ROOT="plugins/pd"; fi  # Fallback (dev workspace)
  D="{pd_artifacts_root}/features/{id}-{slug}"
  LOG=$(mktemp)
  git log {pd_base_branch}..HEAD --format='%s%n%b' > "$LOG"
  # Append reviewer notes pulled from the completed events (engine read).
  "$PLUGIN_ROOT/.venv/bin/python" "$PLUGIN_ROOT/skills/retrospecting/scripts/extract_workarounds.py" \
    --log-path "$LOG" --meta-json-path "$D/.meta.json" 2>/dev/null || echo "[]"
  ```

Every figure enters re-derived from its primary source. A count copied out of a briefing or an earlier artifact is a defect — restated metrics have drifted before, in both directions.

## Produce retro.md
Dispatch `pd:retro-facilitator` with the bundle; it owns the analysis framework and its return shape. Write the result to `{pd_artifacts_root}/features/{id}-{slug}/retro.md`:

- **Observe** — metrics table: phase, duration, iterations, backward transitions.
- **Review** — recurring finding classes, each citing its evidence.
- **Tune** — process changes, each naming the signal behind it.
- **Act** — patterns, anti-patterns, heuristics, each with provenance.

Check self-labels ("first", "only", "highest") against prior retros before writing them down. Promote anything that recurred across features into `{pd_artifacts_root}/knowledge-bank/`; one-offs stay in `retro.md`, which is committed before cleanup begins.
