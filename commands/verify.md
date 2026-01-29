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

**WARNING:** If verifying a phase that isn't marked completed:
```
⚠️ Phase {phase} is not marked complete.
Verifying incomplete work may give misleading results.
Continue anyway? (y/n)
```

### 1b. Check Worktree Location

If feature has a worktree defined in `.meta.json`:
- Compare current working directory against worktree path
- If mismatch and not already warned this session:
  ```
  ⚠️ You are not in the feature worktree.
  Current: {cwd}
  Worktree: {worktree}
  Continue anyway? (y/n)
  ```
- Skip this check if worktree is null (Hotfix mode)

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
Fix the issues and re-run /verify, or proceed anyway.
```

Note: Verify is the review itself - no reviewer loop needed. The verifying skill performs the quality check.
