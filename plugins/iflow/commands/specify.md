---
description: Create specification for current feature
argument-hint: [--feature=<id-slug>]
---

Invoke the specifying skill for the current feature context.

## Config Variables
Use these values from session context (injected at session start):
- `{iflow_artifacts_root}` — root directory for feature artifacts (default: `docs`)

## YOLO Mode Overrides

If `[YOLO_MODE]` is active:
- Multiple active features → auto-select most recently created (highest ID)
- Completion prompt → skip AskUserQuestion, directly invoke `/iflow:design` with `[YOLO_MODE]`

## Determine Target Feature

**If `--feature` argument provided:**
- Use `{iflow_artifacts_root}/features/{feature}/` directly
- If folder doesn't exist: Error "Feature {feature} not found"
- If `.meta.json` missing: Error "Feature {feature} has no metadata"

**If no argument:**
1. Scan `{iflow_artifacts_root}/features/` for folders with `.meta.json` where `status="active"`
2. If none found: "No active feature found. Would you like to /iflow:brainstorm to explore ideas first?"
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

### 1-3. Validate, Branch Check, Partial Recovery, Mark Started

Follow `validateAndSetup("specify")` from the **workflow-transitions** skill.

### 4. Execute with Two-Stage Reviewer Loop

Max iterations: 5.

#### Stage 1: Spec-Reviewer Review (Quality Gate)

a. **Produce artifact:** Follow the specifying skill to create/revise spec.md

b. **Invoke spec-reviewer:** Use the Task tool to spawn spec-reviewer (the skeptic):
   ```
   Task tool call:
     description: "Skeptical review of spec quality"
     subagent_type: iflow:spec-reviewer
     model: opus
     prompt: |
       Skeptically review spec.md for testability, assumptions, and scope discipline.

       ## PRD (original requirements)
       {content of prd.md, or "None - feature created without brainstorm"}

       ## Spec (what you're reviewing)
       {content of spec.md}

       ## Iteration Context
       This is iteration {n} of {max}.

       Your job: Find weaknesses before design does.
       Be the skeptic. Challenge assumptions. Find gaps.

       Return your assessment as JSON:
       {
         "approved": true/false,
         "issues": [{"severity": "blocker|warning|suggestion", "category": "...", "description": "...", "location": "...", "suggestion": "..."}],
         "summary": "..."
       }
   ```

c. **Parse response:** Extract the `approved` field from reviewer's JSON response.
   - If response is not valid JSON, ask reviewer to retry with correct format.

d. **Branch on result (strict threshold):**
   - **PASS:** `approved: true` AND zero issues with severity "blocker" or "warning"
   - **FAIL:** `approved: false` OR any issue has severity "blocker" or "warning"
   - If PASS → Proceed to Stage 2
   - If FAIL AND iteration < max:
     - Append iteration to `.review-history.md` with "Stage 1: Spec-Reviewer Review" marker
     - Increment iteration counter
     - Address all blocker AND warning issues by revising spec.md
     - Return to step 4b (always a NEW Task tool dispatch per iteration)
   - If FAIL AND iteration == max:
     - Note concerns in `.meta.json` reviewerNotes
     - Proceed to Stage 2 with warning

#### Stage 2: Phase-Reviewer Validation (Handoff Gate)

Phase-reviewer iteration budget: max 5 (independent of Stage 1).

Set `phase_iteration = 0`.

e. **Invoke phase-reviewer** (always a NEW Task tool dispatch per iteration):
   ```
   Task tool call:
     description: "Validate spec ready for design"
     subagent_type: iflow:phase-reviewer
     model: sonnet
     prompt: |
       Validate this spec is ready for an engineer to design against.

       ## PRD (original requirements)
       {content of prd.md, or "None - feature created without brainstorm"}

       ## Spec (what you're reviewing)
       {content of spec.md}

       ## Domain Reviewer Outcome
       - Reviewer: spec-reviewer
       - Result: {APPROVED at iteration {n}/{max} | FAILED at iteration cap ({max}/{max})}
       - Unresolved issues: {list of remaining blocker/warning descriptions, or "none"}

       ## Next Phase Expectations
       Design needs: All requirements listed, acceptance criteria defined,
       scope boundaries clear, no ambiguities.

       This is phase-review iteration {phase_iteration}/5.

       Return your assessment as JSON:
       {
         "approved": true/false,
         "issues": [{"severity": "blocker|warning|suggestion", "description": "...", "location": "...", "suggestion": "..."}],
         "summary": "..."
       }
   ```

