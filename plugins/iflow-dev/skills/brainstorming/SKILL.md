---
name: brainstorming
description: Guides a 6-stage process producing evidence-backed PRDs. Use when the user says 'brainstorm this idea', 'explore options for', 'start ideation', or 'create a PRD'.
---

# Brainstorming Phase

Guide divergent thinking through a structured 6-stage process that produces a PRD.

## YOLO Mode Overrides

If `[YOLO_MODE]` is active in the execution context:

- **Stage 1 (CLARIFY):** Skip Q&A. Infer all 5 required items from the user's description.
  Use reasonable defaults for anything not inferable. Do NOT ask any questions.
- **Step 6 (Problem Type):** Auto-select "Product/Feature"
- **Step 9 (Domain):** Auto-select "None"
- **Stages 2-5:** Run normally (research, drafting, and reviews still execute for quality)
- **Stage 6 (Decision):** Auto-select "Promote to Feature" regardless of variant
  (project-recommended, non-project, or blocked — always choose feature, not project)
- **Mode selection:** Auto-select "Standard"
- **Context propagation:** When invoking create-feature, include `[YOLO_MODE]` in args

These overrides take precedence over the PROHIBITED section for YOLO mode only.

## Getting Started

### 1. Create Scratch File

- Get topic from user argument or ask: "What would you like to brainstorm?"
- Generate slug from topic:
  - Lowercase
  - Replace spaces/special chars with hyphens
  - Max 30 characters
  - Trim trailing hyphens
  - If empty, use "untitled"
- Create file: `docs/brainstorms/YYYYMMDD-HHMMSS-{slug}.prd.md`
  - Example: `docs/brainstorms/20260129-143052-api-caching.prd.md`

### 2. Run 6-Stage Process

Follow the Process below, writing content to the PRD file as you go.

## Process

The brainstorm follows 6 stages in sequence:

```
Stage 1: CLARIFY → Stage 2: RESEARCH → Stage 3: DRAFT PRD
                                                    ↓
                                        Stage 4: CRITICAL REVIEW AND CORRECTION
                                                    (prd-reviewer + auto-correct loop, max 3)
                                                    ↓
                                        Stage 5: READINESS CHECK
                                                    (brainstorm-reviewer + auto-correct loop, max 3)
                                                    ↓
                                        Stage 6: USER DECISION
```

---
### Stage 1: CLARIFY

**Goal:** Resolve ambiguities through Q&A before research begins.

**Rules:**
- Ask ONE question at a time
- Use AskUserQuestion with multiple choice options when possible
- Apply YAGNI: challenge "nice to have" features

**Required information to gather:**
1. Problem being solved
2. Target user/audience
3. Success criteria
4. Known constraints
5. Approaches already considered

**Exit condition:** User confirms understanding is correct, OR you have answers to all 5 required items.

**After exit condition is satisfied, always run Steps 6-8 before proceeding to Stage 2:**

#### Step 6: Problem Type Classification
Present problem type options via AskUserQuestion:
```
AskUserQuestion:
  questions: [{
    "question": "What type of problem is this?",
    "header": "Problem Type",
    "options": [
      {"label": "Product/Feature", "description": "User-facing product or feature design"},
      {"label": "Technical/Architecture", "description": "System design, infrastructure, or technical debt"},
      {"label": "Financial/Business", "description": "Business model, pricing, or financial analysis"},
      {"label": "Research/Scientific", "description": "Hypothesis-driven investigation or experiment"},
      {"label": "Creative/Design", "description": "Visual, UX, or creative exploration"},
      {"label": "Skip", "description": "No framework — proceed with standard brainstorm"}
    ],
    "multiSelect": false
  }]
```

(User sees 7 options: 6 above + built-in "Other" for free text.)

#### Step 7: Optional Framework Loading
**If user selected a named type (not "Skip"):**
1. Derive sibling skill path: replace `skills/brainstorming` in Base directory with `skills/structured-problem-solving`
2. Read `{derived path}/SKILL.md` via Read tool
3. If file not found: warn "Structured problem-solving skill not found, skipping framework" → skip to Step 8
4. Read reference files as directed by SKILL.md
5. Apply SCQA framing to the problem
6. Apply type-specific decomposition (or generic issue tree for "Other")
7. Generate inline Mermaid mind map from decomposition
8. Write `## Structured Analysis` section to PRD (between Research Summary and Review History)

