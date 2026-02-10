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

Get max iterations from mode: Standard=1, Full=3.

#### Stage 1: Spec-Reviewer Review (Quality Gate)

a. **Produce artifact:** Follow the specifying skill to create/revise spec.md

b. **Invoke spec-reviewer:** Use the Task tool to spawn spec-reviewer (the skeptic):
   ```
   Task tool call:
     description: "Skeptical review of spec quality"
     subagent_type: iflow:spec-reviewer
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

d. **Branch on result:**
   - If `approved: true` → Proceed to Stage 2
   - If `approved: false` AND iteration < max:
     - Append iteration to `.review-history.md` with "Stage 1: Spec-Reviewer Review" marker
     - Increment iteration counter
     - Address the issues by revising spec.md
     - Return to step 4b
   - If `approved: false` AND iteration == max:
     - Note concerns in `.meta.json` reviewerNotes
     - Proceed to Stage 2 with warning

#### Stage 2: Phase-Reviewer Validation (Handoff Gate)

e. **Invoke phase-reviewer:** Use the Task tool to spawn phase-reviewer (the gatekeeper):
   ```
   Task tool call:
     description: "Validate spec ready for design"
     subagent_type: iflow:phase-reviewer
     prompt: |
       Validate this spec is ready for an engineer to design against.

       ## PRD (original requirements)
       {content of prd.md, or "None - feature created without brainstorm"}

       ## Spec (what you're reviewing)
       {content of spec.md}

       ## Next Phase Expectations
       Design needs: All requirements listed, acceptance criteria defined,
       scope boundaries clear, no ambiguities.

       Return your assessment as JSON:
       {
         "approved": true/false,
         "issues": [{"severity": "blocker|warning|suggestion", "description": "...", "location": "...", "suggestion": "..."}],
         "summary": "..."
       }
   ```

f. **Single pass - no loop.** The spec-reviewer already validated spec quality.

g. **Record result:**
   - If `approved: false`: Store concerns in `.meta.json` phaseReview.reviewerNotes
   - Note concerns but do NOT block (spec-reviewer already validated)

h. **Complete phase:** Proceed to auto-commit, then update state.

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
    "question": "Ready for the next phase?",
    "header": "Next Step",
    "options": [
      {"label": "Continue to /design", "description": "Create architecture design"},
      {"label": "Stop here", "description": "End session"}
    ],
    "multiSelect": false
  }]
```

If "Continue to /design": Invoke `/iflow:design`
If "Stop here": STOP
