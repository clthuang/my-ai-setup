---
name: implementing
description: Guides code implementation with TDD approach. Use when ready to write code. Works through tasks.md items systematically.
---

# Implementation Phase

Execute the implementation plan.

## Prerequisites

- If `tasks.md` exists: Read for task list
- If not: "No tasks found. Run /tasks first, or describe what to implement."

## Process

### 1. Select Next Task

From tasks.md, find first incomplete task:
- Check Vibe-Kanban/TodoWrite for status
- Or ask user which task to work on

### 2. Understand the Task

Read task details:
- What files are involved?
- What's the expected outcome?
- What tests verify completion?

### 3. Implement with TDD

For each task:

**Step A: Write the test first**
```
Create test that describes expected behavior.
Run test - should FAIL (red).
```

**Step B: Write minimal implementation**
```
Write just enough code to pass the test.
Run test - should PASS (green).
```

**Step C: Refactor if needed**
```
Clean up code while keeping tests green.
```

**Step D: Commit**
```
git add {files}
git commit -m "feat: {brief description}"
```

### 4. Mark Complete

Update Vibe-Kanban/TodoWrite status.

### 5. Next Task or Done

If more tasks: "Task complete. Continue to next task?"
If all done: "All tasks complete. Run /verify for quality review, then /finish."

## Agent Delegation

For complex tasks, consider delegation:

```
All files in one domain?
  Frontend (.tsx, .css) → frontend-specialist
  API (routes, handlers) → api-specialist
  Database (migrations) → database-specialist
  Mixed → handle directly

Unsure? Ask user.
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
"Run /verify for quality review."
"Run /finish when ready to complete the feature."
