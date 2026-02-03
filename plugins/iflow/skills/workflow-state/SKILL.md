---
name: workflow-state
description: Central workflow state management. Defines phase sequence, validates transitions, and provides state update patterns. Use when checking phase prerequisites.
---

# Workflow State Management

Manage feature workflow state and validate phase transitions.

## Phase Sequence

The canonical workflow order:

```
brainstorm → specify → design → create-plan → create-tasks → implement → verify → finish
```

| Phase | Produces | Required Before |
|-------|----------|-----------------|
| brainstorm | prd.md | (entry point) |
| specify | spec.md | design, implement |
| design | design.md | create-plan |
| create-plan | plan.md | create-tasks |
| create-tasks | tasks.md | implement |
| implement | code changes | verify |
| verify | verification | finish |
| finish | (terminal) | — |

## Transition Validation

Before executing any phase command, validate the transition.

### Hard Prerequisites (Block)

These transitions are **blocked** if prerequisites are missing:

| Target Phase | Required Artifact | Error Message |
|--------------|-------------------|---------------|
| /iflow:implement | spec.md | "spec.md required before implementation. Run /iflow:specify first." |
| /iflow:create-tasks | plan.md | "plan.md required before task creation. Run /iflow:create-plan first." |

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
- Any phase → verify (out of order) → warn

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

  # Check if skipping phases
  sequence = [brainstorm, specify, design, create-plan, create-tasks, implement, verify, finish]
  currentIndex = sequence.indexOf(currentPhase) or -1
  targetIndex = sequence.indexOf(targetPhase)

  if targetIndex > currentIndex + 1:
    skipped = sequence[currentIndex+1 : targetIndex]
    return { allowed: true, type: "warning", message: "Skipping {skipped}..." }

  return { allowed: true, type: "proceed", message: null }
```

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
  "currentPhase": "specify",
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

### Phase Tracking Fields

| Field | Type | Description |
|-------|------|-------------|
| currentPhase | string/null | Last completed phase name (null until first phase completes) |
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

The design phase uses a 4-stage workflow with detailed tracking:

```json
{
  "phases": {
    "design": {
      "started": "2026-01-30T01:00:00Z",
      "completed": "2026-01-30T02:00:00Z",
      "stages": {
        "architecture": {
          "started": "2026-01-30T01:00:00Z",
          "completed": "2026-01-30T01:15:00Z"
        },
        "interface": {
          "started": "2026-01-30T01:15:00Z",
          "completed": "2026-01-30T01:30:00Z"
        },
        "designReview": {
          "started": "2026-01-30T01:30:00Z",
          "completed": "2026-01-30T01:45:00Z",
          "iterations": 2,
          "reviewerNotes": []
        },
        "handoffReview": {
          "started": "2026-01-30T01:45:00Z",
          "completed": "2026-01-30T01:50:00Z",
          "approved": true,
          "reviewerNotes": []
        }
      }
    }
  }
}
```

### Stage Descriptions

| Stage | Purpose | Reviewer |
|-------|---------|----------|
| architecture | High-level structure, components, decisions, risks | None (validated in designReview) |
| interface | Precise contracts between components | None (validated in designReview) |
| designReview | Challenge assumptions, find gaps, ensure robustness | design-reviewer (skeptic) |
| handoffReview | Ensure plan phase has everything it needs | chain-reviewer (gatekeeper) |

### Stage Object Fields

**architecture / interface:**
| Field | Type | Description |
|-------|------|-------------|
| started | ISO8601 | When stage began |
| completed | ISO8601/null | When stage completed |

**designReview:**
| Field | Type | Description |
|-------|------|-------------|
| started | ISO8601 | When stage began |
| completed | ISO8601/null | When stage completed |
| iterations | number | Review iterations (1-3 based on mode) |
| reviewerNotes | array | Unresolved concerns from design-reviewer |

**handoffReview:**
| Field | Type | Description |
|-------|------|-------------|
| started | ISO8601 | When stage began |
| completed | ISO8601/null | When stage completed |
| approved | boolean | Whether chain-reviewer approved |
| reviewerNotes | array | Concerns noted by chain-reviewer |

### Recovery from Partial Design Phase

When recovering from interrupted design phase, detect the incomplete stage:

1. Check which stages have `started` but not `completed`
2. The first incomplete stage is the current stage
3. Offer user options: Continue from current stage, Start fresh, or Review first

### Status Values

| Status | Meaning | Terminal? |
|--------|---------|-----------|
| active | Work in progress | No |
| completed | Merged/finished successfully | Yes |
| abandoned | Discarded intentionally | Yes |

Terminal statuses cannot be changed. New work requires a new feature.

### Status Updates

The `/iflow:finish` command updates status to terminal values:

```json
// For completed features
{ "status": "completed", "completed": "{ISO timestamp}" }

// For abandoned features
{ "status": "abandoned", "completed": "{ISO timestamp}" }
```

## Review History

During development, `.review-history.md` tracks iteration feedback.
On `/iflow:finish`, this file is deleted (git has the permanent record).
