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
     subagent_type: iflow:plan-reviewer
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

d. **Branch on result:**
   - `approved: true` → Proceed to Stage 2
   - `approved: false` AND iteration < max:
     - Append to `.review-history.md` with "Stage 1: Plan Review" marker
     - Address issues, return to 4b
   - `approved: false` AND iteration == max:
     - Note concerns in `.meta.json` reviewerNotes
     - Proceed to Stage 2 with warning

#### Stage 2: Chain-Reviewer Validation (Execution Readiness)

e. **Invoke phase-reviewer:** Use Task tool:
   ```
   Task tool call:
     description: "Validate plan ready for task breakdown"
     subagent_type: iflow:phase-reviewer
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

       Return JSON: {"approved": bool, "issues": [{"severity": "blocker|warning|suggestion", "description": "...", "location": "...", "suggestion": "..."}], "summary": "..."}
   ```

f. **Parse response:** Extract `approved` field.

g. **Branch on result:**
   - `approved: true` → Proceed to step 4h
   - `approved: false`:
     - Append to `.review-history.md` with "Stage 2: Chain Review" marker
     - If iteration < max: Address issues, return to 4e (phase-reviewer)
     - If iteration == max: Note concerns, proceed to 4h

h. **Complete phase:** Proceed to auto-commit, then update state.

### 4b. Auto-Commit and Update State

Follow `commitAndComplete("create-plan", ["plan.md"])` from the **workflow-transitions** skill.

### 6. User Prompt for Next Step

After phase-reviewer approval, ask user:

```
AskUserQuestion:
  questions: [{
    "question": "Plan approved by reviewers. Run /iflow:create-tasks?",
    "header": "Next Step",
    "options": [
      {"label": "Yes", "description": "Break plan into actionable tasks"},
      {"label": "No", "description": "Review plan.md manually first"}
    ],
    "multiSelect": false
  }]
```

Based on selection:
- "Yes" → Invoke /iflow:create-tasks
- "No" → Show: "Plan at {path}/plan.md. Run /iflow:create-tasks when ready."
