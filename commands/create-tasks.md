---
description: Break down plan into actionable tasks
---

Invoke the breaking-down-tasks skill for the current feature context.

Read docs/features/ to find active feature, then follow the workflow below.

## Workflow Integration

### 1. Validate Transition (HARD PREREQUISITE)

Before executing, check prerequisites using workflow-state skill:
- Read current `.meta.json` state
- Check for plan.md existence

**HARD BLOCK:** If plan.md does not exist:
```
❌ BLOCKED: plan.md required before task creation.

Task breakdown requires an implementation plan to work from.
Run /create-plan first to create the plan.
```
Stop execution. Do not proceed.

- If warning (skipping other phases): Show warning, ask to proceed

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

If `phases.create-tasks.started` exists but `phases.create-tasks.completed` is null:
```
Detected partial task breakdown work.
1. Continue from existing draft
2. Start fresh
3. Review existing before deciding
```

### 3. Mark Phase Started

Update `.meta.json`:
```json
{
  "phases": {
    "create-tasks": {
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

  a. Execute breaking-down-tasks skill → produce/revise tasks.md

  b. Spawn chain-reviewer agent with:
     - Previous artifact: plan.md
     - Current artifact: tasks.md
     - Next phase expectations: "Implement needs: Small actionable tasks
       (<15 min each), clear acceptance criteria per task"

  c. IF reviewer approves:
     - Mark phase completed
     - Present: "Tasks complete ({iteration} iterations)"
     - BREAK

  d. IF NOT approved AND iteration < max:
     - Append to .review-history.md
     - iteration++
     - Revise based on feedback
     - CONTINUE

  e. IF NOT approved AND iteration == max:
     - Mark phase completed with reviewerNotes
     - Present: "Tasks complete. Reviewer concerns: [issues]"
     - BREAK
```

### 5. Update State on Completion

Update `.meta.json`:
```json
{
  "phases": {
    "create-tasks": {
      "completed": "{ISO timestamp}",
      "iterations": {count},
      "reviewerNotes": ["any unresolved concerns"]
    }
  },
  "currentPhase": "create-tasks"
}
```

### 6. Completion Message

"Tasks created. Run /verify to check, or /implement to start building."
