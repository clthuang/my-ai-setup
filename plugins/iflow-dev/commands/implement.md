---
description: Start or continue implementation of current feature
argument-hint: "[--feature=<id-slug>]"
---

Invoke the implementing skill for the current feature context.

Read docs/features/ to find active feature, then follow the workflow below.

## YOLO Mode Overrides

If `[YOLO_MODE]` is active:
- **Circuit breaker (5 iterations):** STOP execution and report failure to user.
  Do NOT force-approve. This is a safety boundary — autonomous operation should not
  merge code that fails review 5 times. Output:
  "YOLO MODE STOPPED: Implementation review failed after 5 iterations.
   Unresolved issues: {issue list}
   Resume with: /secretary continue"
- Completion prompt → skip AskUserQuestion, directly invoke `/iflow-dev:finish` with `[YOLO_MODE]`

## Workflow Integration

### 1-3. Validate, Branch Check, Partial Recovery, Mark Started

Follow `validateAndSetup("implement")` from the **workflow-transitions** skill.

**Hard prerequisite:** Before standard validation, validate spec.md using `validateArtifact(path, "spec.md")`. If validation fails:
```
BLOCKED: Valid spec.md required before implementation.

{Level 1}: spec.md not found. Run /iflow-dev:specify first.
{Level 2}: spec.md appears empty or stub. Run /iflow-dev:specify to complete it.
{Level 3}: spec.md missing markdown structure. Run /iflow-dev:specify to fix.
{Level 4}: spec.md missing required sections (Success Criteria or Acceptance Criteria). Run /iflow-dev:specify to add them.
```
Stop execution. Do not proceed.

**Hard prerequisite:** Additionally, validate tasks.md using `validateArtifact(path, "tasks.md")`. If validation fails:
```
BLOCKED: Valid tasks.md required before implementation.

{Level 1}: tasks.md not found. Run /iflow-dev:create-tasks first.
{Level 2}: tasks.md appears empty or stub. Run /iflow-dev:create-tasks to complete it.
{Level 3}: tasks.md missing markdown structure. Run /iflow-dev:create-tasks to fix.
{Level 4}: tasks.md missing required sections (Phase or Task). Run /iflow-dev:create-tasks to add them.
```
Stop execution. Do not proceed.

### 4. Implementation Phase

Execute the implementing skill which:
- Parses tasks.md for all task headings
- Dispatches implementer agent per task with scoped context
- Collects structured reports (files changed, decisions, deviations, concerns)
- Appends per-task entries to implementation-log.md
- Returns aggregate summary (files changed, completion status)

### 5. Code Simplification Phase

Dispatch code-simplifier agent:
```
Task tool call:
  description: "Simplify implementation"
  subagent_type: iflow-dev:code-simplifier
  prompt: |
    Review the implementation for unnecessary complexity.

    Feature: {feature name}

    ## Spec (acceptance criteria)
    {content of spec.md}

    ## Design (architecture to follow)
    {content of design.md}

    ## Files changed
    {list of files created/modified}

    Look for:
    - Unnecessary abstractions
    - Dead code
    - Over-engineering
    - Verbose patterns

    Return your assessment as JSON with simplifications array.
```

If simplifications found:
- Apply approved simplifications
- Verify tests still pass
- Return to main agent

### 6. Review Phase (Automated Iteration Loop)

Maximum 5 iterations. Loop continues until ALL reviewers approve or cap is reached.

Execute review cycle with three reviewers:

**6a. Implementation Review (4-Level Validation):**
```
Task tool call:
  description: "Review implementation against requirements chain"
  subagent_type: iflow-dev:implementation-reviewer
  prompt: |
    Validate implementation against full requirements chain with 4-level validation.

    ## PRD (original requirements)
    {content of prd.md or brainstorm file}

    ## Spec (acceptance criteria)
    {content of spec.md}

    ## Design (architecture to follow)
    {content of design.md}

    ## Plan (implementation plan)
    {content of plan.md}

    ## Tasks (what should be done)
    {content of tasks.md}

    ## Implementation files
    {list of files with code}

    Validate all 4 levels:
    - Level 1: Task completeness
    - Level 2: Spec compliance
    - Level 3: Design alignment
    - Level 4: PRD delivery

    Return JSON with approval status, level results, issues, and evidence.
```

**6b. Code Quality Review:**
```
Task tool call:
  description: "Review code quality"
  subagent_type: iflow-dev:code-quality-reviewer
  prompt: |
    Review implementation quality.

    ## PRD (original requirements)
    {content of prd.md or brainstorm file}

    ## Spec (acceptance criteria)
    {content of spec.md}

    ## Design (architecture to follow)
    {content of design.md}

    ## Plan (implementation plan)
    {content of plan.md}

    ## Tasks (what should be done)
    {content of tasks.md}

    ## Files changed
    {list of files}

    Check:
    - Readability
    - KISS principle
    - YAGNI principle
    - Formatting
    - Holistic flow

    Return assessment with approval status.
```

**6c. Security Review:**
```
Task tool call:
  description: "Review security"
  subagent_type: iflow-dev:security-reviewer
  prompt: |
    Review implementation for security vulnerabilities.

    ## PRD (original requirements)
    {content of prd.md or brainstorm file}

    ## Spec (acceptance criteria)
    {content of spec.md}

    ## Design (architecture to follow)
    {content of design.md}

    ## Plan (implementation plan)
    {content of plan.md}

    ## Tasks (what should be done)
    {content of tasks.md}

    ## Files changed
    {list of files}

    Check:
    - Input validation
    - Authentication/authorization
    - Data protection
    - OWASP top 10

    Return JSON with approval status and vulnerabilities.
```

