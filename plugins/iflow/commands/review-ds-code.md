---
description: Review data science Python code for anti-patterns and best practices
argument-hint: <file or directory path>
---

# Review DS Code Command

Dispatch the ds-code-reviewer agent to check DS Python code quality.

## Get Target File

If $ARGUMENTS is provided, use it as the target file or directory path.

If $ARGUMENTS is empty, prompt the user:

```
AskUserQuestion:
  questions: [{
    "question": "What would you like to review?",
    "header": "Target",
    "options": [
      {"label": "File", "description": "Review a single Python file or notebook"},
      {"label": "Directory", "description": "Review all Python/notebook files in a directory"},
      {"label": "Recent changes", "description": "Review recently modified DS files"}
    ],
    "multiSelect": false
  }]
```

After selection, ask for the path: "Please provide the file or directory path."

**If "Recent changes":** Use `git diff --name-only HEAD~5` to find recently modified `.py` and `.ipynb` files.

## Dispatch Agent

Use the Task tool to dispatch the ds-code-reviewer agent:

```
Task tool call:
  description: "Review DS code quality"
  subagent_type: iflow:ds-code-reviewer
  model: sonnet
  prompt: |
    Review this data science Python code for anti-patterns, pipeline quality,
    and DS-specific best practices:

    Target: {file or directory path from $ARGUMENTS or user input}

    Read the target file(s) and check for:
    - Anti-patterns (magic numbers, mutation, hardcoded paths, silent data loss, etc.)
    - Pipeline quality (pure functions, I/O boundaries, composition)
    - Code standards (type hints, docstrings, imports, logging, seeds)
    - Notebook quality (if .ipynb: header, structure, narrative, executability)
    - API correctness (verify at least 1 API usage via Context7)

    Return your findings as JSON with: approved, strengths, issues, verification, summary.
```

## On Completion

Present findings with severity levels:

1. Display summary
2. List blockers (if any) — must fix
3. List warnings — should fix
4. List suggestions — consider fixing
5. Display strengths — what was done well

Then offer follow-up:

```
AskUserQuestion:
  questions: [{
    "question": "Code review complete. What would you like to do?",
    "header": "Next Step",
    "options": [
      {"label": "Review analysis", "description": "Also check for statistical pitfalls with /review-ds-analysis"},
      {"label": "Address issues", "description": "Fix the identified code issues"},
      {"label": "Done", "description": "Review complete, no further action"}
    ],
    "multiSelect": false
  }]
```

**If "Review analysis":**
1. Invoke: `/iflow:review-ds-analysis {target file path}`

**If "Address issues":**
1. Display the issues list with suggested fixes
2. Offer to apply fixes automatically where possible

**If "Done":**
1. Display: "DS code review complete."
2. End the workflow