f. **Branch on result (strict threshold):**
   - **PASS:** `approved: true` AND zero issues with severity "blocker" or "warning"
   - **FAIL:** `approved: false` OR any issue has severity "blocker" or "warning"
   - If PASS → Proceed to auto-commit
   - If FAIL AND phase_iteration < 5:
     - Append to `.review-history.md` with "Stage 2: Phase Review" marker
     - Increment phase_iteration
     - Address all blocker AND warning issues
     - Return to step e (new agent instance)
   - If FAIL AND phase_iteration == 5:
     - Store concerns in `.meta.json` phaseReview.reviewerNotes
     - Proceed to auto-commit with warning

g. **Complete phase:** Proceed to auto-commit, then update state.

### 4a. Capture Review Learnings (Automatic)

**Trigger:** Only execute if the review loop ran 2+ iterations (across Stage 1 and/or Stage 2 combined). If approved on first pass in both stages, skip — no review learnings to capture.

**Process:**
1. Read `.review-history.md` entries for THIS phase only (spec-reviewer and phase-reviewer entries)
2. Group issues by description similarity (same category, overlapping file patterns)
3. Identify issues that appeared in 2+ iterations — these are recurring patterns

**For each recurring issue, call `store_memory`:**
- `name`: derived from issue description (max 60 chars)
- `description`: issue description + the suggestion that resolved it
- `reasoning`: "Recurred across {n} review iterations in feature {id} specify phase"
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
- `name`: "Specify review cap: {brief issue category}"
- `description`: summary of unresolved issues that prevented approval
- `category`: "anti-patterns"
- `confidence`: "low"

**Fallback:** If `store_memory` MCP tool unavailable, use `semantic_memory.writer` CLI.

**Output:** `"Review learnings: {n} patterns captured from {m}-iteration review cycle"` (inline, no prompt)

### 4b. Auto-Commit and Update State

Follow `commitAndComplete("specify", ["spec.md"])` from the **workflow-transitions** skill.

**Review History Entry Format** (append to `.review-history.md`):
```markdown
## {Stage 1: Spec-Reviewer Review | Stage 2: Phase Review} - Iteration {n} - {ISO timestamp}

**Reviewer:** {spec-reviewer (skeptic) | phase-reviewer (gatekeeper)}
**Decision:** {Approved / Needs Revision}

**Issues:**
- [{severity}] [{category}] {description} (at: {location})
  Suggestion: {suggestion}

**Changes Made:**
{Summary of revisions made to address issues}

---
```

### 6. Completion Message

Output: "Specification complete."

```
AskUserQuestion:
  questions: [{
    "question": "Specification complete. Continue to next phase?",
    "header": "Next Step",
    "options": [
      {"label": "Continue to /iflow:design (Recommended)", "description": "Create architecture design"},
      {"label": "Review spec.md first", "description": "Inspect the spec before continuing"},
      {"label": "Fix and rerun reviews", "description": "Apply fixes then rerun Stage 1 + Stage 2 review cycle"}
    ],
    "multiSelect": false
  }]
```

If "Continue to /iflow:design (Recommended)": Invoke `/iflow:design`
If "Review spec.md first": Show "Spec at {path}/spec.md. Run /iflow:design when ready." → STOP
If "Fix and rerun reviews": Ask user what needs fixing (plain text via AskUserQuestion with free-text), apply the requested changes to spec.md, then return to Step 4 (Stage 1 spec-reviewer) with iteration counters reset to 0.
