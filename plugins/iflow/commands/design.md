---
description: Create architecture design for current feature
argument-hint: "[--feature=<id-slug>]"
---

Invoke the designing skill for the current feature context.

## Config Variables
Use these values from session context (injected at session start):
- `{iflow_artifacts_root}` — root directory for feature artifacts (default: `docs`)

Read {iflow_artifacts_root}/features/ to find active feature, then follow the workflow below.

## YOLO Mode Overrides

If `[YOLO_MODE]` is active:
- Stage 0 research findings prompt → auto "Proceed"
- Stage 0 partial recovery → auto "Resume"
- Completion prompt → skip AskUserQuestion, directly invoke `/iflow:create-plan` with `[YOLO_MODE]`

## Workflow Integration

### 1-3. Validate, Branch Check, Partial Recovery, Mark Started

Follow `validateAndSetup("design")` from the **workflow-transitions** skill.

**Design-specific partial recovery:** If partial design detected, also check `phases.design.stages` to identify which stage was in progress and offer resumption from that specific stage.

### 4. Execute 5-Stage Workflow

The design phase consists of 5 sequential stages:

```
Stage 0: RESEARCH ("Don't Reinvent the Wheel")
    ↓
Stage 1: ARCHITECTURE DESIGN
    ↓
Stage 2: INTERFACE DESIGN
    ↓
Stage 3: DESIGN REVIEW LOOP (design-reviewer, up to 5 iterations)
    ↓
Stage 4: HANDOFF REVIEW (phase-reviewer)
```

---

#### Stage 0: Research

**Purpose:** Gather prior art before designing to avoid reinventing the wheel.

a. **Mark stage started:**
   ```json
   "stages": {
     "research": { "started": "{ISO timestamp}" }
   }
   ```

b. **Dispatch parallel research agents** (2 agents, within `max_concurrent_agents` budget):
   ```
   Task tool call 1:
     description: "Explore codebase for patterns"
     subagent_type: iflow:codebase-explorer
     model: sonnet
     prompt: |
       Find existing patterns related to: {feature description from spec}

       Look for:
       - Similar implementations
       - Reusable components
       - Established conventions
       - Related utilities

       Return JSON: {"findings": [...], "locations": [...]}

   Task tool call 2:
     description: "Research external solutions"
     subagent_type: iflow:internet-researcher
     model: sonnet
     prompt: |
       Research existing solutions for: {feature description from spec}

       Look for:
       - Industry standard approaches
       - Library support
       - Common patterns
       - Best practices

       Return JSON: {"findings": [...], "sources": [...]}
   ```

c. **Present findings via AskUserQuestion:**
   ```
   AskUserQuestion:
     questions: [{
       "question": "Research found {n} patterns. How to proceed?",
       "header": "Research",
       "options": [
         {"label": "Review findings", "description": "See details before designing"},
         {"label": "Proceed", "description": "Continue to architecture with findings"},
         {"label": "Skip (domain expert)", "description": "Skip research, proceed directly"}
       ],
       "multiSelect": false
     }]
   ```

d. **Record results in design.md Prior Art section:**
   - If "Review findings": Display findings, then ask again (Proceed/Skip)
   - If "Proceed": Write findings to Prior Art Research section
   - If "Skip": Note "Research skipped by user" in Prior Art section

e. **Handle agent failures gracefully:**
   - If codebase-explorer fails: Note "Codebase search unavailable" in Prior Art section
   - If internet-researcher fails: Note "No external solutions found" in Prior Art section
   - If both fail: Proceed with empty Prior Art section, note "Research unavailable"

f. **Mark stage completed:**
   ```json
   "stages": {
     "research": { "started": "...", "completed": "{ISO timestamp}", "skipped": false }
   }
   ```

**Recovery from partial Stage 0:**
If `stages.research.started` exists but `stages.research.completed` is null:
```
AskUserQuestion:
  questions: [{
    "question": "Detected partial research. How to proceed?",
    "header": "Recovery",
    "options": [
      {"label": "Resume", "description": "Continue from where research stopped"},
      {"label": "Restart", "description": "Run research again from beginning"},
      {"label": "Skip", "description": "Proceed without research"}
    ],
    "multiSelect": false
  }]
```

---

#### Stage 1: Architecture Design

**Purpose:** Establish high-level structure, components, decisions, and risks.

a. **Mark stage started:**
   ```json
   "stages": {
     "architecture": { "started": "{ISO timestamp}" }
   }
   ```

