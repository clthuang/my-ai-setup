---
description: Start or continue implementation of current feature
argument-hint: "[--feature=<id-slug>]"
---

Invoke the implementing skill for the current feature context.

Read docs/features/ to find active feature, then follow the workflow below.

## YOLO Mode Overrides

If `[YOLO_MODE]` is active:
- **Circuit breaker (5 iterations) — applies to Review Phase (Step 7) only, not Test Deepening (Step 6):** STOP execution and report failure to user.
  Do NOT force-approve. This is a safety boundary — autonomous operation should not
  merge code that fails review 5 times. Output:
  "YOLO MODE STOPPED: Implementation review failed after 5 iterations.
   Unresolved issues: {issue list}
   Resume with: /secretary continue"
- Completion prompt → skip AskUserQuestion, directly invoke `/iflow-dev:finish-feature` with `[YOLO_MODE]`

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

### 6. Test Deepening Phase

Dispatch test-deepener agent in two phases. Phase A generates spec-driven test outlines without implementation access. Phase B writes executable tests.

**Phase A — Generate test outlines from spec only:**
```
Task tool call:
  description: "Generate test outlines from spec"
  subagent_type: iflow-dev:test-deepener
  prompt: |
    PHASE A: Generate test outlines from specifications only.
    Do NOT read implementation files. Do NOT use Glob/Grep to find source code.
    You will receive implementation access in Phase B.

    Feature: {feature name from .meta.json slug}

    ## Spec (acceptance criteria — your primary test oracle)
    {content of spec.md}

    ## Design (error handling contracts, performance constraints)
    {content of design.md}

    ## Tasks (what was supposed to be built)
    {content of tasks.md}

    ## PRD Goals
    {Problem Statement + Goals sections from prd.md}

    Generate Given/When/Then test outlines for all applicable dimensions.
    Return as structured JSON with dimension, scenario name, given/when/then text,
    and derived_from reference to spec criterion.
```

**Phase A validation:** If `outlines` array is empty, log warning: "Test deepening Phase A returned no outlines — skipping test deepening" and proceed to Step 7.

**Files-changed union assembly:**

Build the union of files from Step 4 (implementation) and Step 5 (simplification):

```
# files from Step 4 (already in orchestrator context)
implementation_files = step_4_aggregate.files_changed

# files from Step 5 (already in orchestrator context)
simplification_files = [s.location.split(":")[0] for s in step_5_output.simplifications]

# union and deduplicate
files_changed = sorted(set(implementation_files + simplification_files))
```

**Fallback if context was compacted:** If the orchestrator no longer holds Step 4/5 data in context (due to conversation compaction), parse `implementation-log.md` directly. Each task section contains a "Files changed" or "files_changed" field with file paths. Match lines that look like file paths (contain `/` and end with a file extension). Validate extracted paths: reject any containing `..`, `%2e`, null bytes, or backslashes; reject paths starting with `/`; only accept relative paths within the project root. Step 5 paths are always a subset of Step 4 paths, so no coverage gap exists.

**Phase B — Write executable tests:**
```
Task tool call:
  description: "Write and verify deepened tests"
  subagent_type: iflow-dev:test-deepener
  prompt: |
    PHASE B: Write executable test code from these outlines.

    Feature: {feature name}

    ## Test Outlines (from Phase A)
    {Phase A JSON output — the full outlines array}

    ## Files Changed (implementation + simplification)
    {deduplicated file list}

    Step 1: Read existing test files for changed code to identify the test
    framework, assertion patterns, and file organization conventions. Match
    these exactly when writing new tests.

    Step 2: Skip scenarios already covered by existing TDD tests.

    Step 3: Write executable tests, run the suite, and report.
```

**Divergence control flow:**

After Phase B completes, check `spec_divergences` in the output:

- **If `spec_divergences` is empty:** Proceed to Step 7 (Review Phase).

