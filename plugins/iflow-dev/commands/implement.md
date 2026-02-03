---
description: Start or continue implementation of current feature
argument-hint: [--no-review]
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
Run /iflow-dev:specify first to create the specification.
```
Stop execution. Do not proceed.

- If warning (skipping other phases like tasks): Show warning, ask to proceed

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

If `phases.implement.started` exists but `phases.implement.completed` is null, use AskUserQuestion:
```
AskUserQuestion:
  questions: [{
    "question": "Detected partial implementation work. How to proceed?",
    "header": "Recovery",
    "options": [
      {"label": "Continue", "description": "Resume from where you left off"},
      {"label": "Start Fresh", "description": "Discard and begin new"},
      {"label": "Review First", "description": "View progress before deciding"}
    ],
    "multiSelect": false
  }]
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

Get max iterations from mode: Standard=1, Full=3.

**If `--no-review` argument is present:** Skip to step 5 directly after producing implementation. Set `reviewSkipped: true` in `.meta.json`.

**Otherwise, execute this loop:**

a. **Produce artifact:** Follow the implementing skill to produce/revise code

b. **Invoke reviewer:** Use the Task tool to spawn chain-reviewer:
   ```
   Task tool call:
     description: "Review implementation for chain sufficiency"
     subagent_type: chain-reviewer
     prompt: |
       Review the following artifacts for chain sufficiency.

       ## Previous Artifact (tasks.md)
       {content of tasks.md, or spec.md if no tasks}

       ## Current Artifact (implementation summary)
       Files changed:
       {list of files created/modified}

       Tests:
       {test results summary}

       ## Next Phase Expectations
       Verify needs: All tasks addressed, tests exist/pass,
       no obvious issues.

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
   - If `approved: true` → Continue to step 5 (final validation)
   - If `approved: false` AND iteration < max:
     - Append iteration to `.review-history.md` using format below
     - Increment iteration counter
     - Address the issues by revising implementation
     - Return to step 4b
   - If `approved: false` AND iteration == max:
     - Continue to step 5 with concerns noted in reviewerNotes

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

"Implementation complete. Run /iflow-dev:verify for quality review, then /iflow-dev:finish when ready."
