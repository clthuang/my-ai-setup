---
name: implementing
description: Dispatches per-task implementer agents from tasks.md, collecting reports into implementation-log.md. Use when the user says 'implement the feature', 'start coding', 'write the code', or 'execute tasks'.
---

# Implementation Phase

Execute the implementation plan with a structured per-task dispatch approach.

## Prerequisites

- If `tasks.md` exists: Read for task list
- If not: "No tasks found. Run /iflow-dev:create-tasks first, or describe what to implement."

## Related Skills

For complex implementations:
- `implementing-with-tdd` - RED-GREEN-REFACTOR discipline

## Read Feature Context

1. Find active feature folder in `docs/features/`
2. Read `.meta.json` for mode and context
3. Adjust behavior based on mode:
   - Standard: Full process with optional verification
   - Full: Full process with required verification

## Process

### Step 1: Read Task List

1. Read `tasks.md` from the active feature directory
2. Parse all task headings using regex: `/^(#{3,4})\s+Task\s+(\d+(?:\.\d+)*):?\s*(.+)$/`
3. For each match, extract:
   - **Task number** (string, e.g., "1.1")
   - **Task title**
   - **Task body** (from heading through next same-or-higher-level heading, or EOF)
   - **Why/Source** field value (from `**Why:**` or `**Source:**`, if present)
   - **Done when** criteria (from `**Done when:**`, if present)
4. If no task headings found: log error, surface to user, STOP

### Step 2: Per-Task Dispatch Loop

For each task (in document order, top to bottom):

**a. Prepare context**

Load feature artifacts from the active feature directory:
- `spec.md`: always in full
- `design.md`: in full (selective loading deferred to future task)
- `plan.md`: in full (selective loading deferred to future task)
- `prd.md`: extract `## Problem Statement` and `## Goals` sections only

**b. Dispatch implementer agent**

```
Task tool call:
  subagent_type: iflow-dev:implementer
  prompt: |
    {task description with done-when criteria}

    ## Spec
    {spec.md content}

    ## Design
    {design.md content}

    ## Plan
    {plan.md content}

    ## PRD Context
    {Problem Statement + Goals from prd.md}
```

**c. Collect report**

Extract from the agent's text response:
- **Files changed** — required
- **Decisions** — optional, default "none"
- **Deviations** — optional, default "none"
- **Concerns** — optional, default "none"

Use substring match (case-insensitive) for field headers.

**d. Append implementation-log.md entry**

Write to `implementation-log.md` in the active feature directory.
Create with `# Implementation Log` header if this is the first task.

```markdown
## Task {number}: {title}
- **Files changed:** {from report}
- **Decisions:** {from report, or "none"}
- **Deviations:** {from report, or "none"}
- **Concerns:** {from report, or "none"}
```

**e. Error handling per task**

- **Dispatch failure (AC-20):** Log the error, then ask the user whether to retry or skip via AskUserQuestion.
- **Malformed report (AC-21):** Write a partial log entry with whatever fields are available, then proceed to the next task.

**f. Proceed to next task**

### Step 3: Return Results

After all tasks dispatched:

1. Report summary: N tasks completed, M skipped/blocked
2. Return deduplicated list of all files changed
3. `implementation-log.md` is on disk for retro to read later

## Commit Pattern

After all tasks dispatched:
```
git add {files}
git commit -m "feat: {brief description}"
```

## Error Handling

If implementation is stuck:
1. Try a different approach
2. Break into smaller pieces
3. Ask user for guidance

**Dispatch failure (AC-20):** If the Task tool call fails or the agent errors out, log the failure and present the user with retry/skip options via AskUserQuestion.

**Malformed report (AC-21):** If the agent response is missing expected fields, write a partial log entry using whatever fields were returned, default missing fields to "none", and continue to the next task.

Never spin endlessly. Ask when stuck.

## Completion

After all tasks:
"Implementation complete. {N} tasks completed, {M} skipped."
"Proceeding to code simplification and review phases."
