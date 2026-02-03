---
description: Create specification for current feature
argument-hint: [--feature=<id-slug>]
---

Invoke the specifying skill for the current feature context.

## Determine Target Feature

**If `--feature` argument provided:**
- Use `docs/features/{feature}/` directly
- If folder doesn't exist: Error "Feature {feature} not found"
- If `.meta.json` missing: Error "Feature {feature} has no metadata"

**If no argument:**
1. Scan `docs/features/` for folders with `.meta.json` where `status="active"`
2. If none found: "No active feature found. Would you like to /iflow-dev:brainstorm to explore ideas first?"
3. If one found: Use that feature
4. If multiple found:
   ```
   AskUserQuestion:
     questions: [{
       "question": "Multiple active features found. Which one?",
       "header": "Feature",
       "options": [dynamically list each active feature as {id}-{slug}],
       "multiSelect": false
     }]
   ```

Once target feature is determined, read feature context and follow the workflow below.

## Workflow Integration

### 1. Ensure Correct Branch

Read `.meta.json` for branch name.
If current branch != expected:
- Run: `git checkout {expected}`
- Output: "Switched to branch {expected}."

Skip this check if branch is null (legacy feature).

### 2. Check for Partial Phase

If `phases.specify.started` exists but `phases.specify.completed` is null, use AskUserQuestion:
```
AskUserQuestion:
  questions: [{
    "question": "Found partial spec. How to proceed?",
    "header": "Recovery",
    "options": [
      {"label": "Continue", "description": "Resume from draft"},
      {"label": "Start Fresh", "description": "Delete draft and begin new"}
    ],
    "multiSelect": false
  }]
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

Get max iterations from mode: Standard=1, Full=3.

a. **Produce artifact:** Follow the specifying skill to create/revise spec.md

b. **Invoke reviewer:** Use the Task tool to spawn chain-reviewer:
   ```
   Task tool call:
     description: "Review spec for chain sufficiency"
     subagent_type: iflow-dev:chain-reviewer
     prompt: |
       Review the following artifacts for chain sufficiency.

       ## Previous Artifact (prd.md)
       {content of prd.md, or "None - feature created without brainstorm"}

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

Output: "Specification complete."

```
AskUserQuestion:
  questions: [{
    "question": "Ready for the next phase?",
    "header": "Next Step",
    "options": [
      {"label": "Continue to /design", "description": "Create architecture design"},
      {"label": "Stop here", "description": "End session"}
    ],
    "multiSelect": false
  }]
```

If "Continue to /design": Invoke `/iflow-dev:design`
If "Stop here": STOP
