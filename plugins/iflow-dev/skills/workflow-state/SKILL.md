---
name: workflow-state
description: Defines phase sequence and validates transitions. Use when checking phase prerequisites or managing workflow state.
---

# Workflow State Management

Manage feature workflow state and validate phase transitions.

## Phase Sequence

The canonical workflow order:

```
brainstorm → specify → design → create-plan → create-tasks → implement → finish
```

| Phase | Produces | Required Before |
|-------|----------|-----------------|
| brainstorm | prd.md | (entry point) |
| specify | spec.md | design, implement |
| design | design.md | create-plan |
| create-plan | plan.md | create-tasks |
| create-tasks | tasks.md | implement |
| implement | code changes | finish |
| finish | (terminal) | — |

## Transition Validation

Before executing any phase command, validate the transition.

### Hard Prerequisites (Block)

These transitions are **blocked** if prerequisites are missing:

| Target Phase | Required Artifact | Error Message |
|--------------|-------------------|---------------|
| /iflow-dev:implement | spec.md | "spec.md required before implementation. Run /iflow-dev:specify first." |
| /iflow-dev:create-tasks | plan.md | "plan.md required before task creation. Run /iflow-dev:create-plan first." |

If blocked: Show error message, do not proceed.

### Soft Prerequisites (Warn)

All other out-of-order transitions produce a **warning** but allow proceeding via AskUserQuestion:

```
AskUserQuestion:
  questions: [{
    "question": "Skipping {skipped phases}. This may reduce artifact quality. Continue anyway?",
    "header": "Skip",
    "options": [
      {"label": "Continue", "description": "Proceed despite skipping phases"},
      {"label": "Stop", "description": "Return to complete skipped phases"}
    ],
    "multiSelect": false
  }]
```

Examples:
- brainstorm → design (skips specify) → warn
- specify → create-tasks (skips design, create-plan) → warn
- Any phase → finish (out of order) → warn

### Normal Transitions (Proceed)

Transitions following the sequence proceed without warnings.

### Validation Logic

```
function validateTransition(currentPhase, targetPhase, artifacts):

  # Hard blocks
  if targetPhase == "implement" and not artifacts.spec:
    return { allowed: false, type: "blocked", message: "spec.md required..." }

  if targetPhase == "create-tasks" and not artifacts.plan:
    return { allowed: false, type: "blocked", message: "plan.md required..." }

  # Phase sequence for ordering
  sequence = [brainstorm, specify, design, create-plan, create-tasks, implement, finish]
  currentIndex = sequence.indexOf(currentPhase) or -1
  targetIndex = sequence.indexOf(targetPhase)

  # Backward transition detection
  if targetIndex < currentIndex AND currentIndex >= 0:
    return {
      allowed: true,
      type: "backward",
      message: "Phase '{targetPhase}' was already completed. Re-running will update timestamps but not undo previous work."
    }

  # Check if skipping phases (forward jump)
  if targetIndex > currentIndex + 1:
    skipped = sequence[currentIndex+1 : targetIndex]
    return { allowed: true, type: "warning", message: "Skipping {skipped}..." }

  return { allowed: true, type: "proceed", message: null }
```

### Backward Transition Warning

When `validateTransition` returns `type: "backward"`, commands should use AskUserQuestion:

```
AskUserQuestion:
  questions: [{
    "question": "Phase '{targetPhase}' was already completed. Re-running will update timestamps but not undo previous work. Continue?",
    "header": "Backward",
    "options": [
      {"label": "Continue", "description": "Re-run the phase"},
      {"label": "Cancel", "description": "Stay at current phase"}
    ],
    "multiSelect": false
  }]
```

If "Cancel": Stop execution.

## Artifact Validation

Beyond existence checks, validate artifact content quality before allowing phase transitions.

### validateArtifact(path, type)

**Level 1: Existence**
- File exists at path

**Level 2: Non-Empty**
- File size > 100 bytes (prevents empty/stub files)

