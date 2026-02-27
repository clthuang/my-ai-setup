---
description: Create implementation plan for current feature
argument-hint: "[--feature=<id-slug>]"
---

Invoke the planning skill for the current feature context.

## Config Variables
Use these values from session context (injected at session start):
- `{iflow_artifacts_root}` — root directory for feature artifacts (default: `docs`)

Read {iflow_artifacts_root}/features/ to find active feature, then follow the workflow below.

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

b. **Invoke plan-reviewer:**

   **PRD resolution (I8):** Before dispatching, resolve the PRD reference:
   1. Check if `{feature_path}/prd.md` exists
   2. If exists → PRD line = `- PRD: {feature_path}/prd.md`
   3. If not → check `.meta.json` for `brainstorm_source`
      a. If found → PRD line = `- PRD: {brainstorm_source path}`
      b. If not → PRD line = `- PRD: No PRD — feature created without brainstorm`

   Use Task tool:
   ```
   Task tool call:
     description: "Skeptical review of plan for failure modes"
     subagent_type: iflow:plan-reviewer
     model: opus
     prompt: |
       Review this plan for failure modes, untested assumptions,
       dependency accuracy, and TDD order compliance.

       ## Required Artifacts
       You MUST read the following files before beginning your review.
       After reading, confirm: "Files read: {name} ({N} lines), ..." in a single line.
       {resolved PRD line from I8}
       - Spec: {feature_path}/spec.md
       - Design: {feature_path}/design.md

       Return JSON: {"approved": bool, "issues": [{"severity": "blocker|warning|suggestion", "description": "...", "location": "...", "suggestion": "..."}], "summary": "..."}

       ## Plan (what you're reviewing)
       {content of plan.md}
   ```

c. **Parse response:** Extract `approved` field.

   **Fallback detection (I9):** Search the agent's response for "Files read:" pattern. If not found, log `LAZY-LOAD-WARNING: plan-reviewer did not confirm artifact reads` to `.review-history.md`. Proceed regardless.

d. **Branch on result (strict threshold):**
   - **PASS:** `approved: true` AND zero issues with severity "blocker" or "warning"
   - **FAIL:** `approved: false` OR any issue has severity "blocker" or "warning"
   - If PASS → Proceed to Stage 2
   - If FAIL AND iteration < max:
     - Append to `.review-history.md` with "Stage 1: Plan Review" marker
     - Address all blocker AND warning issues, return to 4b (Fresh dispatch per iteration — Phase 1 behavior. Phase 2 design defines resume support.)
   - If FAIL AND iteration == max:
     - Note concerns in `.meta.json` reviewerNotes
     - Proceed to Stage 2 with warning

#### Stage 2: Chain-Reviewer Validation (Execution Readiness)

Phase-reviewer iteration budget: max 5 (independent of Stage 1).

Set `phase_iteration = 0`.

e. **Invoke phase-reviewer** (Fresh dispatch per iteration — Phase 1 behavior. Phase 2 design defines resume support.):

   **PRD resolution (I8):** Before dispatching, resolve the PRD reference (same logic as Stage 1).

   ```
   Task tool call:
     description: "Validate plan ready for task breakdown"
     subagent_type: iflow:phase-reviewer
     model: sonnet
     prompt: |
       Validate this plan is ready for an experienced engineer
       to break into executable tasks.

       ## Required Artifacts
       You MUST read the following files before beginning your review.
       After reading, confirm: "Files read: {name} ({N} lines), ..." in a single line.
       {resolved PRD line from I8}
       - Spec: {feature_path}/spec.md
       - Design: {feature_path}/design.md
       - Plan: {feature_path}/plan.md

       ## Next Phase Expectations
       Tasks needs: Ordered steps with dependencies,
       all design items covered, clear sequencing.

       Return JSON: {"approved": bool, "issues": [{"severity": "blocker|warning|suggestion", "description": "...", "location": "...", "suggestion": "..."}], "summary": "..."}

       ## Domain Reviewer Outcome
       - Reviewer: plan-reviewer
       - Result: {APPROVED at iteration {n}/{max} | FAILED at iteration cap ({max}/{max})}
       - Unresolved issues: {list of remaining blocker/warning descriptions, or "none"}

       This is phase-review iteration {phase_iteration}/5.
   ```

f. **Parse response:** Extract `approved` field.

   **Fallback detection (I9):** Search the agent's response for "Files read:" pattern. If not found, log `LAZY-LOAD-WARNING: phase-reviewer did not confirm artifact reads` to `.review-history.md`. Proceed regardless.

g. **Branch on result (strict threshold):**
   - **PASS:** `approved: true` AND zero issues with severity "blocker" or "warning"
   - **FAIL:** `approved: false` OR any issue has severity "blocker" or "warning"
   - If PASS → Proceed to step 4h
   - If FAIL AND phase_iteration < 5:
     - Append to `.review-history.md` with "Stage 2: Chain Review" marker
     - Increment phase_iteration
     - Address all blocker AND warning issues
     - Return to 4e (Fresh dispatch per iteration — Phase 1 behavior. Phase 2 design defines resume support.)
   - If FAIL AND phase_iteration == 5:
     - Note concerns in `.meta.json` phaseReview.reviewerNotes
     - Proceed to 4h with warning

h. **Complete phase:** Proceed to auto-commit, then update state.

### 4a. Capture Review Learnings (Automatic)

**Trigger:** Only execute if the review loop ran 2+ iterations (across Stage 1 and/or Stage 2 combined). If approved on first pass in both stages, skip — no review learnings to capture.

**Process:**
1. Read `.review-history.md` entries for THIS phase only (plan-reviewer and phase-reviewer entries)
2. Group issues by description similarity (same category, overlapping file patterns)
3. Identify issues that appeared in 2+ iterations — these are recurring patterns

**For each recurring issue, call `store_memory`:**
- `name`: derived from issue description (max 60 chars)
- `description`: issue description + the suggestion that resolved it
- `reasoning`: "Recurred across {n} review iterations in feature {id} create-plan phase"
- `category`: infer from issue type:
  - Security issues → `anti-patterns`
  - Quality/SOLID/naming → `heuristics`
  - Missing requirements → `anti-patterns`
  - Feasibility/complexity → `heuristics`
  - Scope/assumption issues → `heuristics`
- `references`: ["feature/{id}-{slug}"]
- `confidence`: "low"

**Budget:** Max 3 entries per review cycle to avoid noise.

**Circuit breaker capture:** If review loop hit max iterations (cap reached) in either stage, also capture a single entry:
- `name`: "Plan review cap: {brief issue category}"
- `description`: summary of unresolved issues that prevented approval
- `category`: "anti-patterns"
- `confidence`: "low"

**Fallback:** If `store_memory` MCP tool unavailable, use `semantic_memory.writer` CLI.

**Output:** `"Review learnings: {n} patterns captured from {m}-iteration review cycle"` (inline, no prompt)

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
