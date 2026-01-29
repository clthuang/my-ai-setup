---
description: Create implementation plan for current feature
argument-hint: [--no-review]
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

Get max iterations from mode: Hotfix=1, Quick=2, Standard=3, Full=5.

**If `--no-review` argument is present:** Skip to step 4e directly after producing artifact. Set `reviewSkipped: true` in `.meta.json`.

**Otherwise, execute this loop:**

a. **Produce artifact:** Follow the planning skill to create/revise plan.md

b. **Invoke reviewer:** Use the Task tool to spawn chain-reviewer:
   ```
   Task tool call:
     description: "Review plan for chain sufficiency"
     subagent_type: chain-reviewer
     prompt: |
       Review the following artifacts for chain sufficiency.

       ## Previous Artifact (design.md)
       {content of design.md}

       ## Current Artifact (plan.md)
       {content of plan.md}

       ## Next Phase Expectations
       Tasks needs: Ordered steps with dependencies,
       all design items covered, clear sequencing.

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
     - Address the issues by revising plan.md
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
