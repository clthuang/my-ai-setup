---
description: Start or continue implementation of current feature
---

Invoke the implementing skill for the current feature context.

Read docs/features/ to find active feature, then follow the workflow below.

## Workflow Integration

### 1. Validate Transition (HARD PREREQUISITE)

Before executing, check prerequisites using workflow-state skill:
- Read current `.meta.json` state
- Validate spec.md using `validateArtifact(path, "spec.md")`

**HARD BLOCK:** If spec.md validation fails:
```
❌ BLOCKED: Valid spec.md required before implementation.

{Level 1}: spec.md not found. Run /iflow-dev:specify first.
{Level 2}: spec.md appears empty or stub. Run /iflow-dev:specify to complete it.
{Level 3}: spec.md missing markdown structure. Run /iflow-dev:specify to fix.
{Level 4}: spec.md missing required sections (Success Criteria or Acceptance Criteria). Run /iflow-dev:specify to add them.
```
Stop execution. Do not proceed.

- If backward (re-running completed phase): Use AskUserQuestion:
  ```
  AskUserQuestion:
    questions: [{
      "question": "Phase 'implement' was already completed. Re-running will update timestamps but not undo previous work. Continue?",
      "header": "Backward",
      "options": [
        {"label": "Continue", "description": "Re-run the phase"},
        {"label": "Cancel", "description": "Stay at current phase"}
      ],
      "multiSelect": false
    }]
  ```
  If "Cancel": Stop execution.
- If warning (skipping other phases like tasks): Show warning via AskUserQuestion:
  ```
  AskUserQuestion:
    questions: [{
      "question": "Skipping {skipped phases}. This may reduce artifact quality. Continue anyway?",
      "header": "Skip",
      "options": [
        {"label": "Continue", "description": "Proceed despite skipping phases"},
        {"label": "Stop", "description": "Return to complete skipped phases"}
      ],
      "multiSelect": false
    }]
  ```
  If "Continue": Record skipped phases in `.meta.json` skippedPhases array, then proceed.
  If "Stop": Stop execution.

### 1b. Check Branch

If feature has a branch defined in `.meta.json`:
- Get current branch: `git branch --show-current`
- If current branch != expected branch, use AskUserQuestion:
  ```
  AskUserQuestion:
    questions: [{
      "question": "You're on '{current}', but feature uses '{expected}'. Switch branches?",
      "header": "Branch",
      "options": [
        {"label": "Switch", "description": "Run: git checkout {expected}"},
        {"label": "Continue", "description": "Stay on {current}"}
      ],
      "multiSelect": false
    }]
  ```
- Skip this check if branch is null (legacy feature)

### 2. Check for Partial Phase

If `phases.implement.started` exists but `phases.implement.completed` is null, use AskUserQuestion:
```
AskUserQuestion:
  questions: [{
    "question": "Detected partial implementation work. How to proceed?",
    "header": "Recovery",
    "options": [
      {"label": "Continue", "description": "Resume from where you left off"},
      {"label": "Start Fresh", "description": "Discard and begin new"},
      {"label": "Review First", "description": "View progress before deciding"}
    ],
    "multiSelect": false
  }]
```

### 3. Mark Phase Started

Update `.meta.json`:
```json
{
  "phases": {
    "implement": {
      "started": "{ISO timestamp}"
    }
  }
}
```

### 4. Implementation Phase

Execute the implementing skill with phased approach:

a. **Deploy subagents** - Select relevant implementer agents based on task domain

b. **Interface Phase** - Build type definitions, function signatures, module structure

c. **RED-GREEN Loop** - For each piece of functionality:
   - RED: Write failing test
   - GREEN: Write minimal code to pass
   - Loop until all functionality covered

d. **REFACTOR Phase** - Clean up while keeping tests green

e. **Return to main agent** with implementation report

### 5. Code Simplification Phase

Dispatch code-simplifier agent:
```
Task tool call:
  description: "Simplify implementation"
  subagent_type: iflow-dev:code-simplifier
  prompt: |
    Review the implementation for unnecessary complexity.

    Feature: {feature name}
    Files changed: {list of files created/modified}

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

No iteration limit. Loop continues until ALL reviewers approve.

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

    Files changed: {list of files}

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

    Files changed: {list of files}

    Check:
    - Input validation
    - Authentication/authorization
    - Data protection
    - OWASP top 10

    Return JSON with approval status and vulnerabilities.
```

**6d. Automated Iteration Logic:**

Collect results from all three reviewers (implementation, quality, security).

IF all three approved:
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

        {consolidated issue list from all reviewers}

        After fixing, return summary of changes made.
    ```
  → Increment iteration counter
  → Loop back to step 6a (repeat until all three approve)

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

### 7. Update State on Completion

Update `.meta.json`:
```json
{
  "phases": {
    "implement": {
      "completed": "{ISO timestamp}",
      "iterations": {count},
      "reviewerNotes": ["any unresolved concerns from reviews"]
    }
  },
  "currentPhase": "implement"
}
```

### 8. Completion Message

Use AskUserQuestion:
```
AskUserQuestion:
  questions: [{
    "question": "Implementation complete. Run /iflow-dev:finish next?",
    "header": "Next",
    "options": [
      {"label": "Yes (Recommended)", "description": "Complete the feature"},
      {"label": "Review implementation first", "description": "Inspect the code before finishing"}
    ],
    "multiSelect": false
  }]
```