b. **Invoke designing skill with stage=architecture:**
   - Produce: Architecture Overview, Components, Technical Decisions, Risks
   - Write to design.md

c. **Mark stage completed:**
   ```json
   "stages": {
     "architecture": { "started": "...", "completed": "{ISO timestamp}" }
   }
   ```

d. **No review at this stage** - validated holistically in Stage 3.

---

#### Stage 2: Interface Design

**Purpose:** Define precise contracts between components.

a. **Mark stage started:**
   ```json
   "stages": {
     "interface": { "started": "{ISO timestamp}" }
   }
   ```

b. **Invoke designing skill with stage=interface:**
   - Read existing design.md for component definitions
   - Produce: Interfaces section with detailed contracts
   - Update design.md

c. **Mark stage completed:**
   ```json
   "stages": {
     "interface": { "started": "...", "completed": "{ISO timestamp}" }
   }
   ```

d. **No review at this stage** - validated holistically in Stage 3.

---

#### Stage 3: Design Review Loop

**Purpose:** Challenge assumptions, find gaps, ensure robustness.

Max iterations: 5.

a. **Mark stage started:**
   ```json
   "stages": {
     "designReview": { "started": "{ISO timestamp}", "iterations": 0, "reviewerNotes": [] }
   }
   ```

b. **Invoke design-reviewer:** Use the Task tool to spawn design-reviewer (the skeptic):
   ```
   Task tool call:
     description: "Review design quality"
     subagent_type: iflow:design-reviewer
     model: opus
     prompt: |
       Review this design for robustness and completeness.

       ## PRD (original requirements)
       {content of prd.md, or "None - feature created without brainstorm"}

       ## Spec (what we must satisfy)
       {content of spec.md}

       ## Design (what we're reviewing)
       {content of design.md}

       ## Iteration Context
       This is iteration {n} of {max}.

       Your job: Find weaknesses before implementation does.
       Be the skeptic. Challenge assumptions. Find gaps.

       Return your assessment as JSON:
       {
         "approved": true/false,
         "issues": [{
           "severity": "blocker|warning|suggestion",
           "category": "completeness|consistency|feasibility|assumptions|complexity",
           "description": "...",
           "location": "...",
           "suggestion": "..."
         }],
         "summary": "..."
       }
   ```

c. **Parse response:** Extract the `approved` field from reviewer's JSON response.
   - If response is not valid JSON, ask reviewer to retry with correct format.

d. **Branch on result (strict threshold):**
   - **PASS:** `approved: true` AND zero issues with severity "blocker" or "warning"
   - **FAIL:** `approved: false` OR any issue has severity "blocker" or "warning"
   - If PASS → Proceed to Stage 4
   - If FAIL AND iteration < max:
     - Append iteration to `.review-history.md` using format below
     - Increment iteration counter in state
     - Address all blocker AND warning issues by revising design.md
     - Return to step b (always a NEW Task tool dispatch per iteration)
   - If FAIL AND iteration == max:
     - Store unresolved concerns in `stages.designReview.reviewerNotes`
     - Proceed to Stage 4 with warning

e. **Mark stage completed:**
   ```json
   "stages": {
     "designReview": { "started": "...", "completed": "{ISO timestamp}", "iterations": {count}, "reviewerNotes": [...] }
   }
   ```

**Review History Entry Format** (append to `.review-history.md`):
```markdown
## Design Review - Iteration {n} - {ISO timestamp}

**Reviewer:** design-reviewer (skeptic)
**Decision:** {Approved / Needs Revision}

**Issues:**
- [{severity}] [{category}] {description} (at: {location})
  Challenge: {challenge}

**Changes Made:**
{Summary of revisions made to address issues}

---
```

---

#### Stage 4: Handoff Review

**Purpose:** Ensure plan phase has everything it needs.

Phase-reviewer iteration budget: max 5 (independent of Stage 3).

Set `phase_iteration = 0`.

a. **Mark stage started:**
   ```json
   "stages": {
     "handoffReview": { "started": "{ISO timestamp}", "iterations": 0 }
   }
   ```