**6d. Automated Iteration Logic:**

Collect results from all three reviewers (implementation, quality, security).

**Apply strict threshold to each reviewer result:**
- **PASS:** `approved: true` AND zero issues with severity "blocker" or "warning"
- **FAIL:** `approved: false` OR any issue has severity "blocker" or "warning"

IF all three PASS:
  → Mark phase completed
  → Proceed to step 7

ELSE (any issues found):
  → Append iteration to `.review-history.md`
  → Dispatch implementer agent to fix issues:
    ```
    Task tool call:
      description: "Fix review issues iteration {n}"
      subagent_type: iflow-dev:implementer
      prompt: |
        Fix the following review issues:

        ## PRD (original requirements)
        {content of prd.md or brainstorm file}

        ## Spec (acceptance criteria)
        {content of spec.md}

        ## Design (architecture to follow)
        {content of design.md}

        ## Plan (implementation plan)
        {content of plan.md}

        ## Tasks (what should be done)
        {content of tasks.md}

        ## Implementation files
        {list of files with code}

        ## Issues to fix
        {consolidated issue list from all reviewers}

        After fixing, return summary of changes made.
    ```
  → Increment iteration counter
  → If iteration >= 5 (circuit breaker):
    ```
    AskUserQuestion:
      questions: [{
        "question": "Review loop reached 5 iterations without full approval. How to proceed?",
        "header": "Circuit Breaker",
        "options": [
          {"label": "Force approve with warnings", "description": "Accept current state, log unresolved issues"},
          {"label": "Pause and review manually", "description": "Stop loop, inspect code yourself"},
          {"label": "Abandon changes", "description": "Discard implementation, return to planning"}
        ],
        "multiSelect": false
      }]
    ```
    - "Force approve": Record unresolved issues in `.meta.json` reviewerNotes, proceed to step 7
    - "Pause and review manually": Stop execution, output file list for manual review
    - "Abandon changes": Stop execution, do NOT mark phase completed
  → Else: Loop back to step 6a

**Review History Entry Format** (append to `.review-history.md`):
```markdown
## Iteration {n} - {ISO timestamp}

**Implementation Review:** {Approved / Issues found}
  - Level 1 (Tasks): {pass/fail}
  - Level 2 (Spec): {pass/fail}
  - Level 3 (Design): {pass/fail}
  - Level 4 (PRD): {pass/fail}
**Quality Review:** {Approved / Issues found}
**Security Review:** {Approved / Issues found}

**Issues:**
- [{severity}] [{level}] {reviewer}: {description} (at: {location})
  Suggestion: {suggestion}

**Changes Made:**
{Summary of revisions made to address issues}

---
```

### 6e. Capture Review Learnings (Automatic)

**Trigger:** Only execute if the review loop ran 2+ iterations. If all three reviewers approved on first pass, skip — no review learnings to capture.

**Process:**
1. Read `.review-history.md` entries for THIS phase only (implementation-reviewer, code-quality-reviewer, and security-reviewer entries)
2. Group issues by description similarity (same category, overlapping file patterns)
3. Identify issues that appeared in 2+ iterations — these are recurring patterns

**For each recurring issue, call `store_memory`:**
- `name`: derived from issue description (max 60 chars)
- `description`: issue description + the suggestion that resolved it
- `reasoning`: "Recurred across {n} review iterations in feature {id} implement phase"
- `category`: infer from issue type:
  - Security issues → `anti-patterns`
  - Quality/SOLID/naming → `heuristics`
  - Missing requirements → `anti-patterns`
  - Feasibility/complexity → `heuristics`
  - Scope/assumption issues → `heuristics`
- `references`: ["feature/{id}-{slug}"]
- `confidence`: "low"

**Budget:** Max 3 entries per review cycle to avoid noise.

**Circuit breaker capture:** If review loop hit max iterations (cap reached), also capture a single entry:
- `name`: "Implement review cap: {brief issue category}"
- `description`: summary of unresolved issues that prevented approval
- `category`: "anti-patterns"
- `confidence`: "low"

**Fallback:** If `store_memory` MCP tool unavailable, use `semantic_memory.writer` CLI.

**Output:** `"Review learnings: {n} patterns captured from {m}-iteration review cycle"` (inline, no prompt)

### 7. Update State on Completion

Follow the state update step from `commitAndComplete("implement", [])` in the **workflow-transitions** skill. Implementation does not auto-commit artifacts (code is committed during implementation).

### 8. Completion Message

Output: "Implementation complete."

```
AskUserQuestion:
  questions: [{
    "question": "Implementation complete. Continue to next phase?",
    "header": "Next Step",
    "options": [
      {"label": "Continue to /iflow-dev:finish (Recommended)", "description": "Complete the feature"},
      {"label": "Review implementation first", "description": "Inspect the code before finishing"},
      {"label": "Fix and rerun reviews", "description": "Apply fixes then rerun the 3-reviewer review cycle"}
    ],
    "multiSelect": false
  }]
```

If "Continue to /iflow-dev:finish (Recommended)": Invoke `/iflow-dev:finish`
If "Review implementation first": Show "Run /iflow-dev:finish when ready." → STOP
If "Fix and rerun reviews": Ask user what needs fixing (plain text via AskUserQuestion with free-text), apply the requested changes to the implementation, then return to Step 6 (3-reviewer loop) with the iteration counter reset to 0.
