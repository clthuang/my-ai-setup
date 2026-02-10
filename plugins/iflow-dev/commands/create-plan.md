---
description: Create implementation plan for current feature
argument-hint: "[--feature=<id-slug>]"
---

Invoke the planning skill for the current feature context.

Read docs/features/ to find active feature, then follow the workflow below.

## Workflow Integration

### 1-3. Validate, Branch Check, Partial Recovery, Mark Started

Follow `validateAndSetup("create-plan")` from the **workflow-transitions** skill.

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

       ## PRD (original requirements)
       {content of prd.md, or "None - feature created without brainstorm"}

       ## Spec (requirements)
       {content of spec.md}

       ## Design (architecture)
       {content of design.md}

       ## Plan (what you're reviewing)
       {content of plan.md}

       Return JSON: {"approved": bool, "issues": [{"severity": "blocker|warning|suggestion", "description": "...", "location": "...", "suggestion": "..."}], "summary": "..."}
   ```

c. **Parse response:** Extract `approved` field.

d. **Branch on result (strict threshold):**
   - **PASS:** `approved: true` AND zero issues with severity "blocker" or "warning"
   - **FAIL:** `approved: false` OR any issue has severity "blocker" or "warning"
   - If PASS → Proceed to Stage 2
   - If FAIL AND iteration < max:
     - Append to `.review-history.md` with "Stage 1: Plan Review" marker
     - Address all blocker AND warning issues, return to 4b (always a NEW Task tool dispatch per iteration)
   - If FAIL AND iteration == max:
     - Note concerns in `.meta.json` reviewerNotes
     - Proceed to Stage 2 with warning

#### Stage 2: Chain-Reviewer Validation (Execution Readiness)

Phase-reviewer iteration budget: max 3 (independent of Stage 1).

Set `phase_iteration = 0`.

e. **Invoke phase-reviewer** (always a NEW Task tool dispatch per iteration):
   ```
   Task tool call:
     description: "Validate plan ready for task breakdown"
     subagent_type: iflow-dev:phase-reviewer
     prompt: |
       Validate this plan is ready for an experienced engineer
       to break into executable tasks.

       ## PRD (original requirements)
       {content of prd.md, or "None - feature created without brainstorm"}

       ## Spec (requirements)
       {content of spec.md}

       ## Design (architecture)
       {content of design.md}

       ## Plan (what you're reviewing)
       {content of plan.md}

       ## Next Phase Expectations
       Tasks needs: Ordered steps with dependencies,
       all design items covered, clear sequencing.

       This is phase-review iteration {phase_iteration}/3.

       Return JSON: {"approved": bool, "issues": [{"severity": "blocker|warning|suggestion", "description": "...", "location": "...", "suggestion": "..."}], "summary": "..."}
   ```

f. **Parse response:** Extract `approved` field.

g. **Branch on result (strict threshold):**
   - **PASS:** `approved: true` AND zero issues with severity "blocker" or "warning"
   - **FAIL:** `approved: false` OR any issue has severity "blocker" or "warning"
   - If PASS → Proceed to step 4h
   - If FAIL AND phase_iteration < 3:
     - Append to `.review-history.md` with "Stage 2: Chain Review" marker
     - Increment phase_iteration
     - Address all blocker AND warning issues
     - Return to 4e (new agent instance)
   - If FAIL AND phase_iteration == 3:
     - Note concerns in `.meta.json` phaseReview.reviewerNotes
     - Proceed to 4h with warning

h. **Complete phase:** Proceed to auto-commit, then update state.

### 4b. Auto-Commit and Update State

Follow `commitAndComplete("create-plan", ["plan.md"])` from the **workflow-transitions** skill.

### 6. Completion Message

Output: "Plan complete."

```
AskUserQuestion:
  questions: [{
    "question": "Plan complete. Continue to next phase?",
    "header": "Next Step",
    "options": [
      {"label": "Continue to /iflow-dev:create-tasks (Recommended)", "description": "Break plan into actionable tasks"},
      {"label": "Review plan.md first", "description": "Inspect the plan before continuing"}
    ],
    "multiSelect": false
  }]
```

If "Continue to /iflow-dev:create-tasks (Recommended)": Invoke `/iflow-dev:create-tasks`
If "Review plan.md first": Show "Plan at {path}/plan.md. Run /iflow-dev:create-tasks when ready." → STOP
