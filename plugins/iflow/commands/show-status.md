---
description: Show current feature state and progress
argument-hint: [feature-id]
---

# /iflow:show-status Command

Display the current state of a feature.

## Determine Feature

1. If argument provided: Use that feature ID
2. If on feature branch: Extract feature ID from branch name pattern `feature/{id}-{slug}`
3. Otherwise: List recent features and ask

## Gather State

Read `docs/features/{id}-{slug}/`:

| File | Exists? | Phase Status |
|------|---------|--------------|
| brainstorm.md | ✓/✗ | Brainstorm complete/pending |
| spec.md | ✓/✗ | Spec complete/pending |
| design.md | ✓/✗ | Design complete/pending |
| plan.md | ✓/✗ | Plan complete/pending |
| tasks.md | ✓/✗ | Tasks complete/pending |

Current phase = first missing artifact (or "implement" if all exist)

## Check Execution Progress

If Vibe-Kanban available:
- Get card status
- Get task completion counts

If TodoWrite:
- Check task list status

## Display Status

```
Feature: {id}-{slug}
Mode: {mode}
Phase: {current-phase}

Artifacts:
  ✓ brainstorm.md
  ✓ spec.md
  ○ design.md (current)
  ○ plan.md
  ○ tasks.md

Progress: {completed}/{total} tasks (if in implement phase)

Next: Run /iflow:design to continue
```

## If No Feature Active

```
No active feature detected.

Recent features:
  42-user-auth (design phase)
  41-search (complete)

Run /iflow:create-feature to start a new feature
or /iflow:show-status {id} to check a specific feature
```
