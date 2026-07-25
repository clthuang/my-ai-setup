---
description: List features, optionally filtered by status or phase
argument-hint: "[--status=<status> | --phase=<phase>]"
---

# /pd:list-features

Read-only engine query. One MCP call, one table — no filesystem scan, no phase inference.

**Steps:**
1. `--status=<status>` → `list_features_by_status(status)`. `--phase=<phase>` → `list_features_by_phase(phase)`. Both return workflow state per feature: `feature_type_id`, `current_phase`, `last_completed_phase`, `mode`. Render those columns.
2. No flag → `export_entities(entity_type="feature", fields="entity_id,status,metadata", include_lineage=false)`. Render `entity_id`, `status`, `metadata.branch`, `metadata.project_id`.
3. Empty result → `No features match.`

**Constraints:** columns are whatever the chosen call returns — do not merge the two shapes, and do not infer a phase for a feature the phase call did not report. Error envelopes surface verbatim.
