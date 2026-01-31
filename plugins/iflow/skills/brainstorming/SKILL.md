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

### 7. Verification (REQUIRED)

Before the promotion question, you MUST verify the brainstorm:

1. Invoke reviewer via Task tool:
   ```
   Task:
     description: "Review brainstorm for promotion"
     subagent_type: "iflow:brainstorm-reviewer"
     prompt: |
       Review this brainstorm file for readiness to become a feature:
       File: {absolute path to brainstorm file}

       Checklist:
       - Problem clearly stated?
       - Goals defined?
       - Options explored?
       - Direction chosen?
       - Rationale documented?

       Return JSON: { "approved": bool, "issues": [...], "summary": "..." }
   ```

2. Parse response and check for blockers (severity: "blocker")

3. If blockers found:
   - Show: "Review found blockers:\n🔴 {description} (at: {location})"
   - Ask user to address issues
   - Re-verify when user says "ready"
   - If user says "skip verification" → proceed with warning

4. If no blockers → Proceed to Promotion Flow

5. If reviewer unavailable → Show warning, proceed to Promotion Flow

### 8. Promotion Flow (REQUIRED)

After verification passes, you MUST use AskUserQuestion:

1. Call AskUserQuestion tool with EXACTLY:
   ```
   AskUserQuestion:
     questions: [{
       "question": "Turn this into a feature?",
       "header": "Promote",
       "options": [
         {"label": "Yes", "description": "Create feature and continue workflow"},
         {"label": "No", "description": "End session, brainstorm already saved"}
       ],
       "multiSelect": false
     }]
   ```

2. Handle response:

   **If "Yes":**
   a. Ask for mode:
      ```
      AskUserQuestion:
        questions: [{
          "question": "Which workflow mode?",
          "header": "Mode",
          "options": [
            {"label": "Standard", "description": "All phases, optional verification"},
            {"label": "Full", "description": "All phases, required verification"}
          ],
          "multiSelect": false
        }]
      ```
   b. Invoke `/iflow:create-feature` with brainstorm content
   c. STOP (create-feature handles the rest)

   **If "No":**
   a. Output: "Brainstorm saved to {filepath}."
   b. STOP — Do NOT continue with any other action

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
Ready for /iflow:specify to define requirements.
```

## Completion

**Both standalone and with-feature modes** use the same closing sequence:
1. Run verification (### 7)
2. Run promotion flow (### 8)

The only difference is where the file is saved:
- Standalone: `docs/brainstorms/{timestamp}-{slug}.md`
- With feature: `docs/features/{id}-{slug}/brainstorm.md`

## PROHIBITED Actions

When executing the brainstorming skill, you MUST NOT:

- Proceed to /iflow:specify, /iflow:design, /iflow:create-plan, or /iflow:implement
- Write any implementation code
- Create feature folders directly (use /iflow:create-feature)
- Continue with any action after user says "No" to promotion
- Skip the verification step
- Skip the AskUserQuestion promotion gate
