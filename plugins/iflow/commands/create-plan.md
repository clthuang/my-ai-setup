---
description: Create implementation plan for current feature
argument-hint: "[--feature=<id-slug>]"
---

Invoke the planning skill for the current feature context.

Read docs/features/ to find active feature, then follow the workflow below.

## Workflow Integration

### 1-3. Validate, Branch Check, Partial Recovery, Mark Started

Follow `validateAndSetup("create-plan")` from the **workflow-transitions** skill.

**Hard prerequisite:** Before standard validation, validate design.md using `validateArtifact(path, "design.md")`. If validation fails:
```
BLOCKED: Valid design.md required before planning.

{Level 1}: design.md not found. Run /iflow:design first.
{Level 2}: design.md appears empty or stub. Run /iflow:design to complete it.
{Level 3}: design.md missing markdown structure. Run /iflow:design to fix.
{Level 4}: design.md missing required sections (Components or Architecture). Run /iflow:design to add them.
```
Stop execution. Do not proceed.

### 4. Execute with Two-Stage Reviewer Loop

Max iterations: 5.

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

Phase-reviewer iteration budget: max 5 (independent of Stage 1).

Set `phase_iteration = 0`.

e. **Invoke phase-reviewer** (always a NEW Task tool dispatch per iteration):
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

       ## Domain Reviewer Outcome
       - Reviewer: plan-reviewer
       - Result: {APPROVED at iteration {n}/{max} | FAILED at iteration cap ({max}/{max})}
       - Unresolved issues: {list of remaining blocker/warning descriptions, or "none"}

       ## Next Phase Expectations
       Tasks needs: Ordered steps with dependencies,
       all design items covered, clear sequencing.

       This is phase-review iteration {phase_iteration}/5.

       Return JSON: {"approved": bool, "issues": [{"severity": "blocker|warning|suggestion", "description": "...", "location": "...", "suggestion": "..."}], "summary": "..."}
   ```

f. **Parse response:** Extract `approved` field.

g. **Branch on result (strict threshold):**
   - **PASS:** `approved: true` AND zero issues with severity "blocker" or "warning"
   - **FAIL:** `approved: false` OR any issue has severity "blocker" or "warning"
   - If PASS → Proceed to step 4h
   - If FAIL AND phase_iteration < 5:
     - Append to `.review-history.md` with "Stage 2: Chain Review" marker
     - Increment phase_iteration
     - Address all blocker AND warning issues
     - Return to 4e (new agent instance)
   - If FAIL AND phase_iteration == 5:
     - Note concerns in `.meta.json` phaseReview.reviewerNotes
     - Proceed to 4h with warning

h. **Complete phase:** Proceed to auto-commit, then update state.

### 4b. Auto-Commit and Update State

Follow `commitAndComplete("create-plan", ["plan.md"])` from the **workflow-transitions** skill.

### 6. Completion Message

Output: "Plan complete."

**YOLO Mode:** If `[YOLO_MODE]` is active, skip the AskUserQuestion and directly invoke
`/iflow:create-tasks` with `[YOLO_MODE]` in args.

```
AskUserQuestion:
  questions: [{
    "question": "Plan complete. Continue to next phase?",
    "header": "Next Step",
    "options": [
      {"label": "Continue to /iflow:create-tasks (Recommended)", "description": "Break plan into actionable tasks"},
      {"label": "Review plan.md first", "description": "Inspect the plan before continuing"},
      {"label": "Fix and rerun reviews", "description": "Apply fixes then rerun Stage 1 + Stage 2 review cycle"}
    ],
    "multiSelect": false
  }]
```

If "Continue to /iflow:create-tasks (Recommended)": Invoke `/iflow:create-tasks`
If "Review plan.md first": Show "Plan at {path}/plan.md. Run /iflow:create-tasks when ready." → STOP
If "Fix and rerun reviews": Ask user what needs fixing (plain text via AskUserQuestion with free-text), apply the requested changes to plan.md, then return to Step 4 (Stage 1 plan-reviewer) with iteration counters reset to 0.
