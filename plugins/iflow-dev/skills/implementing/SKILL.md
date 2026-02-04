---
name: implementing
description: This skill should be used when the user says 'implement the feature', 'start coding', 'write the code', or 'execute tasks'. Guides phased TDD implementation (Interface → RED-GREEN → REFACTOR).
---

# Implementation Phase

Execute the implementation plan with a structured phased approach.

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

### Phase 1: Deploy Implementation Subagents

Select and dispatch relevant implementer agents based on:
- Task domain (UI, API, DB, etc.)
- Technology stack
- Complexity level

Use `Task` tool with appropriate `subagent_type`:
- `implementer` for general implementation with TDD
- `generic-worker` for mixed-domain tasks

### Phase 2: Interface Phase (Scaffold)

Before writing implementation:

1. **Define type definitions / interfaces**
   - Create types for all data structures
   - Define function signatures with documentation

2. **Set up module structure**
   - Create file/folder organization
   - Establish imports/exports

3. **Establish contracts between components**
   - Define how modules interact
   - Document expected inputs/outputs

This creates the "skeleton" that tests can target.

### Phase 3: RED-GREEN Loop

For each piece of functionality:

**RED Phase:**
1. Write ONE failing test
2. Test must fail for the expected reason
3. Test targets the interface defined in Phase 2
4. Run test - confirm it FAILS

**GREEN Phase:**
1. Write MINIMAL code to pass the test
2. No more than necessary
3. Run test - confirm it PASSES

**Loop:** Continue RED-GREEN until functionality complete.

### Phase 4: REFACTOR Phase

After all tests pass:

1. Remove duplication
2. Improve naming
3. Extract helpers if needed
4. Keep all tests green throughout

### Phase 5: Return to Main Agent

Report back with:
- What was implemented
- Test results
- Files changed
- Any concerns or blockers

## Task Selection

From tasks.md, find first incomplete task:
- Check Vibe-Kanban/TodoWrite for status
- Or ask user which task to work on

Read task details:
- What files are involved?
- What's the expected outcome?
- What tests verify completion?

## Commit Pattern

After completing each task:
```
git add {files}
git commit -m "feat: {brief description}"
```

## Error Handling

If implementation is stuck:
1. Try a different approach
2. Break into smaller pieces
3. Ask user for guidance

Never spin endlessly. Ask when stuck.

## Completion

After all tasks:
"Implementation complete. {n} tasks done."
"Proceeding to code simplification and review phases."
