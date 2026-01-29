---
name: specifying
description: Creates precise feature specifications with requirements and acceptance criteria. Use after brainstorming or when requirements need documenting. Produces spec.md.
---

# Specification Phase

Create precise, testable requirements.

## Prerequisites

Check for feature context:
- Look for feature folder in `docs/features/`
- If not found:
  - "No active feature. Would you like to /brainstorm first to explore ideas?"
  - Do NOT proceed without user confirmation
- If found:
  - If `brainstorm.md` exists: Read for context
  - If not: Gather requirements directly from user

## Read Feature Context

1. Find active feature folder in `docs/features/`
2. Read `.meta.json` for mode and context
3. Adjust behavior based on mode:
   - Hotfix: Skip to implementation guidance
   - Quick: Streamlined process
   - Standard: Full process with optional verification
   - Full: Full process with required verification

## Process

### 1. Define the Problem

From brainstorm or user input, distill:
- One-sentence problem statement
- Who it affects
- Why it matters

### 2. Define Success Criteria

Ask: "How will we know this is done?"

Each criterion must be:
- Specific (not vague)
- Measurable (can verify)
- Testable (can write test for)

### 3. Define Scope

**In scope:** What we WILL build
**Out of scope:** What we WON'T build (explicit)

Apply YAGNI: Remove anything not essential.

### 4. Define Acceptance Criteria

For each feature aspect:
- Given [context]
- When [action]
- Then [result]

## Output: spec.md

Write to `docs/features/{id}-{slug}/spec.md`:

```markdown
# Specification: {Feature Name}

## Problem Statement
{One sentence}

## Success Criteria
- [ ] {Criterion 1 — measurable}
- [ ] {Criterion 2 — measurable}

## Scope

### In Scope
- {What we will build}

### Out of Scope
- {What we explicitly won't build}

## Acceptance Criteria

### {Feature Aspect 1}
- Given {context}
- When {action}
- Then {result}

### {Feature Aspect 2}
- Given {context}
- When {action}
- Then {result}

## Dependencies
- {External dependency, if any}

## Open Questions
- {Resolved during spec or deferred}
```

## Self-Check Before Completing

- [ ] Each criterion is testable?
- [ ] No implementation details (what, not how)?
- [ ] No unnecessary features (YAGNI)?
- [ ] Concise (fits one screen)?

If any check fails, revise before saving.

## Completion

"Spec complete. Saved to spec.md."
"Run /verify to check, or /design to continue."
