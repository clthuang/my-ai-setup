---
name: breaking-down-tasks
description: Breaks implementation plan into small, actionable tasks. Use after planning to create executable work items. Produces tasks.md.
---

# Task Breakdown Phase

Create small, actionable, testable tasks.

## Prerequisites

- If `plan.md` exists: Read for implementation order
- If not: "No plan found. Run /create-plan first."

## Read Feature Context

1. Find active feature folder in `docs/features/`
2. Read `.meta.json` for mode and context
3. Adjust behavior based on mode:
   - Hotfix: Skip to implementation guidance
   - Quick: Streamlined process
   - Standard: Full process with optional verification
   - Full: Full process with required verification

## Process

### 1. Break Down Each Plan Item

For each item in the plan:
- What are the smallest testable pieces?
- Each task: 5-15 minutes of work
- Each task: Clear completion criteria

### 2. Apply TDD Structure

For implementation tasks:
1. Write failing test
2. Implement minimal code
3. Verify test passes
4. Refactor if needed
5. Commit

### 3. Ensure Independence

Each task should:
- Be completable on its own
- Have clear inputs/outputs
- Not require context from other tasks

## Output: tasks.md

Write to `docs/features/{id}-{slug}/tasks.md`:

```markdown
# Tasks: {Feature Name}

## Task List

### Phase 1: Foundation

#### Task 1.1: {Brief description}
- **Files:** `path/to/file.ts`
- **Do:** {What to do}
- **Test:** {How to verify}
- **Done when:** {Completion criteria}

#### Task 1.2: {Brief description}
...

### Phase 2: Core Implementation

#### Task 2.1: {Brief description}
- **Depends on:** Task 1.1, 1.2
- **Files:** `path/to/file.ts`
- **Do:** {What to do}
- **Test:** {How to verify}
- **Done when:** {Completion criteria}

...

## Summary

- Total tasks: {n}
- Phase 1: {n} tasks
- Phase 2: {n} tasks
- Phase 3: {n} tasks
```

## State Tracking

If Vibe-Kanban available:
- Create card for each task
- Set dependencies

If TodoWrite:
- Create todo items

## Completion

"Tasks created. {n} tasks across {m} phases."
"Run /verify to check, or /implement to start building."
