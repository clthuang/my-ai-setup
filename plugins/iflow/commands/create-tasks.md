---
description: Break down plan into actionable tasks
argument-hint: "[--feature=<id-slug>]"
---

Invoke the breaking-down-tasks skill for the current feature context.

Read docs/features/ to find active feature, then follow the workflow below.

## Workflow Integration

### 1-3. Validate, Branch Check, Partial Recovery, Mark Started

Follow `validateAndSetup("create-tasks")` from the **workflow-transitions** skill.

**Hard prerequisite:** Before standard validation, validate plan.md using `validateArtifact(path, "plan.md")`. If validation fails:
```
BLOCKED: Valid plan.md required before task creation.

{Level 1}: plan.md not found. Run /iflow:create-plan first.
{Level 2}: plan.md appears empty or stub. Run /iflow:create-plan to complete it.
{Level 3}: plan.md missing markdown structure. Run /iflow:create-plan to fix.
{Level 4}: plan.md missing required sections (Implementation Order or Phase). Run /iflow:create-plan to add them.
```
Stop execution. Do not proceed.

### 4. Stage 1: Task Breakdown with Review Loop

Get max iterations from mode: Standard=1, Full=3.

Execute this loop:

a. **Produce artifact:** Follow the breaking-down-tasks skill to create/revise tasks.md

b. **Invoke task-reviewer:** Use the Task tool:
   ```
   Task tool call:
     description: "Review task breakdown quality"
     subagent_type: iflow:task-reviewer
     prompt: |
       Review the task breakdown for quality and executability.

       ## Spec (requirements)
       {content of spec.md}

       ## Design (architecture)
       {content of design.md}

       ## Plan (what tasks should cover)
       {content of plan.md}

       ## Tasks (what you're reviewing)
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
         "issues": [{"severity": "blocker|warning|suggestion", "task": "...", "description": "...", "suggestion": "..."}],
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

After Stage 1 completes, invoke phase-reviewer for final validation:

```
Task tool call:
  description: "Validate tasks ready for implementation"
  subagent_type: iflow:phase-reviewer
  prompt: |
    Validate this task breakdown is ready for implementation.

    ## Spec (requirements)
    {content of spec.md}

    ## Design (architecture)
    {content of design.md}

    ## Plan (what tasks should cover)
    {content of plan.md}

    ## Tasks (what you're reviewing)
    {content of tasks.md}

    ## Next Phase Expectations
    Implement needs: Small actionable tasks (<15 min each),
    clear acceptance criteria per task, dependency graph for parallel execution.

    Return your assessment as JSON:
    {
      "approved": true/false,
      "issues": [{"severity": "blocker|warning|suggestion", "description": "...", "location": "...", "suggestion": "..."}],
      "summary": "..."
    }
```

**Branch on result:**
- If `approved: true` → Proceed to step 5b
- If `approved: false` → Note concerns in `.meta.json` chainReview.concerns, proceed to step 5b

### 5b. Auto-Commit and Update State

Follow `commitAndComplete("create-tasks", ["tasks.md"])` from the **workflow-transitions** skill.

Create-tasks additionally records taskReview and chainReview sub-objects in the phase state.

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
