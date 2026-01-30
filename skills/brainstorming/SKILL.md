---
name: brainstorming
description: Guides ideation and exploration with incremental presentation and YAGNI discipline. Use when starting a feature, exploring options, or generating ideas.
---

# Brainstorming Phase

Guide divergent thinking to explore the problem space.

## Prerequisites

Check for feature context:
- Look for feature folder in `docs/features/`
- If found: Ask "Add to existing feature's brainstorm, or start a new brainstorm?"
  - Add to existing: Proceed to "Read Feature Context" below
  - Start new: Proceed to "Standalone Mode" below
- If not found: Proceed to "Standalone Mode" below

## Read Feature Context (With Active Feature)

1. Find active feature folder in `docs/features/`
2. Read `.meta.json` for mode and context
3. Adjust behavior based on mode:
   - Hotfix: Skip to implementation guidance
   - Quick: Streamlined process
   - Standard: Full process with optional verification
   - Full: Full process with required verification
4. Write output to `docs/features/{id}-{slug}/brainstorm.md`

## Standalone Mode (No Active Feature)

When no feature context exists or user chooses new brainstorm:

### 1. Create Scratch File

- Get topic from user argument or ask: "What would you like to brainstorm?"
- Generate timestamp: `YYYYMMDD-HHMMSS` format (e.g., `20260129-143052`)
- Generate slug from topic:
  - Lowercase
  - Replace spaces/special chars with hyphens
  - Max 30 characters
  - Trim trailing hyphens
  - If empty, use "untitled"
- Create file: `docs/brainstorms/{timestamp}-{slug}.md`

### 2. Run Exploration

Follow the standard Process (below) for brainstorming.
Write content to the scratch file as you go.

### 3. Promotion Flow

At end of brainstorming session, ask:

"Turn this into a feature? (y/n)"

**If yes:**
1. Ask for workflow mode:
   ```
   Modes:
   1. Hotfix — implement only
   2. Quick — spec → tasks → implement
   3. Standard — all phases
   4. Full — all phases, required verification
   ```
2. Generate feature ID: Find highest number in `docs/features/` and add 1
3. Create folder: `docs/features/{id}-{slug}/`
4. Create feature branch:
   ```bash
   git checkout -b feature/{id}-{slug}
   ```
5. Move scratch file to feature folder as `brainstorm.md`
6. Create `.meta.json`:
   ```json
   {
     "id": "{id}",
     "name": "{slug}",
     "mode": "{selected-mode}",
     "created": "{ISO timestamp}",
     "branch": "feature/{id}-{slug}",
     "brainstorm_source": "{original scratch file path}"
   }
   ```
7. Inform user: "Feature {id}-{slug} created on branch feature/{id}-{slug}. Continuing to /specify..."
8. Auto-invoke `/specify`

**If no:**
- Inform: "Saved to docs/brainstorms/{filename}. You can revisit later."
- End session

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

Write to scratch file (standalone) or `docs/features/{id}-{slug}/brainstorm.md` (with feature):

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

**With active feature:**
- "Brainstorm complete. Saved to brainstorm.md."
- For Standard/Full mode: "Run /verify to check, or /specify to continue."
- For Quick mode: "Run /specify to continue."

**Standalone mode:**
- Follow "Promotion Flow" above to decide next steps.
