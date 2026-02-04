---
description: Start or continue implementation of current feature
---

Invoke the implementing skill for the current feature context.

Read docs/features/ to find active feature, then follow the workflow below.

## Workflow Integration

### 1. Validate Transition (HARD PREREQUISITE)

Before executing, check prerequisites using workflow-state skill:
- Read current `.meta.json` state
- Check for spec.md existence

**HARD BLOCK:** If spec.md does not exist:
```
❌ BLOCKED: spec.md required before implementation.

Implementation requires a specification to implement against.
Run /iflow:specify first to create the specification.
```
Stop execution. Do not proceed.

- If warning (skipping other phases like tasks): Show warning, ask to proceed

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
  subagent_type: iflow:code-simplifier
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

Execute review cycle with all four reviewers:

**6a. Spec Compliance Review:**
```
Task tool call:
  description: "Review spec compliance"
  subagent_type: iflow:spec-reviewer
  prompt: |
    Verify implementation matches specification.

    ## spec.md
    {content of spec.md}

    ## Implementation files
    {list of files with code}

    Return verification with COMPLIANT or ISSUES FOUND status.
```

**6b. Behavior Review:**
```
Task tool call:
  description: "Review implementation behavior"
  subagent_type: iflow:implementation-behavior-reviewer
  prompt: |
    Validate implementation behavior against requirements chain.

    ## tasks.md
    {content of tasks.md}

    ## spec.md
    {content of spec.md}

    ## design.md
    {content of design.md}

    ## PRD source
    {content of prd.md or brainstorm file}

    ## Implementation files
    {list of files with summaries}

    Return JSON with approval status and issues by level.
```

**6c. Code Quality Review:**
```
Task tool call:
  description: "Review code quality"
  subagent_type: iflow:code-quality-reviewer
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

**6d. Security Review:**
```
Task tool call:
  description: "Review security"
  subagent_type: iflow:security-reviewer
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

**6e. Automated Iteration Logic:**

Collect results from all four reviewers (spec, behavior, quality, security).

IF all four approved:
  → Proceed to Final Review (step 7)

ELSE (any issues found):
  → Append iteration to `.review-history.md`
  → Dispatch implementer agent to fix issues:
    ```
    Task tool call:
      description: "Fix review issues iteration {n}"
      subagent_type: iflow:implementer
      prompt: |
        Fix the following review issues:

        {consolidated issue list from all reviewers}

        After fixing, return summary of changes made.
    ```
  → Increment iteration counter
  → Loop back to step 6a (repeat until all four approve)

**Review History Entry Format** (append to `.review-history.md`):
```markdown
## Iteration {n} - {ISO timestamp}

**Spec Review:** {Compliant / Issues found}
**Behavior Review:** {Approved / Issues found}
**Quality Review:** {Approved / Issues found}
**Security Review:** {Approved / Issues found}
**Final Review:** {Approved / Issues found / Not run yet}

**Issues:**
- [{severity}] {reviewer}: {description} (at: {location})

**Changes Made:**
{Summary of revisions made to address issues}

---
```

### 7. Final Review (Automated)

Dispatch final-reviewer against PRD deliverables:
```
Task tool call:
  description: "Final review against PRD"
  subagent_type: iflow:final-reviewer
  prompt: |
    Verify implementation delivers PRD outcomes.

    ## PRD Source
    {content of prd.md or brainstorm file - the original requirements}

    ## Implementation Summary
    Files: {list of files created/modified}
    Tests: {test results summary}

    Does this deliver what was originally requested?
    Return JSON with approval status, issues, and evidence.
```

**Automated iteration on final review issues:**

IF final-reviewer approves:
  → Mark phase completed
  → Proceed to step 8

ELSE (issues found):
  → Append to `.review-history.md` under "Final Review" section
  → Dispatch implementer to fix:
    ```
    Task tool call:
      description: "Fix final review issues"
      subagent_type: iflow:implementer
      prompt: |
        The final reviewer found issues with PRD delivery:

        {issues from final-reviewer}

        Fix these issues to ensure PRD outcomes are met.
    ```
  → Increment iteration counter
  → Loop back to step 6a (full review cycle, repeat until final-reviewer approves)

### 8. Update State on Completion

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

### 9. Completion Message

Use AskUserQuestion:
```
AskUserQuestion:
  questions: [{
    "question": "Implementation complete. Run /iflow:finish next?",
    "header": "Next",
    "options": [
      {"label": "Yes (Recommended)", "description": "Complete the feature"},
      {"label": "Review implementation first", "description": "Inspect the code before finishing"}
    ],
    "multiSelect": false
  }]
```
