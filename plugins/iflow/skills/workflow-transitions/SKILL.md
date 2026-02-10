---
name: workflow-transitions
description: Shared workflow boilerplate for phase commands. Use when a command needs to validate transitions, check branches, handle partial phases, mark started, auto-commit, and update state.
---

# Workflow Transitions

Shared procedures used by all phase commands (specify, design, create-plan, create-tasks, implement, finish). Commands reference these procedures instead of inlining identical boilerplate.

## validateAndSetup(phaseName)

Execute steps 1-3 in order. Stop on any blocking result.

### Step 1: Validate Transition

Check prerequisites using workflow-state skill:
- Read current `.meta.json` state
- Apply validateTransition logic for target phase `{phaseName}`
- If blocked: Show error, stop

**If backward** (re-running completed phase):
```
AskUserQuestion:
  questions: [{
    "question": "Phase '{phaseName}' was already completed. Re-running will update timestamps but not undo previous work. Continue?",
    "header": "Backward",
    "options": [
      {"label": "Continue", "description": "Re-run the phase"},
      {"label": "Cancel", "description": "Stay at current phase"}
    ],
    "multiSelect": false
  }]
```
If "Cancel": Stop execution.

**If warning** (skipping phases):
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
If "Continue": Record skipped phases in `.meta.json` skippedPhases array, then proceed.
If "Stop": Stop execution.

### Step 2: Check Branch

If feature has a branch defined in `.meta.json`:
- Get current branch: `git branch --show-current`
- If current branch != expected branch, use AskUserQuestion:
  ```
  AskUserQuestion:
    questions: [{
      "question": "You're on '{current}', but feature uses '{expected}'. Switch branches?",
      "header": "Branch",
      "options": [
        {"label": "Switch", "description": "Run: git checkout {expected}"},
        {"label": "Continue", "description": "Stay on {current}"}
      ],
      "multiSelect": false
    }]
  ```
- Skip this check if branch is null (legacy feature)

### Step 3: Check for Partial Phase

If `phases.{phaseName}.started` exists but `phases.{phaseName}.completed` is null:
```
AskUserQuestion:
  questions: [{
    "question": "Detected partial {phaseName} work. How to proceed?",
    "header": "Recovery",
    "options": [
      {"label": "Continue", "description": "Resume from where you left off"},
      {"label": "Start Fresh", "description": "Discard and begin new"},
      {"label": "Review First", "description": "View progress before deciding"}
    ],
    "multiSelect": false
  }]
```

### Step 4: Mark Phase Started

Update `.meta.json`:
```json
{
  "phases": {
    "{phaseName}": {
      "started": "{ISO timestamp}"
    }
  }
}
```

## commitAndComplete(phaseName, artifacts[])

Execute after phase work and reviews are done.

### Step 1: Auto-Commit

```bash
git add {artifacts joined by space} docs/features/{id}-{slug}/.meta.json docs/features/{id}-{slug}/.review-history.md
git commit -m "phase({phaseName}): {slug} - approved"
git push
```

**Error handling:**
- On commit failure: Display error, do NOT mark phase completed, allow retry
- On push failure: Commit succeeds locally, warn user with "Run: git push" instruction, mark phase completed

### Step 2: Update State

Update `.meta.json`:
```json
{
  "phases": {
    "{phaseName}": {
      "completed": "{ISO timestamp}",
      "iterations": {count},
      "reviewerNotes": ["any unresolved concerns"]
    }
  },
  "lastCompletedPhase": "{phaseName}"
}
```
