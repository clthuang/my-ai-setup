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
| brainstorm | brainstorm.md | (entry point) |
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

All other out-of-order transitions produce a **warning** but allow proceeding:

```
⚠️ Skipping {skipped phases}. This may reduce artifact quality.
Continue anyway? (y/n)
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

The `.meta.json` file in each feature folder uses a minimal schema:

```json
{
  "id": "006",
  "slug": "feature-slug",
  "mode": "standard",
  "status": "active",
  "created": "2026-01-30T00:00:00Z",
  "completed": null,
  "branch": "feature/006-feature-slug"
}
```

| Field | Type | Description |
|-------|------|-------------|
| id | string | Zero-padded feature number (e.g., "006") |
| slug | string | Hyphenated feature name |
| mode | string | One of: standard, full |
| status | string | One of: active, completed, abandoned |
| created | ISO8601 | Feature creation timestamp |
| completed | ISO8601/null | Completion timestamp (null if active) |
| branch | string | Git branch name |

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
