---
description: Create specification for current feature
argument-hint: [--no-review]
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

Get max iterations from mode: Hotfix=1, Quick=2, Standard=3, Full=5.

**If `--no-review` argument is present:** Skip to step 4e directly after producing artifact. Set `reviewSkipped: true` in `.meta.json`.

**Otherwise, execute this loop:**

a. **Produce artifact:** Follow the specifying skill to create/revise spec.md

b. **Invoke reviewer:** Use the Task tool to spawn chain-reviewer:
   ```
   Task tool call:
     description: "Review spec for chain sufficiency"
     subagent_type: chain-reviewer
     prompt: |
       Review the following artifacts for chain sufficiency.

       ## Previous Artifact (brainstorm.md)
       {content of brainstorm.md, or "None - this is the first phase" if doesn't exist}

       ## Current Artifact (spec.md)
       {content of spec.md}

       ## Next Phase Expectations
       Design needs: All requirements listed, acceptance criteria defined,
       scope boundaries clear.

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
     - Address the issues by revising spec.md
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
