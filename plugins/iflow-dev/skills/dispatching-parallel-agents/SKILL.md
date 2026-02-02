---
name: dispatching-parallel-agents
description: Dispatches one agent per independent problem domain for concurrent investigation. Use when facing 2+ independent tasks without shared state or dependencies.
---

# Dispatching Parallel Agents

When you have multiple unrelated problems, investigating them sequentially wastes time.

## Core Principle

Dispatch one agent per independent problem domain. Let them work concurrently.

## When to Use

**Use when:**
- 3+ failures with different root causes
- Multiple subsystems broken independently
- Each problem can be understood without context from others
- No shared state between investigations

**Don't use when:**
- Failures are related (fix one might fix others)
- Need to understand full system state
- Agents would interfere (editing same files)

## The Pattern

### 1. Identify Independent Domains

Group by what's broken:
- File A tests: one domain
- File B tests: different domain
- Each domain is independent

### 2. Create Focused Agent Tasks

Each agent gets:
- **Specific scope:** One test file or subsystem
- **Clear goal:** Make these tests pass
- **Constraints:** Don't change other code
- **Expected output:** Summary of findings and fixes

### 3. Dispatch in Parallel

```
Task("Fix file-a.test.ts failures")
Task("Fix file-b.test.ts failures")
// Both run concurrently
```

### 4. Review and Integrate

When agents return:
- Read each summary
- Verify fixes don't conflict
- Run full test suite
- Integrate all changes

## Agent Prompt Structure

Good prompts are:
- **Focused:** One clear problem domain
- **Self-contained:** All context needed
- **Specific about output:** What should agent return?

## Common Mistakes

| Mistake | Fix |
|---------|-----|
| "Fix all the tests" | Specify exact file/subsystem |
| No context | Paste error messages and test names |
| No constraints | "Do NOT change production code" |
| Vague output | "Return summary of root cause and changes" |
