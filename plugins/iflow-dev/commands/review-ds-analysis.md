---
description: Review data analysis for statistical pitfalls and methodology issues
argument-hint: <notebook or script path>
---

# Review Analysis Command

Load the analysis pitfalls skill and dispatch the ds-analysis-reviewer agent.

## Get Target File

If $ARGUMENTS is provided, use it as the target file path.

If $ARGUMENTS is empty, prompt the user:

```
AskUserQuestion:
  questions: [{
    "question": "What would you like to review?",
    "header": "Target",
    "options": [
      {"label": "Notebook", "description": "Review a Jupyter notebook (.ipynb)"},
      {"label": "Script", "description": "Review a Python script (.py)"},
      {"label": "Directory", "description": "Review all analysis files in a directory"}
    ],
    "multiSelect": false
  }]
```

After selection, ask for the path: "Please provide the file or directory path."

## Load Skill

Read the analysis pitfalls skill: Glob `~/.claude/plugins/cache/*/iflow*/*/skills/spotting-ds-analysis-pitfalls/SKILL.md` — read first match.
Fallback: Read `plugins/iflow-dev/skills/spotting-ds-analysis-pitfalls/SKILL.md` (dev workspace).
If not found: proceed with general analysis pitfall methodology.

## Dispatch Agent

Use the Task tool to dispatch the ds-analysis-reviewer agent:

```
Task tool call:
  description: "Review analysis for pitfalls"
  subagent_type: iflow-dev:ds-analysis-reviewer
  prompt: |
    Review this data analysis for statistical pitfalls, methodology issues, and conclusion validity:

    Target: {file path from $ARGUMENTS or user input}

    Read the target file(s) and apply the full pitfall diagnostic tree.
    Check methodology, statistical validity, data quality, and conclusions.
    Verify at least 1 statistical claim using external tools.

    Return your findings as JSON with: approved, pitfalls_detected, code_issues,
    methodology_concerns, verification, recommendations, summary.
```

## On Completion

After the agent completes the review, present findings and offer follow-up:

```
AskUserQuestion:
  questions: [{
    "question": "Analysis review complete. What would you like to do?",
    "header": "Next Step",
    "options": [
      {"label": "Review DS code quality", "description": "Also check code anti-patterns with /review-ds-code"},
      {"label": "Address issues", "description": "Fix the identified pitfalls and issues"},
      {"label": "Done", "description": "Review complete, no further action"}
    ],
    "multiSelect": false
  }]
```

**If "Review DS code quality":**
1. Invoke: `/iflow-dev:review-ds-code {target file path}`

**If "Address issues":**
1. Display the issues list with suggested fixes
2. Offer to apply fixes automatically where possible

**If "Done":**
1. Display: "Analysis review complete."
2. End the workflow
