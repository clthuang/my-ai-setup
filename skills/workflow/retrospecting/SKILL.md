---
name: retrospecting
description: Captures learnings from completed features into knowledge bank. Use after /finish or anytime to reflect. Updates constitution.md, patterns.md, etc.
---

# Retrospective

Capture and codify learnings.

## Read Feature Context

1. Find active feature folder in `docs/features/`
2. Read `.meta.json` for mode and context
3. Adjust behavior based on mode:
   - Hotfix: Skip to implementation guidance
   - Quick: Streamlined process
   - Standard: Full process with optional verification
   - Full: Full process with required verification

## Gather Data

Read feature folder:
- What verification issues occurred?
- What blockers were encountered?
- What surprises came up?
- What went well?

Ask user:
- "What would you do differently?"
- "What worked well?"
- "Any patterns worth documenting?"

## Identify Learnings

Categorize findings:

### Patterns (What worked)
- Approach that solved a problem well
- Technique worth reusing

### Anti-Patterns (What to avoid)
- Approach that caused problems
- Mistake not to repeat

### Heuristics (Decision guides)
- Rule of thumb discovered
- When to use which approach

### Principles (If fundamental enough)
- Core principle reinforced or discovered

## Propose Updates

For each learning, propose where it goes:

```
Learning: "Defining interfaces first enabled parallel work"

Proposed update:
- File: docs/knowledge-bank/patterns.md
- Add:
  ### Pattern: Early Interface Definition
  Define interfaces before implementation to enable parallel work.
  - Observed in: Feature #{id}
  - Benefit: Reduced integration issues

Add this? (y/n)
```

## Write Updates

For approved updates:
1. Read current file
2. Add new entry
3. Save file

## Output: retro.md

Write to `docs/features/{id}-{slug}/retro.md`:

```markdown
# Retrospective: {Feature Name}

## What Went Well
- {Positive observation}

## What Could Improve
- {Improvement area}

## Learnings Captured
- Added to patterns.md: {pattern name}
- Added to anti-patterns.md: {anti-pattern name}

## Action Items
- {Any follow-up actions}
```

## Completion

"Retrospective complete."
"Updated: {list of knowledge-bank files updated}"
"Saved to retro.md."
