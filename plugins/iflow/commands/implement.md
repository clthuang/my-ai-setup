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

### 6. Review Phase (Iterative Loop)

Get max iterations from mode: Standard=2, Full=3.

Execute review cycle:

**6a. Behavior Review:**
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

**6b. Code Quality Review:**
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

**6c. Security Review:**
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

**6d. Branch on results:**
- All three approved → Proceed to Final Review (step 7)
- Any issues found AND iteration < max:
  - Append iteration to `.review-history.md`
  - Address the issues by revising implementation
  - Return to step 6a
- Max iterations hit → Note concerns in reviewerNotes, proceed to step 7

**Review History Entry Format** (append to `.review-history.md`):
```markdown
## Iteration {n} - {ISO timestamp}

**Behavior Review:** {Approved / Issues found}
**Quality Review:** {Approved / Issues found}
**Security Review:** {Approved / Issues found}

**Issues:**
- [{severity}] {reviewer}: {description} (at: {location})

**Changes Made:**
{Summary of revisions made to address issues}

---
```

### 7. Final Review

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

IF final-reviewer finds issues:
- Present issues to user
- Use AskUserQuestion:
  ```
  AskUserQuestion:
    questions: [{
      "question": "Final review found issues. How to proceed?",
      "header": "Final Review",
      "options": [
        {"label": "Address issues", "description": "Fix and re-review"},
        {"label": "Proceed anyway", "description": "Note concerns and continue"}
      ],
      "multiSelect": false
    }]
  ```
- If address: Loop back to implementation
- If proceed: Note in reviewerNotes

IF final-reviewer approves:
- Mark phase completed

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
