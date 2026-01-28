---
name: brainstorming
description: Guides ideation and exploration with incremental presentation and YAGNI discipline. Use when starting a feature, exploring options, or generating ideas.
---

# Brainstorming Phase

Guide divergent thinking to explore the problem space.

## Prerequisites

Check for feature context:
- Look for feature folder in `docs/features/`
- If not found: "No active feature. Run /create-feature first, or describe what you want to explore."

## Read Feature Context

1. Find active feature folder in `docs/features/`
2. Read `.meta.json` for mode and context
3. Adjust behavior based on mode:
   - Hotfix: Skip to implementation guidance
   - Quick: Streamlined process
   - Standard: Full process with optional verification
   - Full: Full process with required verification

## Process

### 1. Understand the Goal

Ask ONE question at a time:
- "What problem are you trying to solve?"
- "Who is this for?"
- "What does success look like?"

Prefer multiple choice when possible.

### 2. Explore Options

Generate 2-3 different approaches:
- Approach A: [description] — Pros, Cons
- Approach B: [description] — Pros, Cons
- Approach C: [description] — Pros, Cons

State your recommendation and why.

### 3. Identify Constraints

- Technical constraints?
- Time constraints?
- Dependencies?

### 4. Present Design Incrementally

When presenting a design or direction:
- Break into sections of 200-300 words
- After each section: "Does this look right so far?"
- Be ready to go back and clarify

### 5. Apply YAGNI Ruthlessly

Before finalizing:
- Review each proposed feature
- Ask: "Is this strictly necessary for the core goal?"
- Remove anything that's "nice to have"
- Simpler is better

### 6. Capture Ideas

As you discuss, note:
- Key ideas
- Decisions made
- Open questions

## Output: brainstorm.md

Write to `docs/features/{id}-{slug}/brainstorm.md`:

```markdown
# Brainstorm: {Feature Name}

## Problem Statement
{What we're solving}

## Goals
- {Goal 1}
- {Goal 2}

## Approaches Considered

### Approach A: {Name}
{Description}
- Pros: ...
- Cons: ...

### Approach B: {Name}
{Description}
- Pros: ...
- Cons: ...

## Chosen Direction
{Which approach and why}

## Open Questions
- {Question 1}
- {Question 2}

## Next Steps
Ready for /specify to define requirements.
```

## Completion

"Brainstorm complete. Saved to brainstorm.md."

For Standard/Full mode: "Run /verify to check, or /specify to continue."
For Quick mode: "Run /specify to continue."