**Level 3: Structure**
- Has at least one markdown header (## )

**Level 4: Type-Specific Sections**

| Type | Required Sections |
|------|-------------------|
| spec.md | "## Success Criteria" OR "## Acceptance Criteria" |
| design.md | "## Components" OR "## Architecture" |
| plan.md | "## Implementation Order" OR "## Phase" |
| tasks.md | "## Phase" OR "### Task" |

**Implementation:**
```
function validateArtifact(path, type):
  # Level 1
  if not exists(path):
    return { valid: false, level: 1, error: "File not found" }

  content = read(path)

  # Level 2
  if len(content) < 100:
    return { valid: false, level: 2, error: "File appears empty or stub (< 100 bytes)" }

  # Level 3
  if not contains(content, "## "):
    return { valid: false, level: 3, error: "Missing markdown structure (no ## headers)" }

  # Level 4
  requiredSections = getSectionsForType(type)
  foundAny = false
  for section in requiredSections:
    if contains(content, section):
      foundAny = true
      break

  if not foundAny:
    return { valid: false, level: 4, error: "Missing required sections: {requiredSections}" }

  return { valid: true }
```

**Usage in Commands:**
Commands with hard prerequisites should call validateArtifact instead of just checking existence:
- `/iflow-dev:implement` validates spec.md
- `/iflow-dev:create-tasks` validates plan.md

---

## State Schema

The `.meta.json` file in each feature folder:

```json
{
  "id": "006",
  "slug": "feature-slug",
  "mode": "standard",
  "status": "active",
  "created": "2026-01-30T00:00:00Z",
  "completed": null,
  "branch": "feature/006-feature-slug",
  "brainstorm_source": "docs/brainstorms/20260130-143052-feature-slug.prd.md",
  "backlog_source": "00001",
  "lastCompletedPhase": "specify",
  "skippedPhases": [],
  "phases": {
    "specify": {
      "started": "2026-01-30T01:00:00Z",
      "completed": "2026-01-30T02:00:00Z",
      "iterations": 1,
      "reviewerNotes": []
    }
  }
}
```

### Core Fields

| Field | Type | Description |
|-------|------|-------------|
| id | string | Zero-padded feature number (e.g., "006") |
| slug | string | Hyphenated feature name |
| mode | string | One of: standard, full |
| status | string | One of: active, completed, abandoned |
| created | ISO8601 | Feature creation timestamp |
| completed | ISO8601/null | Completion timestamp (null if active) |
| branch | string | Git branch name |

### Source Tracking Fields

| Field | Type | Description |
|-------|------|-------------|
| brainstorm_source | string/null | Path to original PRD if promoted from brainstorm |
| backlog_source | string/null | Backlog item ID if promoted from backlog |

### Skip Tracking Fields

| Field | Type | Description |
|-------|------|-------------|
| skippedPhases | array | Record of phases skipped via soft prerequisites |

**skippedPhases Entry Structure:**
```json
{
  "phase": "design",
  "skippedAt": "2026-01-30T01:00:00Z",
  "fromPhase": "specify",
  "toPhase": "create-plan"
}
```

When user confirms skipping phases via AskUserQuestion soft prerequisite warning:
1. Read current `.meta.json`
2. Append to `skippedPhases` array for each skipped phase
3. Write updated `.meta.json`
4. Proceed with target phase

### Phase Tracking Fields

| Field | Type | Description |
|-------|------|-------------|
| lastCompletedPhase | string/null | Last completed phase name (null until first phase completes) |
| phases | object | Phase tracking object with started/completed timestamps |

### Phase Object Structure

Each phase entry in `phases` contains:

| Field | Type | Description |
|-------|------|-------------|
| started | ISO8601 | When phase execution began |
| completed | ISO8601/null | When phase completed (null if in progress) |
| iterations | number | Number of review iterations performed |
| reviewerNotes | array | Unresolved concerns from reviewer |
| stages | object | (design phase only) Sub-stage tracking |

### Design Phase Stages Schema

See [references/design-stages-schema.md](references/design-stages-schema.md) for the full 4-stage design workflow schema, stage descriptions, field definitions, and partial recovery logic.

### Status Values

| Status | Meaning | Terminal? |
|--------|---------|-----------|
| active | Work in progress | No |
| completed | Merged/finished successfully | Yes |
| abandoned | Discarded intentionally | Yes |

Terminal statuses cannot be changed. New work requires a new feature.

### Status Updates

The `/iflow-dev:finish` command updates status to terminal values:

```json
// For completed features
{ "status": "completed", "completed": "{ISO timestamp}" }

// For abandoned features
{ "status": "abandoned", "completed": "{ISO timestamp}" }
```

## Review History

During development, `.review-history.md` tracks iteration feedback.
On `/iflow-dev:finish`, this file is deleted (git has the permanent record).
