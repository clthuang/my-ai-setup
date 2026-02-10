---
description: Create architecture design for current feature
argument-hint: "[--feature=<id-slug>]"
---

Invoke the designing skill for the current feature context.

Read docs/features/ to find active feature, then follow the workflow below.

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
Stage 3: DESIGN REVIEW LOOP (design-reviewer, 1-3 iterations)
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

b. **Dispatch parallel research agents:**
   ```
   Task tool call 1:
     description: "Explore codebase for patterns"
     subagent_type: iflow:codebase-explorer
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

Get max iterations from mode: Standard=1, Full=3.

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

d. **Branch on result:**
   - If `approved: true` → Proceed to Stage 4
   - If `approved: false` AND iteration < max:
     - Append iteration to `.review-history.md` using format below
     - Increment iteration counter in state
     - Address the issues by revising design.md
     - Return to step b
   - If `approved: false` AND iteration == max:
     - Store unresolved concerns in `stages.designReview.reviewerNotes`
     - Proceed to Stage 4

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

a. **Mark stage started:**
   ```json
   "stages": {
     "handoffReview": { "started": "{ISO timestamp}" }
   }
   ```

b. **Invoke phase-reviewer:** Use the Task tool to spawn phase-reviewer (the gatekeeper):
   ```
   Task tool call:
     description: "Review design for phase sufficiency"
     subagent_type: iflow:phase-reviewer
     prompt: |
       Validate this design is ready for implementation planning.

       ## PRD (original requirements)
       {content of prd.md, or "None - feature created without brainstorm"}

       ## Spec (requirements)
       {content of spec.md}

       ## Design (what you're reviewing)
       {content of design.md}

       ## Next Phase Expectations
       Plan needs: Components defined, interfaces specified,
       dependencies identified, risks noted.

       Return your assessment as JSON:
       {
         "approved": true/false,
         "issues": [{"severity": "blocker|warning|suggestion", "description": "...", "location": "...", "suggestion": "..."}],
         "summary": "..."
       }
   ```

c. **Single pass - no loop.** The design-reviewer already validated design quality.

d. **Record result:**
   - If `approved: false`: Store concerns in `stages.handoffReview.reviewerNotes`
   - Note concerns but do NOT block (design-reviewer already validated)

e. **Mark stage completed:**
   ```json
   "stages": {
     "handoffReview": { "started": "...", "completed": "{ISO timestamp}", "approved": true/false, "reviewerNotes": [...] }
   }
   ```

f. **Append to review history:**
   ```markdown
   ## Handoff Review - {ISO timestamp}

   **Reviewer:** phase-reviewer (gatekeeper)
   **Decision:** {Approved / Concerns Noted}

   **Issues:**
   - [{severity}] {description} (at: {location})

   ---
   ```

---

### 4c. Auto-Commit and Update State

Follow `commitAndComplete("design", ["design.md"])` from the **workflow-transitions** skill.

Design additionally records stage-level tracking in `.meta.json` phases.design.stages (architecture, interface, designReview, handoffReview).

### 6. Completion Message

"Design complete. Saved to design.md."

Present planning options via AskUserQuestion:

```
AskUserQuestion:
  questions: [{
    "question": "How would you like to create your implementation plan?",
    "header": "Planning",
    "options": [
      {"label": "iflow create-plan (Recommended)", "description": "Creates plan.md with dependency graphs and workflow tracking"},
      {"label": "Claude Code Plan Mode", "description": "Read-only analysis mode with approval workflow (Shift+Tab)"}
    ],
    "multiSelect": false
  }]
```

**If Option 1 (Claude Code Plan Mode):**
- Inform: "To enter plan mode:"
- Show instructions:
  ```
  1. Press Shift+Tab until you see "⏸ plan mode on" indicator
  2. Provide: "Create implementation plan based on docs/features/{id}-{slug}/design.md. Output to docs/features/{id}-{slug}/plan.md"
  3. Refine the plan interactively
  4. Press Ctrl+G to edit plan in your editor
  5. Say "proceed with the plan" when ready
  ```
- Note: "Phase tracking won't be updated until you run /iflow:create-tasks"
- Do NOT auto-continue (user switches modes manually)

**If Option 2 (iflow /iflow:create-plan):**
- Inform: "Continuing with /iflow:create-plan..."
- Auto-invoke `/iflow:create-plan`