**If user selected "Other" (free text):**
- Apply SCQA framing (universal) + generic issue tree decomposition
- Store custom type string as-is

**If "Skip":** Set type to "none", skip Step 7 body entirely.

**Loop-back behavior:** If `## Structured Analysis` already exists in the PRD (from a previous Stage 6 → Stage 1 loop), delete it entirely before re-running Steps 6-8. Do NOT duplicate.

#### Step 8: Store Problem Type
- Add `- Problem Type: {type}` to PRD Status section (or `none` if skipped)

#### Step 9: Domain Selection

**Domain-to-skill mapping:**

| Label | Skill Dir | Analysis Heading |
|-------|-----------|------------------|
| Game Design | game-design | Game Design Analysis |
| Crypto/Web3 | crypto-analysis | Crypto Analysis |

Present domain options via AskUserQuestion:
```
AskUserQuestion:
  questions: [{
    "question": "Does this concept have a specific domain?",
    "header": "Domain",
    "options": [
      {"label": "Game Design", "description": "Apply game design frameworks (core loop, engagement, aesthetics, viability)"},
      {"label": "Crypto/Web3", "description": "Apply crypto analysis frameworks (protocol, tokenomics, market, risk)"},
      {"label": "None", "description": "No domain-specific analysis"}
    ],
    "multiSelect": false
  }]
```
If "None": skip Step 10, proceed to Stage 2.

#### Step 10: Domain Loading
1. Look up user's selection in the domain-to-skill mapping table (Step 9) to get **Skill Dir** and **Analysis Heading**
2. Derive sibling skill path: replace `skills/brainstorming` in Base directory with `skills/{Skill Dir}`
3. Read `{derived path}/SKILL.md` via Read tool
4. If file not found: warn "{Skill Dir} skill not found, skipping domain enrichment" → skip to Stage 2
5. Execute the domain skill inline (read reference files, apply frameworks to concept)
6. **Two-phase write:** Hold analysis in memory — do NOT write to PRD yet. Stage 3 writes it during PRD drafting.
7. Store domain review criteria (from skill output) for Stage 6 dispatch
8. Store `domain: {Skill Dir}` context for Stage 2 query enhancement

**Loop-back behavior:** If `## {Analysis Heading}` already exists in the PRD (from a previous Stage 6 → Stage 1 loop), delete it entirely, clear domain context, and re-prompt Step 9.

---
### Stage 2: RESEARCH

**Goal:** Gather evidence from 3 sources in parallel.

**Action:** Dispatch 3 Task tool calls in a single response:

1. **Internet research:**
   - Tool: `Task`
   - subagent_type: `iflow-dev:internet-researcher`
   - prompt: Query about the topic with context
   - **If a domain is active:** Append the domain skill's `## Stage 2 Research Context` prompt lines to the internet-researcher dispatch

2. **Codebase exploration:**
   - Tool: `Task`
   - subagent_type: `iflow-dev:codebase-explorer`
   - prompt: Query about existing patterns/constraints

3. **Skills search:**
   - Tool: `Task`
   - subagent_type: `iflow-dev:skill-searcher`
   - prompt: Query about related capabilities

**Collect results:** Each agent returns JSON with `findings` array and `source` references.

**Fallback:** If an agent fails, note warning and proceed with available results.

**Exit condition:** All 3 agents have returned (success or failure).

---
### Stage 3: DRAFT PRD

**Goal:** Generate a complete PRD document with evidence citations.

**Action:** Write PRD to file using the PRD Output Format section below.

**Citation requirements:** Every claim must have one of:
- `— Evidence: {URL}` (from internet research)
- `— Evidence: {file:line}` (from codebase)
- `— Evidence: User input` (from Stage 1)
- `— Assumption: needs verification` (unverified)

**Exit condition:** PRD file written with all sections populated.

---
### Stage 4: CRITICAL REVIEW AND CORRECTION

**Goal:** Challenge PRD quality and auto-correct issues in a review-correct loop (max 3 iterations).

Set `review_iteration = 0`.

**a. Dispatch prd-reviewer** (always a NEW Task tool instance per iteration):
- Tool: `Task`
- subagent_type: `iflow-dev:prd-reviewer`
- prompt: Full PRD content + request for JSON response + "This is review iteration {review_iteration}/3"

