---
name: subagent-driven-development
description: Orchestrates task execution with fresh subagent per task and two-stage review. Use when executing implementation plans with independent tasks in the current session.
---

# Subagent-Driven Development

Execute plan by dispatching fresh subagent per task, with two-stage review after each.

## Core Principle

Fresh subagent per task + two-stage review (spec then quality) = high quality, fast iteration.

## The Process

For each task in the plan:

### 1. Dispatch Implementer

Use `agents/implementer.md` with:
- Full task text (don't make subagent read plan file)
- Scene-setting context (where this fits, dependencies)
- Working directory

### 2. Answer Questions

If implementer asks questions:
- Answer clearly and completely
- Provide additional context if needed
- Don't rush them into implementation

### 3. Spec Compliance Review

After implementer commits, dispatch `agents/spec-reviewer.md`:
- Provide task requirements
- Provide implementer's report
- **Do NOT proceed until spec review passes**

If issues found → implementer fixes → re-review

### 4. Code Quality Review

**Only after spec compliance passes**, dispatch `agents/code-quality-reviewer.md`:
- Provide what was implemented
- Provide git SHAs (base and head)

If issues found → implementer fixes → re-review

### 5. Mark Complete

Only mark task complete when both reviews pass.

## Red Flags - Never

- Skip reviews (spec OR quality)
- Proceed with unfixed issues
- Start quality review before spec compliance passes
- Trust implementer report without verification
- Move to next task while review has open issues

## Integration

**Required skills:**
- `test-driven-development` - Subagents follow TDD
- `verification-before-completion` - Verify before claiming done

**When complete:**
- Use `finishing-branch` skill to handle merge/PR/cleanup

## Prompt Templates

Use these templates when dispatching subagents:

- [Implementer Prompt](templates/implementer-prompt.md) - Task implementation dispatch
- [Spec Reviewer Prompt](templates/spec-reviewer-prompt.md) - Spec compliance verification
- [Code Quality Reviewer Prompt](templates/code-quality-reviewer-prompt.md) - Quality assessment

## Key Template Principles

**Implementer:**
- Provide FULL task text (don't make subagent read file)
- Include scene-setting context
- Encourage questions before starting
- Require self-review before reporting

**Spec Reviewer:**
- Do NOT trust implementer report
- Verify by reading actual code
- Check for missing requirements
- Check for extra/unneeded work

**Code Quality Reviewer:**
- Only after spec compliance passes
- Focus on HOW not WHAT
- Categorize issues (Critical/Important/Minor)
- Provide fix suggestions
