---
name: workflow-state
description: Central workflow state management. Defines phase sequence, validates transitions, and provides state update patterns. Use before any phase command to check prerequisites.
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
| /implement | spec.md | "spec.md required before implementation. Run /specify first." |
| /create-tasks | plan.md | "plan.md required before task creation. Run /create-plan first." |

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

The `.meta.json` file in each feature folder:

```json
{
  "id": "003",
  "name": "feature-slug",
  "mode": "standard",
  "status": "active",
  "created": "2026-01-30T00:00:00Z",
  "completed": null,
  "worktree": "../project-003-feature-slug",
  "currentPhase": "design",
  "phases": {
    "brainstorm": {
      "started": "2026-01-30T00:00:00Z",
      "completed": "2026-01-30T01:00:00Z",
      "verified": true,
      "iterations": 1
    },
    "specify": {
      "started": "2026-01-30T01:00:00Z",
      "completed": "2026-01-30T02:00:00Z",
      "verified": true,
      "iterations": 2,
      "reviewerNotes": ["Minor clarity issues accepted"]
    }
  }
}
```

### Status Values

| Status | Meaning | Terminal? |
|--------|---------|-----------|
| active | Work in progress | No |
| completed | Merged/finished successfully | Yes |
| abandoned | Discarded intentionally | Yes |

Terminal statuses cannot be changed. New work requires a new feature.

## State Update Pattern

Use read-modify-write pattern to update `.meta.json`:

### 1. Read Current State

```
Read docs/features/{id}-{slug}/.meta.json
Parse JSON into state object
```

### 2. Apply Updates

```
function updatePhaseState(state, phaseName, updates):
  # Initialize phase if needed
  if phaseName not in state.phases:
    state.phases[phaseName] = {}

  # Merge updates
  for key, value in updates:
    state.phases[phaseName][key] = value

  # Update currentPhase if this phase is now the furthest completed
  if updates.completed:
    state.currentPhase = phaseName

  return state
```

### 3. Write Back

```
Write updated JSON to .meta.json
Use pretty-print with 2-space indent
```

### Example Updates

**Mark phase started:**
```json
{
  "started": "2026-01-30T12:00:00Z"
}
```

**Mark phase completed:**
```json
{
  "completed": "2026-01-30T13:00:00Z",
  "iterations": 2
}
```

**Mark phase verified:**
```json
{
  "verified": true
}
```

**Mark with reviewer notes:**
```json
{
  "completed": "2026-01-30T13:00:00Z",
  "iterations": 3,
  "reviewerNotes": ["Concern about X accepted", "Concern about Y deferred"]
}
```

## Iteration Limits by Mode

| Mode | Max Iterations | Description |
|------|----------------|-------------|
| Hotfix | 1 | Single pass, no revision |
| Quick | 2 | One revision allowed |
| Standard | 3 | Up to two revisions |
| Full | 5 | Thorough iteration |

When max iterations reached without approval, mark phase complete with `reviewerNotes` containing unresolved concerns.

## Partial Phase Detection

Before starting a phase, check if it was previously started but not completed:

```
if phases[phaseName].started and not phases[phaseName].completed:
  # Partial phase detected
  Ask user:
  1. Continue from existing draft
  2. Start fresh (reset started timestamp)
  3. Review existing before deciding
```

## Review History

During development, iteration details are stored in `.review-history.md`:

```markdown
## Phase: design

### Iteration 1 - 2026-01-30T12:00:00Z

**Reviewer Feedback:**
Not approved - missing interface definitions

**Issues:**
- [blocker] No interface contracts defined
- [warning] Risk section incomplete

**Changes Made:**
Added Interface section with 3 contracts

---

### Iteration 2 - 2026-01-30T12:30:00Z

**Reviewer Feedback:**
Approved

**Summary:**
All design elements present and sufficient for planning phase.
```

On `/finish`, delete `.review-history.md` (history served its purpose, git has the record).
