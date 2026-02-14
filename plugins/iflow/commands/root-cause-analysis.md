---
description: Investigate bugs and failures to find all root causes
argument-hint: <bug description or test failure>
---

# Root Cause Analysis Command

Invoke the root-cause-analysis skill and dispatch the rca-investigator agent.

## Get Bug Description

If $ARGUMENTS is provided, use it as the bug description.

If $ARGUMENTS is empty, prompt the user:

```
AskUserQuestion:
  questions: [{
    "question": "What bug or failure would you like to investigate?",
    "header": "Bug Description",
    "options": [
      {"label": "Test failure", "description": "A test is failing with an error"},
      {"label": "Runtime error", "description": "Application throws an error"},
      {"label": "Unexpected behavior", "description": "Something works incorrectly"}
    ],
    "multiSelect": false
  }]
```

After selection, ask for details: "Please describe the specific error or behavior."

## Load Skill

Reference the RCA methodology:
@plugins/iflow/skills/root-cause-analysis/SKILL.md

## Dispatch Agent

Use the Task tool to dispatch the rca-investigator agent:

```
Task tool call:
  description: "Investigate root causes"
  subagent_type: iflow:rca-investigator
  prompt: |
    Investigate this bug/failure:

    {bug description from $ARGUMENTS or user input}

    Follow the 6-phase RCA process. Generate a report at docs/rca/.
```

## On Completion

After the agent completes the RCA, offer handoff options:

```
AskUserQuestion:
  questions: [{
    "question": "RCA complete. What would you like to do?",
    "header": "Next Step",
    "options": [
      {"label": "Create feature for fix", "description": "Start /create-feature with RCA findings"},
      {"label": "Save and exit", "description": "Keep report, end session"}
    ],
    "multiSelect": false
  }]
```

**If "Create feature for fix":**
1. Extract the title from the RCA report
2. Invoke: `/create-feature "Fix: {rca-title}"`
3. Display: "RCA report available at: {report-path} - reference for Problem Statement"

**If "Save and exit":**
1. Display: "RCA report saved to {report-path}"
2. End the workflow