**Expected response:**
```json
{ "approved": true/false, "issues": [...], "summary": "..." }
```

**b. Apply strict threshold:**
- **PASS:** `approved: true` AND zero issues with severity "blocker" or "warning"
- **FAIL:** `approved: false` OR any issue has severity "blocker" or "warning"

**c. Branch on result:**
- If PASS → Proceed to Stage 5
- If FAIL AND review_iteration < 3:
  - Auto-correct: For each issue with severity "blocker" or "warning":
    - If has `suggested_fix`: Apply the fix to PRD content
    - Record: `Changed: {what} — Reason: {issue description}`
  - For "suggestion" severity: Consider but don't require action
  - Update PRD file with all corrections
  - Add to Review History section:
    ```markdown
    ### Review {review_iteration} ({date})
    **Findings:**
    - [{severity}] {description} (at: {location})

    **Corrections Applied:**
    - {what changed} — Reason: {reference to finding}
    ```
  - Increment review_iteration
  - Return to step a (new prd-reviewer instance verifies corrections)
- If FAIL AND review_iteration == 3:
  - Record unresolved issues in Review History
  - Proceed to Stage 5 with warning

**Fallback:** If reviewer unavailable on any iteration, show warning and proceed to Stage 5 with empty issues array.

**Exit condition:** PASS achieved or 3 iterations exhausted.

---
### Stage 5: READINESS CHECK

**Goal:** Validate brainstorm is ready for feature promotion (quality gate with auto-correction loop, max 3 iterations).

Set `readiness_iteration = 0`.

**a. Dispatch brainstorm-reviewer** (always a NEW Task tool instance per iteration):
- Tool: `Task`
- subagent_type: `iflow-dev:brainstorm-reviewer`
- prompt: |
    Review this brainstorm for promotion readiness.

    ## PRD Content
    {read PRD file and paste full markdown content here}

    ## Context
    Problem Type: {type from Step 8, or "none" if skipped/absent}
    {If domain context exists, add:}
    Domain: {stored domain name from Step 10}
    Domain Review Criteria:
    {stored criteria list from Step 10}

    This is readiness-check iteration {readiness_iteration}/3.

    Return your assessment as JSON:
    { "approved": true/false, "issues": [...], "summary": "..." }

**Expected response:**
```json
{ "approved": true/false, "issues": [...], "summary": "..." }
```

**b. Apply strict threshold:**
- **PASS:** `approved: true` AND zero issues with severity "blocker" or "warning"
- **FAIL:** `approved: false` OR any issue has severity "blocker" or "warning"

**c. Branch on result:**
- If PASS → Store `approved: true`, proceed to Stage 6
- If FAIL AND readiness_iteration < 3:
  - Auto-correct PRD to address all blocker AND warning issues
  - Record corrections in Review History
  - Increment readiness_iteration
  - Return to step a (new brainstorm-reviewer instance verifies)
- If FAIL AND readiness_iteration == 3:
  - Store unresolved issues
  - Proceed to Stage 6 with BLOCKED status (user must decide)

**Fallback:** If reviewer unavailable, show warning and proceed with `approved: unknown`.

**Exit condition:** PASS achieved, or 3 iterations exhausted (BLOCKED).

---
### Stage 6: USER DECISION

**Goal:** Present readiness status and let user decide next action.

**Step 1: Display readiness status**
- If `approved: true` with no blockers: Output "Readiness check: PASSED"
- If `approved: true` with warnings: Output "Readiness check: PASSED ({n} warnings)" + list warnings
- If `approved: false`: Output "Readiness check: BLOCKED ({n} issues)" + list all issues
- If `approved: unknown`: Output "Readiness check: SKIPPED (reviewer unavailable)"

**Step 1.5: Scale Detection (inline, before presenting options)**

Analyze the PRD content against 6 closed signals:

1. **Multiple entity types** — 3+ distinct data entities with separate CRUD lifecycles
2. **Multiple functional areas** — 3+ distinct functional capabilities
3. **Multiple API surfaces** — 2+ API types or 3+ distinct endpoint groups
4. **Cross-cutting concerns** — Capabilities spanning multiple functional areas
5. **Multiple UI sections** — 3+ distinct user-facing views/pages/screens
6. **External integrations** — 2+ external service integrations

