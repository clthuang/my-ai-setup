---
description: Create architecture design for current feature
argument-hint: [--no-review]
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

Get max iterations from mode: Standard=1, Full=3.

**If `--no-review` argument is present:** Skip to step 4e directly after producing artifact. Set `reviewSkipped: true` in `.meta.json`.

**Otherwise, execute this loop:**

a. **Produce artifact:** Follow the designing skill to create/revise design.md

b. **Invoke reviewer:** Use the Task tool to spawn chain-reviewer:
   ```
   Task tool call:
     description: "Review design for chain sufficiency"
     subagent_type: chain-reviewer
     prompt: |
       Review the following artifacts for chain sufficiency.

       ## Previous Artifact (spec.md)
       {content of spec.md}

       ## Current Artifact (design.md)
       {content of design.md}

       ## Next Phase Expectations
       Plan needs: Components defined, interfaces specified,
       dependencies identified, risks noted.

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
     - Address the issues by revising design.md
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

"Design complete. Saved to design.md."

Present planning options:

```
How would you like to create your implementation plan?

1. Claude Code Plan Mode
   - Read-only analysis mode with approval workflow
   - Enter: Press Shift+Tab until showing "⏸ plan mode on"
   - Prompt: "Create implementation plan for docs/features/{id}-{slug}/design.md, output to plan.md"
   - Edit plan: Press Ctrl+G to open in editor
   - Execute: Say "proceed with the plan"

2. iflow /iflow:create-plan (Recommended for workflow tracking)
   - Creates plan.md with dependency graphs
   - Includes chain-reviewer verification loop
   - Updates .meta.json phase tracking

Choose [1-2] or press Enter for 2:
```

**If Option 1 (Claude Code Plan Mode):**
- Inform: "To enter plan mode:"
- Show instructions:
  ```
  1. Press Shift+Tab until you see "⏸ plan mode on" indicator
  2. Provide: "Create implementation plan based on docs/features/{id}-{slug}/design.md. Output to docs/features/{id}-{slug}/plan.md"
  3. Refine the plan interactively
  4. Press Ctrl+G to edit plan in your editor
  5. Say "proceed with the plan" when ready
  ```
- Note: "Phase tracking won't be updated until you run /iflow:create-tasks"
- Do NOT auto-continue (user switches modes manually)

**If Option 2 (iflow /iflow:create-plan):**
- Inform: "Continuing with /iflow:create-plan..."
- Auto-invoke `/iflow:create-plan`
