---
description: Create specification for current feature
---

Invoke the specifying skill for the current feature context.

First, check docs/features/ for active feature:
- If not found: "No active feature found. Would you like to /brainstorm to explore ideas first?"
- If found: Read feature context and follow the workflow below.

## Workflow Integration

### 1. Validate Transition

Before executing, check prerequisites using workflow-state skill:
- Read current `.meta.json` state
- Apply validateTransition logic for target phase "specify"
- If blocked: Show error, stop
- If warning (skipping phases): Show warning, ask to proceed

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

If `phases.specify.started` exists but `phases.specify.completed` is null:
```
Detected partial specification work.
1. Continue from existing draft
2. Start fresh
3. Review existing before deciding
```

### 3. Mark Phase Started

Update `.meta.json`:
```json
{
  "phases": {
    "specify": {
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

  a. Execute specifying skill → produce/revise spec.md

  b. Spawn chain-reviewer agent with:
     - Previous artifact: brainstorm.md (if exists)
     - Current artifact: spec.md
     - Next phase expectations: "Design needs: All requirements listed,
       acceptance criteria defined, scope boundaries clear"

  c. IF reviewer approves:
     - Mark phase completed
     - Present: "Specification complete ({iteration} iterations)"
     - BREAK

  d. IF NOT approved AND iteration < max:
     - Append to .review-history.md
     - iteration++
     - Revise based on feedback
     - CONTINUE

  e. IF NOT approved AND iteration == max:
     - Mark phase completed with reviewerNotes
     - Present: "Specification complete. Reviewer concerns: [issues]"
     - BREAK
```

### 5. Update State on Completion

Update `.meta.json`:
```json
{
  "phases": {
    "specify": {
      "completed": "{ISO timestamp}",
      "iterations": {count},
      "reviewerNotes": ["any unresolved concerns"]
    }
  },
  "currentPhase": "specify"
}
```

### 6. Completion Message

"Specification complete. Run /verify to check, or /design to continue."
