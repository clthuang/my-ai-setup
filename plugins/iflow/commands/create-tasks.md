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

Max iterations: 5.

Execute this loop:

a. **Produce artifact:** Follow the breaking-down-tasks skill to create/revise tasks.md

b. **Invoke task-reviewer:** Use the Task tool:
   ```
   Task tool call:
     description: "Review task breakdown quality"
     subagent_type: iflow:task-reviewer
     prompt: |
       Review the task breakdown for quality and executability.

       ## PRD (original requirements)
       {content of prd.md, or "None - feature created without brainstorm"}

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

d. **Branch on result (strict threshold):**
   - **PASS:** `approved: true` AND zero issues with severity "blocker" or "warning"
   - **FAIL:** `approved: false` OR any issue has severity "blocker" or "warning"
   - If PASS → Proceed to Stage 2 (step 5)
   - If FAIL AND iteration < max:
     - Append iteration to `.review-history.md` using format below
     - Increment iteration counter
     - Address all blocker AND warning issues by revising tasks.md
     - Return to step 4b (always a NEW Task tool dispatch per iteration)
   - If FAIL AND iteration == max:
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

### 5. Stage 2: Chain Validation (Handoff Gate)

Phase-reviewer iteration budget: max 5 (independent of Stage 1).

Set `phase_iteration = 0`.

After Stage 1 completes, invoke phase-reviewer (always a NEW Task tool dispatch per iteration):

```
Task tool call:
  description: "Validate tasks ready for implementation"
  subagent_type: iflow:phase-reviewer
  prompt: |
    Validate this task breakdown is ready for implementation.

    ## PRD (original requirements)
    {content of prd.md, or "None - feature created without brainstorm"}

    ## Spec (requirements)
    {content of spec.md}

    ## Design (architecture)
    {content of design.md}

    ## Plan (what tasks should cover)
    {content of plan.md}

    ## Tasks (what you're reviewing)
    {content of tasks.md}

    ## Domain Reviewer Outcome
    - Reviewer: task-reviewer
    - Result: {APPROVED at iteration {n}/{max} | FAILED at iteration cap ({max}/{max})}
    - Unresolved issues: {list of remaining blocker/warning descriptions, or "none"}

    ## Next Phase Expectations
    Implement needs: Small actionable tasks (<15 min each),
    clear acceptance criteria per task, dependency graph for parallel execution.

    This is phase-review iteration {phase_iteration}/5.

    Return your assessment as JSON:
    {
      "approved": true/false,
      "issues": [{"severity": "blocker|warning|suggestion", "description": "...", "location": "...", "suggestion": "..."}],
      "summary": "..."
    }
```

**Branch on result (strict threshold):**
- **PASS:** `approved: true` AND zero issues with severity "blocker" or "warning"
- **FAIL:** `approved: false` OR any issue has severity "blocker" or "warning"
- If PASS → Proceed to step 5b
- If FAIL AND phase_iteration < 5:
  - Append to `.review-history.md` with "Stage 2: Chain Review" marker
  - Increment phase_iteration
  - Address all blocker AND warning issues
  - Return to phase-reviewer invocation (new agent instance)
- If FAIL AND phase_iteration == 5:
  - Store concerns in `.meta.json` chainReview.concerns
  - Proceed to step 5b with warning

### 5b. Auto-Commit and Update State

Follow `commitAndComplete("create-tasks", ["tasks.md"])` from the **workflow-transitions** skill.

Create-tasks additionally records taskReview and chainReview sub-objects in the phase state.

### 7. Completion Message and Next Step

Output: "Tasks created. {n} tasks across {m} phases, {p} parallel groups."

**YOLO Mode:** If `[YOLO_MODE]` is active, skip the AskUserQuestion and directly invoke
`/iflow:implement` with `[YOLO_MODE]` in args.

```
AskUserQuestion:
  questions: [{
    "question": "Tasks complete. Continue to next phase?",
    "header": "Next Step",
    "options": [
      {"label": "Continue to /iflow:implement (Recommended)", "description": "Start implementation"},
      {"label": "Review tasks.md first", "description": "Inspect the tasks before continuing"},
      {"label": "Fix and rerun reviews", "description": "Apply fixes then rerun Stage 1 + Stage 2 review cycle"}
    ],
    "multiSelect": false
  }]
```

If "Continue to /iflow:implement (Recommended)": Invoke `/iflow:implement`
If "Review tasks.md first": Show "Tasks at {path}/tasks.md. Run /iflow:implement when ready." → STOP
If "Fix and rerun reviews": Ask user what needs fixing (plain text via AskUserQuestion with free-text), apply the requested changes to tasks.md, then return to Step 4 (Stage 1 task-reviewer) with iteration counters reset to 0.
