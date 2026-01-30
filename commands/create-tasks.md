---
description: Break down plan into actionable tasks
argument-hint: [--no-review]
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

### 1b. Check Branch

If feature has a branch defined in `.meta.json`:
- Get current branch: `git branch --show-current`
- If current branch != expected branch:
  ```
  ⚠️ You're on branch '{current}', but feature uses '{expected}'.

  Switch branches:
    git checkout {expected}

  Or continue on current branch? (y/n)
  ```
- Skip this check if branch is null (legacy feature)

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

Get max iterations from mode: Hotfix=1, Quick=2, Standard=3, Full=5.

**If `--no-review` argument is present:** Skip to step 4e directly after producing artifact. Set `reviewSkipped: true` in `.meta.json`.

**Otherwise, execute this loop:**

a. **Produce artifact:** Follow the breaking-down-tasks skill to create/revise tasks.md

b. **Invoke reviewer:** Use the Task tool to spawn chain-reviewer:
   ```
   Task tool call:
     description: "Review tasks for chain sufficiency"
     subagent_type: chain-reviewer
     prompt: |
       Review the following artifacts for chain sufficiency.

       ## Previous Artifact (plan.md)
       {content of plan.md}

       ## Current Artifact (tasks.md)
       {content of tasks.md}

       ## Next Phase Expectations
       Implement needs: Small actionable tasks (<15 min each),
       clear acceptance criteria per task.

       Return your assessment as JSON:
       {
         "approved": true/false,
         "issues": [...],
         "summary": "..."
       }
   ```

c. **Parse response:** Extract the `approved` field from reviewer's JSON response.
   - If response is not valid JSON, ask reviewer to retry with correct format.

d. **Branch on result:**
   - If `approved: true` → Proceed to step 4e
   - If `approved: false` AND iteration < max:
     - Append iteration to `.review-history.md` using format below
     - Increment iteration counter
     - Address the issues by revising tasks.md
     - Return to step 4b
   - If `approved: false` AND iteration == max:
     - Note concerns in `.meta.json` reviewerNotes
     - Proceed to step 4e

e. **Complete phase:** Update state and show completion message.

**Review History Entry Format** (append to `.review-history.md`):
```markdown
## Iteration {n} - {ISO timestamp}

**Decision:** {Approved / Needs Revision}

**Issues:**
- [{severity}] {description} (at: {location})

**Changes Made:**
{Summary of revisions made to address issues}

---
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
