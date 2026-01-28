---
name: writing-skills
description: Applies TDD approach to skill documentation with pressure testing. Use when creating new skills, editing existing skills, or verifying skills work.
---

# Writing Skills

**Writing skills IS Test-Driven Development applied to process documentation.**

## Core Principle

If you didn't watch an agent fail without the skill, you don't know if the skill teaches the right thing.

## TDD Mapping

| TDD Concept | Skill Creation |
|-------------|----------------|
| Test case | Pressure scenario with subagent |
| Production code | Skill document (SKILL.md) |
| Test fails (RED) | Agent violates rule without skill |
| Test passes (GREEN) | Agent complies with skill present |
| Refactor | Close loopholes while maintaining compliance |

## When to Create

**Create when:**
- Technique wasn't intuitively obvious
- You'd reference this again across projects
- Pattern applies broadly
- Others would benefit

**Don't create for:**
- One-off solutions
- Standard practices documented elsewhere
- Project-specific conventions (put in CLAUDE.md)

## SKILL.md Structure

```markdown
---
name: skill-name-with-hyphens
description: [What it does]. Use when [specific triggering conditions].
---

# Skill Name

## Overview
Core principle in 1-2 sentences.

## When to Use
Bullet list with symptoms and use cases.

## Core Pattern
Before/after or step-by-step.

## Common Mistakes
What goes wrong + fixes.
```

## Description Best Practices

- Format: "[What it does]. Use when [triggers]."
- Include specific triggers/symptoms
- Do NOT summarize the skill's workflow
- Written in third person
- Under 500 characters

**Bad:** "Use for TDD - write test first, watch it fail..."
**Good:** "Use when implementing any feature or bugfix, before writing implementation code"

## The Iron Law

```
NO SKILL WITHOUT A FAILING TEST FIRST
```

Write skill before testing? Delete it. Start over.

## Validation Checklist

- [ ] Name uses lowercase and hyphens only
- [ ] Description starts with "Use when..."
- [ ] Description doesn't summarize workflow
- [ ] Under 500 lines
- [ ] Tested with pressure scenario
- [ ] `./validate.sh` passes
