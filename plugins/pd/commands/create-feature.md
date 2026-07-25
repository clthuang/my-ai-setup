---
description: Create and activate a feature, deep or express lane
argument-hint: <feature-description> [--prd=<path>] [--express]
---

# /pd:create-feature

Contract command. Shared mechanics (entry, exit, YOLO, review gate, dispatch hygiene): workflow-transitions skill.

**Purpose:** mint one feature identity — id, directory, entity, branch — and hand control to its first phase.

**Inputs:** the description argument; `--prd=<path>` when promoting a brainstorm PRD; `--express` plus an inline mini-spec for the express lane; `list_features_by_status(status="active")` for what is already active.

**Output:** a registered, active feature entity with its directory and branch; control passed to `/pd:specify` (deep) or `/pd:implement` (express).

**Steps:**
1. If a feature is already active, confirm via AskUserQuestion before minting a second one.
2. `allocate_entity_id(entity_type="feature", name=<description>)` — the returned `entity_id` is the authoritative `{id}-{slug}` for directory, branch, and registration. An error envelope stops the command; never derive an id locally.
3. `mkdir -p {pd_artifacts_root}/features/{id}-{slug}/`. With `--prd`, copy the PRD into it as `prd.md` and stop if the copy is missing or empty.
4. `register_entity(entity_type="feature", entity_id="{id}-{slug}", name=<description>, status="planned", ...)` — promotion sources go in `metadata` (brainstorm stem, backlog id, or both) with `parent_uuid` resolved from that source, never into prose. `status="planned"` is what the next step requires.
5. Activate per the workflow-state skill: `activate_feature`, then the feature branch.
6. `--express`: `record_mini_spec(feature_type_id="feature:{id}-{slug}", text="<mini-spec>")`, then hand `/pd:implement` its entry skip set — every phase before implement in workflow-state's sequence, passed as `skipped_phases`. Otherwise continue into `/pd:specify`.

**Constraints:** an allocation or registration error stops the command — a half-minted feature costs more than none. No state writes outside MCP tools; no phase-sequence or status-vocabulary restatement.