b. **Invoke phase-reviewer** (always a NEW Task tool dispatch per iteration):
   ```
   Task tool call:
     description: "Review design for phase sufficiency"
     subagent_type: iflow:phase-reviewer
     model: sonnet
     prompt: |
       Validate this design is ready for implementation planning.

       ## PRD (original requirements)
       {content of prd.md, or "None - feature created without brainstorm"}

       ## Spec (requirements)
       {content of spec.md}

       ## Design (what you're reviewing)
       {content of design.md}

       ## Domain Reviewer Outcome
       - Reviewer: design-reviewer
       - Result: {APPROVED at iteration {n}/{max} | FAILED at iteration cap ({max}/{max})}
       - Unresolved issues: {list of remaining blocker/warning descriptions, or "none"}

       ## Next Phase Expectations
       Plan needs: Components defined, interfaces specified,
       dependencies identified, risks noted.

       This is phase-review iteration {phase_iteration}/5.

       Return your assessment as JSON:
       {
         "approved": true/false,
         "issues": [{"severity": "blocker|warning|suggestion", "description": "...", "location": "...", "suggestion": "..."}],
         "summary": "..."
       }
   ```

c. **Branch on result (strict threshold):**
   - **PASS:** `approved: true` AND zero issues with severity "blocker" or "warning"
   - **FAIL:** `approved: false` OR any issue has severity "blocker" or "warning"
   - If PASS → Proceed to auto-commit
   - If FAIL AND phase_iteration < 5:
     - Append to `.review-history.md` with "Stage 4: Handoff Review" marker
     - Increment phase_iteration
     - Address all blocker AND warning issues by revising design.md
     - Return to step b (new agent instance)
   - If FAIL AND phase_iteration == 5:
     - Store concerns in `stages.handoffReview.reviewerNotes`
     - Proceed to auto-commit with warning

d. **Mark stage completed:**
   ```json
   "stages": {
     "handoffReview": { "started": "...", "completed": "{ISO timestamp}", "iterations": {phase_iteration}, "approved": true/false, "reviewerNotes": [...] }
   }
   ```

e. **Append to review history:**
   ```markdown
   ## Handoff Review - Iteration {n} - {ISO timestamp}

   **Reviewer:** phase-reviewer (gatekeeper)
   **Decision:** {Approved / Needs Revision}

   **Issues:**
   - [{severity}] {description} (at: {location})

   **Changes Made:**
   {Summary of revisions made to address issues}

   ---
   ```

---

### 4b. Capture Review Learnings (Automatic)

**Trigger:** Only execute if the review loop ran 2+ iterations (across Stage 3 and/or Stage 4 combined). If approved on first pass in both stages, skip — no review learnings to capture.

**Process:**
1. Read `.review-history.md` entries for THIS phase only (design-reviewer and phase-reviewer entries)
2. Group issues by description similarity (same category, overlapping file patterns)
3. Identify issues that appeared in 2+ iterations — these are recurring patterns

**For each recurring issue, call `store_memory`:**
- `name`: derived from issue description (max 60 chars)
- `description`: issue description + the suggestion that resolved it
- `reasoning`: "Recurred across {n} review iterations in feature {id} design phase"
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
- `name`: "Design review cap: {brief issue category}"
- `description`: summary of unresolved issues that prevented approval
- `category`: "anti-patterns"
- `confidence`: "low"

**Fallback:** If `store_memory` MCP tool unavailable, use `semantic_memory.writer` CLI.

**Output:** `"Review learnings: {n} patterns captured from {m}-iteration review cycle"` (inline, no prompt)

### 4c. Auto-Commit and Update State

Follow `commitAndComplete("design", ["design.md"])` from the **workflow-transitions** skill.

Design additionally records stage-level tracking in `.meta.json` phases.design.stages (architecture, interface, designReview, handoffReview).

### 6. Completion Message

Output: "Design complete."

```
AskUserQuestion:
  questions: [{
    "question": "Design complete. Continue to next phase?",
    "header": "Next Step",
    "options": [
      {"label": "Continue to /iflow:create-plan (Recommended)", "description": "Creates plan.md with dependency graphs and workflow tracking"},
      {"label": "Review design.md first", "description": "Inspect the design before continuing"},
      {"label": "Fix and rerun reviews", "description": "Apply fixes then rerun Stage 3 + Stage 4 review cycle"}
    ],
    "multiSelect": false
  }]
```

If "Continue to /iflow:create-plan (Recommended)": Invoke `/iflow:create-plan`
If "Review design.md first": Show "Design at {path}/design.md. Run /iflow:create-plan when ready." → STOP
If "Fix and rerun reviews": Ask user what needs fixing (plain text via AskUserQuestion with free-text), apply the requested changes to design.md, then return to Stage 3 (design-reviewer) with iteration counters reset to 0.
