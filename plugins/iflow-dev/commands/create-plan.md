---
description: Create implementation plan for current feature
---

Invoke the planning skill for the current feature context.

Read docs/features/ to find active feature, then follow the workflow below.

## Workflow Integration

### 1. Validate Transition

Before executing, check prerequisites using workflow-state skill:
- Read current `.meta.json` state
- Apply validateTransition logic for target phase "create-plan"
- If blocked: Show error, stop
- If backward (re-running completed phase): Use AskUserQuestion:
  ```
  AskUserQuestion:
    questions: [{
      "question": "Phase 'create-plan' was already completed. Re-running will update timestamps but not undo previous work. Continue?",
      "header": "Backward",
      "options": [
        {"label": "Continue", "description": "Re-run the phase"},
        {"label": "Cancel", "description": "Stay at current phase"}
      ],
      "multiSelect": false
    }]
  ```
  If "Cancel": Stop execution.
- If warning (skipping phases like design): Show warning via AskUserQuestion:
  ```
  AskUserQuestion:
    questions: [{
      "question": "Skipping {skipped phases}. This may reduce artifact quality. Continue anyway?",
      "header": "Skip",
      "options": [
        {"label": "Continue", "description": "Proceed despite skipping phases"},
        {"label": "Stop", "description": "Return to complete skipped phases"}
      ],
      "multiSelect": false
    }]
  ```
  If "Continue": Record skipped phases in `.meta.json` skippedPhases array, then proceed.
  If "Stop": Stop execution.

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

If `phases.create-plan.started` exists but `phases.create-plan.completed` is null, use AskUserQuestion:
```
AskUserQuestion:
  questions: [{
    "question": "Detected partial planning work. How to proceed?",
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
    "create-plan": {
      "started": "{ISO timestamp}"
    }
  }
}
```

### 4. Execute with Two-Stage Reviewer Loop

Get max iterations from mode: Standard=1, Full=3.

#### Stage 1: Plan-Reviewer Cycle (Skeptical Review)

a. **Produce artifact:** Follow the planning skill to create/revise plan.md

b. **Invoke plan-reviewer:** Use Task tool:
   ```
   Task tool call:
     description: "Skeptical review of plan for failure modes"
     subagent_type: iflow-dev:plan-reviewer
     prompt: |
       Review this plan for failure modes, untested assumptions,
       dependency accuracy, and TDD order compliance.

       ## Design Artifact
       {content of design.md}

       ## Plan Artifact
       {content of plan.md}

       Return JSON: {"approved": bool, "issues": [...], "summary": "..."}
   ```

c. **Parse response:** Extract `approved` field.

d. **Branch on result:**
   - `approved: true` → Proceed to Stage 2
   - `approved: false` AND iteration < max:
     - Append to `.review-history.md` with "Stage 1: Plan Review" marker
     - Address issues, return to 4b
   - `approved: false` AND iteration == max:
     - Note concerns in `.meta.json` reviewerNotes
     - Proceed to Stage 2 with warning

#### Stage 2: Chain-Reviewer Validation (Execution Readiness)

e. **Invoke chain-reviewer:** Use Task tool:
   ```
   Task tool call:
     description: "Validate plan ready for task breakdown"
     subagent_type: iflow-dev:chain-reviewer
     prompt: |
       Validate this plan is ready for an experienced engineer
       to break into executable tasks.

       ## Design Artifact
       {content of design.md}

       ## Plan Artifact
       {content of plan.md}

       ## Next Phase Expectations
       Tasks needs: Ordered steps with dependencies,
       all design items covered, clear sequencing.

       Return JSON: {"approved": bool, "issues": [...], "summary": "..."}
   ```

f. **Parse response:** Extract `approved` field.

g. **Branch on result:**
   - `approved: true` → Proceed to step 4h
   - `approved: false`:
     - Append to `.review-history.md` with "Stage 2: Chain Review" marker
     - If iteration < max: Address issues, return to 4e (chain-reviewer)
     - If iteration == max: Note concerns, proceed to 4h

h. **Complete phase:** Update state.

**Review History Entry Format** (append to `.review-history.md`):
```markdown
## {Stage 1: Plan Review | Stage 2: Chain Review} - Iteration {n} - {ISO timestamp}

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

### 6. User Prompt for Next Step

After chain-reviewer approval, ask user:

```
AskUserQuestion:
  questions: [{
    "question": "Plan approved by reviewers. Run /iflow-dev:create-tasks?",
    "header": "Next Step",
    "options": [
      {"label": "Yes", "description": "Break plan into actionable tasks"},
      {"label": "No", "description": "Review plan.md manually first"}
    ],
    "multiSelect": false
  }]
```

Based on selection:
- "Yes" → Invoke /iflow-dev:create-tasks
- "No" → Show: "Plan at {path}/plan.md. Run /iflow-dev:create-tasks when ready."
