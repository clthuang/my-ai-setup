---
description: Create architecture design for current feature
---

Invoke the designing skill for the current feature context.

Read docs/features/ to find active feature, then follow the workflow below.

## Workflow Integration

### 1. Validate Transition

Before executing, check prerequisites using workflow-state skill:
- Read current `.meta.json` state
- Apply validateTransition logic for target phase "design"
- If blocked: Show error, stop
- If warning (skipping phases like specify): Show warning, ask to proceed

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

### 2. Check for Partial Phase

If `phases.design.started` exists but `phases.design.completed` is null:
```
Detected partial design work.
1. Continue from existing draft
2. Start fresh
3. Review existing before deciding
```

### 3. Mark Phase Started

Update `.meta.json`:
```json
{
  "phases": {
    "design": {
      "started": "{ISO timestamp}"
    }
  }
}
```

### 4. Execute with Reviewer Loop

Get max iterations from mode (Hotfix=1, Quick=2, Standard=3, Full=5).

```
iteration = 1
WHILE iteration <= max_iterations:

  a. Execute designing skill → produce/revise design.md

  b. Spawn chain-reviewer agent with:
     - Previous artifact: spec.md
     - Current artifact: design.md
     - Next phase expectations: "Plan needs: Components defined,
       interfaces specified, dependencies identified, risks noted"

  c. IF reviewer approves:
     - Mark phase completed
     - Present: "Design complete ({iteration} iterations)"
     - BREAK

  d. IF NOT approved AND iteration < max:
     - Append to .review-history.md
     - iteration++
     - Revise based on feedback
     - CONTINUE

  e. IF NOT approved AND iteration == max:
     - Mark phase completed with reviewerNotes
     - Present: "Design complete. Reviewer concerns: [issues]"
     - BREAK
```

### 5. Update State on Completion

Update `.meta.json`:
```json
{
  "phases": {
    "design": {
      "completed": "{ISO timestamp}",
      "iterations": {count},
      "reviewerNotes": ["any unresolved concerns"]
    }
  },
  "currentPhase": "design"
}
```

### 6. Completion Message

"Design complete. Run /verify to check, or /create-plan to continue."
