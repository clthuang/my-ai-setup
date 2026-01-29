---
description: Start or continue implementation of current feature
---

Invoke the implementing skill for the current feature context.

Read docs/features/ to find active feature, then follow the workflow below.

## Workflow Integration

### 1. Validate Transition (HARD PREREQUISITE)

Before executing, check prerequisites using workflow-state skill:
- Read current `.meta.json` state
- Check for spec.md existence

**HARD BLOCK:** If spec.md does not exist:
```
❌ BLOCKED: spec.md required before implementation.

Implementation requires a specification to implement against.
Run /specify first to create the specification.
```
Stop execution. Do not proceed.

- If warning (skipping other phases like tasks): Show warning, ask to proceed

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

If `phases.implement.started` exists but `phases.implement.completed` is null:
```
Detected partial implementation work.
1. Continue from where you left off
2. Start fresh
3. Review progress before deciding
```

### 3. Mark Phase Started

Update `.meta.json`:
```json
{
  "phases": {
    "implement": {
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

  a. Execute implementing skill → produce/revise code

  b. Spawn chain-reviewer agent with:
     - Previous artifact: tasks.md (or spec.md if no tasks)
     - Current artifact: implementation summary (files changed, tests)
     - Next phase expectations: "Verify needs: All tasks addressed,
       tests exist/pass, no obvious issues"

  c. IF reviewer approves:
     - Continue to final validation (step 5)
     - BREAK

  d. IF NOT approved AND iteration < max:
     - Append to .review-history.md
     - iteration++
     - Revise based on feedback
     - CONTINUE

  e. IF NOT approved AND iteration == max:
     - Continue to final validation with concerns noted
     - BREAK
```

### 5. Final Validation (Spec Compliance)

After chain review passes (or max iterations):

```
Spawn final-reviewer agent with:
- spec.md: Original specification
- Implementation files: All files created/modified

IF final-reviewer finds issues:
  - Present issues to user
  - Ask: "Address these concerns or proceed anyway?"
  - If address: Loop back to implementation
  - If proceed: Note in reviewerNotes

IF final-reviewer approves:
  - Mark phase completed
```

### 6. Update State on Completion

Update `.meta.json`:
```json
{
  "phases": {
    "implement": {
      "completed": "{ISO timestamp}",
      "iterations": {count},
      "reviewerNotes": ["any unresolved concerns from chain or final review"]
    }
  },
  "currentPhase": "implement"
}
```

### 7. Completion Message

"Implementation complete. Run /verify for quality review, then /finish when ready."
