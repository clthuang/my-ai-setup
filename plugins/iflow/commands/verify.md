---
description: Run verification for current phase
---

Invoke the verifying skill for the current feature context.

Read docs/features/ to find active feature and determine phase, then follow the workflow below.

## Workflow Integration

### 1. Validate Transition

Before executing, check state using workflow-state skill:
- Read current `.meta.json` state
- Determine which phase to verify (most recent completed phase)
- If backward (re-running completed verification): Use AskUserQuestion:
  ```
  AskUserQuestion:
    questions: [{
      "question": "Phase 'verify' was already completed. Re-running will update timestamps but not undo previous work. Continue?",
      "header": "Backward",
      "options": [
        {"label": "Continue", "description": "Re-run verification"},
        {"label": "Cancel", "description": "Stay at current phase"}
      ],
      "multiSelect": false
    }]
  ```
  If "Cancel": Stop execution.

**WARNING:** If verifying a phase that isn't marked completed, use AskUserQuestion:
```
AskUserQuestion:
  questions: [{
    "question": "Phase {phase} is not marked complete. Verifying incomplete work may give misleading results. Continue anyway?",
    "header": "Verify",
    "options": [
      {"label": "Continue", "description": "Proceed with verification"},
      {"label": "Stop", "description": "Cancel verification"}
    ],
    "multiSelect": false
  }]
```

### 1b. Check Branch

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

### 1c. Check for Partial Phase

If `phases.verify.started` exists but `phases.verify.completed` is null:

```
AskUserQuestion:
  questions: [{
    "question": "Detected partial verification. How to proceed?",
    "header": "Recovery",
    "options": [
      {"label": "Continue", "description": "Resume from where you left off"},
      {"label": "Start Fresh", "description": "Begin verification anew"}
    ],
    "multiSelect": false
  }]
```

If "Start Fresh": Clear `phases.verify.started` from `.meta.json`.

### 2. Execute Verification

Follow verifying skill instructions:
- Determine current phase from artifacts
- Apply phase-appropriate checklist
- Report issues by severity (blocker, warning, note)

### 3. Update State on Pass

If verification passes (no blockers):

Update `.meta.json`:
```json
{
  "phases": {
    "{verified-phase}": {
      "verified": true
    }
  }
}
```

### 4. Completion Message

**If PASS:**
```
Verification passed for {phase}.
Ready for next phase: {suggested next command}
```

**If NEEDS FIXES:**
```
Verification found issues for {phase}.
Fix the issues and re-run /iflow-dev:verify, or proceed anyway.
```

Note: Verify is the review itself - no reviewer loop needed. The verifying skill performs the quality check.
