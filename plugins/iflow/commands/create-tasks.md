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
BLOCKED: plan.md required before task creation.

Task breakdown requires an implementation plan to work from.
Run /iflow:create-plan first to create the plan.
```
Stop execution. Do not proceed.

- If warning (skipping other phases): Show warning, ask to proceed

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

### 2. Check for Partial Phase

If `phases.create-tasks.started` exists but `phases.create-tasks.completed` is null, use AskUserQuestion:
```
AskUserQuestion:
  questions: [{
    "question": "Detected partial task breakdown work. How to proceed?",
    "header": "Recovery",
    "options": [
      {"label": "Continue", "description": "Resume from draft"},
      {"label": "Start Fresh", "description": "Discard and begin new"},
      {"label": "Review First", "description": "View existing before deciding"}
    ],
    "multiSelect": false
  }]
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

### 4. Stage 1: Task Breakdown with Review Loop

Get max iterations from mode: Standard=1, Full=3.

Execute this loop:

a. **Produce artifact:** Follow the breaking-down-tasks skill to create/revise tasks.md

b. **Invoke task-breakdown-reviewer:** Use the Task tool:
   ```
   Task tool call:
     description: "Review task breakdown quality"
     subagent_type: task-breakdown-reviewer
     prompt: |
       Review the task breakdown for quality and executability.

       ## Implementation Plan (plan.md)
       {content of plan.md}

       ## Task Breakdown (tasks.md)
       {content of tasks.md}

       Validate:
       1. Plan fidelity - every plan item has tasks
       2. Task executability - any engineer can start immediately
       3. Task size - 5-15 min each
       4. Dependency accuracy - parallel groups correct
       5. Testability - binary done criteria

       Return your assessment as JSON:
       {
         "approved": true/false,
         "issues": [{"severity": "blocker|warning|note", "task": "...", "description": "...", "suggestion": "..."}],
         "summary": "..."
       }
   ```

c. **Parse response:** Extract the `approved` field from reviewer's JSON response.
   - If response is not valid JSON, ask reviewer to retry with correct format.

d. **Branch on result:**
   - If `approved: true` → Proceed to Stage 2 (step 5)
   - If `approved: false` AND iteration < max:
     - Append iteration to `.review-history.md` using format below
     - Increment iteration counter
     - Address the issues by revising tasks.md
     - Return to step 4b
   - If `approved: false` AND iteration == max:
     - Note concerns in `.meta.json` taskReview.concerns
     - Proceed to Stage 2 (step 5)

**Review History Entry Format** (append to `.review-history.md`):
```markdown
## Task Review Iteration {n} - {ISO timestamp}

**Decision:** {Approved / Needs Revision}

**Issues:**
- [{severity}] {task}: {description} → {suggestion}

**Changes Made:**
{Summary of revisions made to address issues}

---
```

### 5. Stage 2: Chain Validation

After Stage 1 completes, invoke chain-reviewer for final validation:

```
Task tool call:
  description: "Validate chain readiness for implementation"
  subagent_type: chain-reviewer
  prompt: |
    Review the task breakdown for chain sufficiency.

    ## Previous Artifact (plan.md)
    {content of plan.md}

    ## Current Artifact (tasks.md)
    {content of tasks.md}

    ## Next Phase Expectations
    Implement needs: Small actionable tasks (<15 min each),
    clear acceptance criteria per task, dependency graph for parallel execution.

    Return your assessment as JSON:
    {
      "approved": true/false,
      "issues": [...],
      "summary": "..."
    }
```

**Branch on result:**
- If `approved: true` → Proceed to step 6
- If `approved: false` → Note concerns in `.meta.json` chainReview.concerns, proceed to step 6

### 6. Update State on Completion

Update `.meta.json`:
```json
{
  "phases": {
    "create-tasks": {
      "completed": "{ISO timestamp}",
      "taskReview": {
        "iterations": {count},
        "approved": true/false,
        "concerns": []
      },
      "chainReview": {
        "approved": true/false,
        "concerns": []
      }
    }
  },
  "currentPhase": "create-tasks"
}
```

### 7. Completion Message and Next Step

Show completion message:
"Tasks created. {n} tasks across {m} phases, {p} parallel groups."

Then use AskUserQuestion:
```
AskUserQuestion:
  questions: [{
    "question": "Run /iflow:implement next?",
    "header": "Next",
    "options": [
      {"label": "Yes (Recommended)", "description": "Start implementation"},
      {"label": "Review tasks first", "description": "Read tasks.md"}
    ],
    "multiSelect": false
  }]
```