Count matches. Store as `scale_signal_count`.
- If `scale_signal_count >= 3`: set `project_recommended = true`
- Otherwise: set `project_recommended = false`

**Step 2: Present options based on status**
If PASSED or SKIPPED AND `project_recommended == true`:
```
AskUserQuestion:
  questions: [{
    "question": "PRD complete ({scale_signal_count}/6 project-scale signals detected). What would you like to do?",
    "header": "Decision",
    "options": [
      {"label": "Promote to Project (Recommended)", "description": "Create project with AI-driven decomposition into features"},
      {"label": "Promote to Feature", "description": "Create single feature and continue workflow"},
      {"label": "Refine Further", "description": "Loop back to clarify and improve"},
      {"label": "Save and Exit", "description": "Keep PRD, end session"}
    ],
    "multiSelect": false
  }]
```

If PASSED or SKIPPED AND `project_recommended == false`:
```
AskUserQuestion:
  questions: [{
    "question": "PRD complete. What would you like to do?",
    "header": "Decision",
    "options": [
      {"label": "Promote to Feature", "description": "Create feature and continue workflow"},
      {"label": "Refine Further", "description": "Loop back to clarify and improve"},
      {"label": "Save and Exit", "description": "Keep PRD, end session"}
    ],
    "multiSelect": false
  }]
```

If BLOCKED:
```
AskUserQuestion:
  questions: [{
    "question": "PRD has blockers. What would you like to do?",
    "header": "Decision",
    "options": [
      {"label": "Address Issues", "description": "Auto-correction failed after 3 attempts. Loop back to clarify and fix manually."},
      {"label": "Promote Anyway", "description": "Create feature despite blockers"},
      {"label": "Save and Exit", "description": "Keep PRD, end session"}
    ],
    "multiSelect": false
  }]
```

**Step 3: Handle response**

| Response | Action |
|----------|--------|
| Promote to Project | Skip mode prompt → Invoke `/iflow-dev:create-project --prd={current-prd-path}` → STOP |
| Promote to Feature / Promote Anyway | Ask for mode → Invoke `/iflow-dev:create-feature --prd={current-prd-path}` → STOP |
| Refine Further / Address Issues | Loop back to Stage 1 with issue context |
| Save and Exit | Output "PRD saved to {filepath}." → STOP |

**Mode prompt bypass:** "Promote to Project" skips the mode selection below. Projects have no mode — modes are per-feature, set during planned→active transition when a user starts working on a decomposed feature.

**Mode selection (only for "Promote to Feature" / "Promote Anyway"):**
```
AskUserQuestion:
  questions: [{
    "question": "Which workflow mode?",
    "header": "Mode",
    "options": [
      {"label": "Standard", "description": "All phases, optional verification"},
      {"label": "Full", "description": "All phases, required verification"}
    ],
    "multiSelect": false
  }]
```

---
## PRD Output Format

Write PRD using template from [references/prd-template.md](references/prd-template.md).

---
## Error Handling

- **WebSearch Unavailable:** Skip internet research with warning, proceed with codebase and skills research only
- **Agent Unavailable:** Show warning "{agent} unavailable, proceeding without", continue with available agents
- **All Research Fails:** Proceed with user input only, mark all claims as "Assumption: needs verification"
- **PRD Reviewer Unavailable:** Show warning, proceed to Stage 5 with empty issues array
- **Brainstorm Reviewer Unavailable:** Show warning, proceed directly to Stage 6 with `approved: unknown`

---
## Completion
After Stage 6:
- If "Promote to Project": Invoke `/iflow-dev:create-project --prd={prd-file-path}` directly (no mode prompt)
- If "Promote to Feature": Ask for workflow mode (Standard/Full), then invoke `/iflow-dev:create-feature --prd={prd-file-path}`

---
## PROHIBITED Actions
When executing the brainstorming skill, you MUST NOT:
- Proceed to /iflow-dev:specify, /iflow-dev:design, /iflow-dev:create-plan, or /iflow-dev:implement
- Write any implementation code
- Create feature folders directly (use /iflow-dev:create-feature)
- Continue with any action after user says "Save and Exit"
- Skip the research stage (Stage 2)
- Skip the critical review stage (Stage 4)
- Skip the readiness check stage (Stage 5)
- Skip the AskUserQuestion decision gate (Stage 6)
