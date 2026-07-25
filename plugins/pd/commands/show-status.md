---
description: Render engine state for the active feature(s)
---

# /pd:show-status

Read-only render of engine state. No state writes, no `.meta.json` writes, no phase resolution of its own — the engine's answer is the display value.

**Steps:**
1. `export_entities(entity_type="feature", fields="type_id,entity_id,status,metadata", include_lineage=false)` for the feature set. Also `export_entities(entity_type="brainstorm")` and `export_entities(entity_type="backlog")` for the open-items sections.
2. For each feature with status `active`, `get_phase(feature_type_id=...)`. Non-active features display their status; do not call `get_phase` for them.
3. Render, in order: current branch (`git branch --show-current`); features grouped under `## Project: {metadata.project_id}` when that key is set — append the slug from `get_entity(ref="project:{project_id}")` when it resolves — else `## Open Features`; then open brainstorms and open backlog items.
4. One line per active feature, fields taken verbatim from the `get_phase` response: `{id}-{slug} — {current_phase} (last completed: {last_completed_phase}, mode: {mode})`. A `degraded: true` response is labelled as such on that line.
5. Footer: `Tip: /pd:secretary <request>` when no feature is active.

**Constraints:** read tools unavailable → say so and fall back to `git` plus a `{pd_artifacts_root}/features/` listing (MCP degradation, workflow-transitions skill).
