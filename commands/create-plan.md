---
description: Create implementation plan for current feature
---

Invoke the planning skill for the current feature context.

Read docs/features/ to find active feature, then follow the workflow below.

## Workflow Integration

### 1. Validate Transition

Before executing, check prerequisites using workflow-state skill:
- Read current `.meta.json` state
- Apply validateTransition logic for target phase "create-plan"
- If blocked: Show error, stop
- If warning (skipping phases like design): Show warning, ask to proceed

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

If `phases.create-plan.started` exists but `phases.create-plan.completed` is null:
```
Detected partial planning work.
1. Continue from existing draft
2. Start fresh
3. Review existing before deciding
```

### 3. Mark Phase Started

Update `.meta.json`:
```json
{
  "phases": {
    "create-plan": {
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

  a. Execute planning skill → produce/revise plan.md

  b. Spawn chain-reviewer agent with:
     - Previous artifact: design.md
     - Current artifact: plan.md
     - Next phase expectations: "Tasks needs: Ordered steps with dependencies,
       all design items covered, clear sequencing"

  c. IF reviewer approves:
     - Mark phase completed
     - Present: "Plan complete ({iteration} iterations)"
     - BREAK

  d. IF NOT approved AND iteration < max:
     - Append to .review-history.md
     - iteration++
     - Revise based on feedback
     - CONTINUE

  e. IF NOT approved AND iteration == max:
     - Mark phase completed with reviewerNotes
     - Present: "Plan complete. Reviewer concerns: [issues]"
     - BREAK
```

### 5. Update State on Completion

Update `.meta.json`:
```json
{
  "phases": {
    "create-plan": {
      "completed": "{ISO timestamp}",
      "iterations": {count},
      "reviewerNotes": ["any unresolved concerns"]
    }
  },
  "currentPhase": "create-plan"
}
```

### 6. Completion Message

"Plan complete. Run /verify to check, or /create-tasks to continue."
