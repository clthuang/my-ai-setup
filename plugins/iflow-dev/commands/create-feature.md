---
description: Alternative entry point - skip brainstorming and create feature directly
argument-hint: <feature-description> [--prd=<path>]
---

# /iflow-dev:create-feature Command

## Config Variables
Use these values from session context (injected at session start):
- `{iflow_artifacts_root}` — root directory for feature artifacts (default: `docs`)

**Alternative entry point** for feature development. Use when you want to skip brainstorming.

Recommended flow: `/iflow-dev:brainstorm` → (promotion) → `/iflow-dev:specify` → ...
This command: `/iflow-dev:create-feature` → `/iflow-dev:specify` → ... (skips exploration)

## YOLO Mode Overrides

If `[YOLO_MODE]` is active:
- Active feature conflict → auto "Create new anyway"
- Mode selection → auto "Standard (Recommended)"
- Context propagation: when auto-invoking specify, include `[YOLO_MODE]` in args

## Check for Active Feature

Before creating, check if a feature is already active:

1. Look in `{iflow_artifacts_root}/features/` for folders with `.meta.json` where `status: "active"`
2. If found:
   ```
   AskUserQuestion:
     questions: [{
       "question": "Feature {id}-{slug} is already active. What would you like to do?",
       "header": "Active Feature",
       "options": [
         {"label": "Continue with existing", "description": "Show status and stop"},
         {"label": "Create new anyway", "description": "Proceed with new feature creation"}
       ],
       "multiSelect": false
     }]
   ```
3. If "Continue with existing": Invoke `/iflow-dev:show-status` → STOP
4. If "Create new anyway": Proceed with creation below

## Gather Information

1. **Get feature description** from argument or ask user
2. **Determine feature ID**: Find highest number in `{iflow_artifacts_root}/features/` and add 1
3. **Create slug** from description (lowercase, hyphens, max 30 chars)

## Suggest Workflow Mode

Based on described scope, suggest a mode:

| Scope | Suggested Mode |
|-------|----------------|
| Most features, clear scope | Standard |
| "rewrite", "refactor system", "breaking change" | Full |

Present mode selection via AskUserQuestion:
```
AskUserQuestion:
  questions: [{
    "question": "Feature: {id}-{slug}. Select workflow mode:",
    "header": "Mode",
    "options": [
      {"label": "Standard (Recommended)", "description": "All phases with optional verification"},
      {"label": "Full", "description": "All phases with required verification"}
    ],
    "multiSelect": false
  }]
```

Note: If "Full" indicators are detected in the description, swap the recommended label to Full.

## Create Feature

### For All Modes

1. Create folder: `{iflow_artifacts_root}/features/{id}-{slug}/`
2. Create feature branch:
   ```bash
   git checkout -b feature/{id}-{slug}
   ```
3. Create `.meta.json` (see below)

### Mode-Specific Behavior

**Standard/Full:**
- Inform: "Created branch feature/{id}-{slug}."
- Inform: "Continuing to /iflow-dev:specify..."
- Auto-invoke `/iflow-dev:specify`

## Create Metadata File

Write to `{iflow_artifacts_root}/features/{id}-{slug}/.meta.json`:

```json
{
  "id": "{id}",
  "slug": "{slug}",
  "mode": "{selected-mode}",
  "status": "active",
  "created": "{ISO timestamp}",
  "branch": "feature/{id}-{slug}",
  "brainstorm_source": "{path-to-brainstorm-if-promoted}",
  "lastCompletedPhase": null,
  "phases": {}
}
```

Notes:
- `brainstorm_source` is only included when feature is promoted from a brainstorm
- `phases` is initialized empty; phase commands populate it as they execute
- `lastCompletedPhase` tracks the last completed phase (null until first phase completes)

## Handle PRD Source

If `--prd` argument provided (promotion from brainstorm):

1. Copy the PRD file: `{prd-path}` → `{iflow_artifacts_root}/features/{id}-{slug}/prd.md`
2. **Verify copy succeeded:** Confirm destination file exists and is non-empty
3. If verification fails: Output error and STOP
4. Add to `.meta.json`: `"brainstorm_source": "{prd-path}"`

If `--prd` NOT provided (direct creation):
- No PRD file is created
- `brainstorm_source` is not set in `.meta.json`

## Handle Backlog Source

If feature was promoted from a brainstorm that originated from a backlog item:

1. **Read brainstorm content** from `brainstorm_source` path in context
2. **Parse for backlog source** using pattern `\*Source: Backlog #(\d{5})\*`
3. **If found:**
   - Add `"backlog_source": "{id}"` to `.meta.json`
   - Read `{iflow_artifacts_root}/backlog.md`
   - Find row matching `| {id} |`
   - Remove that row
   - Write updated backlog
   - Display: `Linked from backlog item #{id} (removed from backlog)`
4. **If pattern not found:** No action, continue normally
5. **If ID found but row missing:** Display warning `⚠️ Backlog item #{id} not found in {iflow_artifacts_root}/backlog.md`, continue with feature creation

## State Tracking

Apply the detecting-kanban skill:
1. If Vibe-Kanban available:
   - Create card with feature name
   - Set status to "New"
2. Otherwise:
   - Use TodoWrite to track feature

## Output

**If `--prd` provided (promotion from brainstorm):**
```
✓ Feature {id}-{slug} created
  Mode: {mode}
  Folder: {iflow_artifacts_root}/features/{id}-{slug}/
  Branch: feature/{id}-{slug}
  PRD: Copied from brainstorm
  Linked from: Backlog #{backlog_id} (removed)  ← only if backlog source found
```

**If `--prd` NOT provided (direct creation):**
```
✓ Feature {id}-{slug} created
  Mode: {mode}
  Folder: {iflow_artifacts_root}/features/{id}-{slug}/
  Branch: feature/{id}-{slug}
  Linked from: Backlog #{backlog_id} (removed)  ← only if backlog source found

  Note: No PRD. /specify will gather requirements.
```

## Auto-Continue

After creation, automatically invoke `/iflow-dev:specify --feature={id}-{slug}`.
