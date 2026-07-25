---
description: Render engine state for the active feature(s)
---

# /pd:show-status

Read-only render of engine state. No state writes, no `.meta.json` writes, no phase resolution of its own — the engine's answer is the display value.

**Steps:**
1. `export_entities(entity_type="feature", fields="type_id,entity_id,status,metadata", include_lineage=false)` for the feature set. Also `export_entities(entity_type="brainstorm")` and `export_entities(entity_type="backlog")` for the open-items sections.
2. For each feature with status `active`, `get_phase(feature_type_id=...)`. Non-active features display their status; do not call `get_phase` for them.
3. Render: current branch; features grouped by project (`## Project: {metadata.project_id}`, slug via `get_entity` when it resolves) else `## Open Features`; open brainstorms; open backlog items.
4. One line per active feature, fields verbatim from `get_phase`: `{id}-{slug} — {current_phase} (last completed: {last_completed_phase}, mode: {mode})`; label `degraded: true` responses.
5. No active feature → footer `Tip: /pd:secretary <request>`.

**Constraints:** read tools unavailable → say so and fall back to `git` plus a `{pd_artifacts_root}/features/` listing (MCP degradation, workflow-transitions skill).