- **If `spec_divergences` is non-empty AND YOLO mode OFF:**
  ```
  AskUserQuestion:
    questions: [{
      "question": "Test deepening found {n} spec divergences. How to proceed?",
      "header": "Spec Divergences",
      "options": [
        {"label": "Fix implementation", "description": "Dispatch implementer to fix code to match spec, then re-run Phase B"},
        {"label": "Accept implementation", "description": "Remove divergent tests and proceed to review"},
        {"label": "Review manually", "description": "Inspect divergences before deciding"}
      ],
      "multiSelect": false
    }]
  ```

  - **"Fix implementation":**
    1. Dispatch implementer agent with `spec_divergences` formatted as issues (spec_criterion as requirement, expected as target, actual as bug, failing_test as evidence). Include spec.md, design.md, and implementation files in context.
    2. Re-run Phase B only (Phase A outlines are unchanged since spec inputs don't change when implementation is fixed).
    3. Max 2 re-runs. If divergences persist after 2 cycles, escalate with AskUserQuestion offering only "Accept implementation" and "Review manually".

  - **"Accept implementation":**
    1. For each divergence in `spec_divergences`, delete the test function identified by `failing_test` from the file.
    2. After ALL deletions, re-run the test suite once to verify remaining tests pass.
    3. Proceed to Step 7.

  - **"Review manually":** Stop execution.

- **If `spec_divergences` is non-empty AND YOLO mode ON:**
  - If re-run count < 2: Auto-select "Fix implementation" (dispatch implementer, re-run Phase B only).
  - If re-run count >= 2: STOP execution and surface to user:
    "YOLO MODE STOPPED: Test deepening found persistent spec divergences after 2 fix cycles.
     Divergences: {divergence list}
     Resume with: /secretary continue"

**Error handling:** If Phase A or Phase B agent dispatch fails (tool error, timeout, or agent crash), log the error and proceed to Step 7. Test deepening is additive — failure should not block the review phase.

### 7. Review Phase (Automated Iteration Loop)

Maximum 5 iterations. Loop continues until ALL reviewers approve or cap is reached.

Execute review cycle with three reviewers:

**7a. Implementation Review (4-Level Validation):**
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

**7b. Code Quality Review:**
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

**7c. Security Review:**
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

**7d. Automated Iteration Logic:**

Collect results from all three reviewers (implementation, quality, security).

**Apply strict threshold to each reviewer result:**
- **PASS:** `approved: true` AND zero issues with severity "blocker" or "warning"
- **FAIL:** `approved: false` OR any issue has severity "blocker" or "warning"

IF all three PASS:
  → Mark phase completed
  → Proceed to step 8

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
    - "Force approve": Record unresolved issues in `.meta.json` reviewerNotes, proceed to step 8
    - "Pause and review manually": Stop execution, output file list for manual review
    - "Abandon changes": Stop execution, do NOT mark phase completed
  → Else: Loop back to step 7a

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

### 7e. Capture Review Learnings (Automatic)

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

### 8. Update State on Completion

Follow the state update step from `commitAndComplete("implement", [])` in the **workflow-transitions** skill. Implementation does not auto-commit artifacts (code is committed during implementation).

### 9. Completion Message

Output: "Implementation complete."

```
AskUserQuestion:
  questions: [{
    "question": "Implementation complete. Continue to next phase?",
    "header": "Next Step",
    "options": [
      {"label": "Continue to /iflow-dev:finish-feature (Recommended)", "description": "Complete the feature"},
      {"label": "Review implementation first", "description": "Inspect the code before finishing"},
      {"label": "Fix and rerun reviews", "description": "Apply fixes then rerun the 3-reviewer review cycle"}
    ],
    "multiSelect": false
  }]
```

If "Continue to /iflow-dev:finish-feature (Recommended)": Invoke `/iflow-dev:finish-feature`
If "Review implementation first": Show "Run /iflow-dev:finish-feature when ready." → STOP
If "Fix and rerun reviews": Ask user what needs fixing (plain text via AskUserQuestion with free-text), apply the requested changes to the implementation, then return to Step 7 (3-reviewer loop) with the iteration counter reset to 0.
