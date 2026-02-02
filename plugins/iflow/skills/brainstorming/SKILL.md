---
name: brainstorming
description: Guides ideation and exploration through a 6-stage process producing evidence-backed PRDs. Use when starting a feature, exploring options, or generating ideas.
---

# Brainstorming Phase

Guide divergent thinking through a structured 6-stage process that produces a PRD.

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
4. Write output to `docs/features/{id}-{slug}/brainstorm.prd.md`

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
- Create file: `docs/brainstorms/{timestamp}-{slug}.prd.md`

### 2. Run 6-Stage Process

Follow the Process below, writing content to the PRD file as you go.

## Process

The brainstorm follows 6 stages in sequence:

```
Stage 1: CLARIFY → Stage 2: RESEARCH → Stage 3: DRAFT PRD
                                              ↓
Stage 6: USER DECISION ← Stage 5: AUTO-CORRECT ← Stage 4: CRITICAL REVIEW
```

---

### Stage 1: CLARIFY

Resolve ambiguities through interactive Q&A before research.

**Ask ONE question at a time.** Prefer multiple choice when possible.

Questions to cover:
- "What problem are you trying to solve?"
- "Who is this for?"
- "What does success look like?"
- "What constraints exist?"
- "What approaches have you considered?"

**Apply YAGNI Ruthlessly:**
- Review each proposed feature
- Ask: "Is this strictly necessary for the core goal?"
- Remove anything that's "nice to have"
- Simpler is better

**Completion marker:** User confirms understanding is correct, or you have enough context to proceed.

---

### Stage 2: RESEARCH

Deploy research subagents in parallel to gather evidence.

**Invoke all 3 research agents simultaneously** using multiple Task tool calls in a single response:

```
Task tool call 1:
  description: "Research internet for {topic}"
  subagent_type: "iflow-dev:internet-researcher"
  prompt: |
    query: "{topic/question}"
    context: "{what we're building}"

Task tool call 2:
  description: "Explore codebase for {topic}"
  subagent_type: "iflow-dev:codebase-explorer"
  prompt: |
    query: "{topic/question}"
    context: "{what we're building}"

Task tool call 3:
  description: "Search skills for {topic}"
  subagent_type: "iflow-dev:skill-searcher"
  prompt: |
    query: "{topic/question}"
    context: "{what we're building}"
```

**Collect findings** from all three agents. Each returns:
```json
{
  "findings": [{"finding": "...", "source": "...", "relevance": "high|medium|low"}],
  "no_findings_reason": "..." // if empty
}
```

**Error handling:**
- If an agent fails or is unavailable → Note warning, proceed with other findings
- If all agents return empty → Proceed with "Assumption: needs verification" labels

---

### Stage 3: DRAFT PRD

Generate the PRD using the template, incorporating research findings.

**Evidence citation format:** Every claim must cite its source:
- `{claim} — Evidence: {source URL}`
- `{claim} — Evidence: {file:line}`
- `{claim} — Evidence: User input`
- `{claim} — Assumption: needs verification`

Write the PRD to the scratch file using the PRD Output Format below.

---

### Stage 4: CRITICAL REVIEW

Invoke the PRD reviewer agent to challenge the draft.

```
Task tool call:
  description: "Critical review of PRD"
  subagent_type: "iflow-dev:prd-reviewer"
  prompt: |
    Review this PRD for quality and completeness:

    {full PRD content}

    Return JSON: { "approved": bool, "issues": [...], "summary": "..." }
```

**Parse response** and collect issues array.

**Error handling:**
- If reviewer unavailable → Show warning, proceed to Stage 5 with empty issues

---

### Stage 5: AUTO-CORRECT

Apply actionable improvements from the review.

**For each issue in the issues array:**

1. If `severity: "blocker"` or `severity: "warning"`:
   - Determine if fix is actionable (has `suggested_fix`)
   - Apply the fix to the PRD content
   - Record: `Changed: {what} — Reason: {issue description}`

2. If `severity: "suggestion"`:
   - Consider but don't require action
   - Record if applied

**Update the PRD file** with all corrections.

**Add to Review History section:**
```markdown
### Review 1 ({date})
**Findings:**
- [{severity}] {description} (at: {location})

**Corrections Applied:**
- {what changed} — Reason: {reference to finding}
```

---

### Stage 6: USER DECISION

Present the corrected PRD and ask user for next steps.

**Use AskUserQuestion with EXACTLY:**
```
AskUserQuestion:
  questions: [{
    "question": "PRD complete. What would you like to do?",
    "header": "Decision",
    "options": [
      {"label": "Promote to Feature", "description": "Create feature and continue workflow"},
      {"label": "Refine Further", "description": "Loop back to clarify and improve"},
      {"label": "Save and Exit", "description": "Keep PRD, end session"}
    ],
    "multiSelect": false
  }]
```

**Handle response:**

**If "Promote to Feature":**
1. Ask for mode:
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
2. Invoke `/iflow:create-feature` with PRD content
3. STOP (create-feature handles the rest)

**If "Refine Further":**
1. Ask what needs refinement
2. Loop back to Stage 1 with new context
3. Research and review again

**If "Save and Exit":**
1. Output: "PRD saved to {filepath}."
2. STOP — Do NOT continue with any other action

---

## PRD Output Format

Write to scratch file (standalone) or `docs/features/{id}-{slug}/brainstorm.prd.md` (with feature):

```markdown
# PRD: {Feature Name}

## Status
- Created: {date}
- Last updated: {date}
- Status: Draft

## Problem Statement
{What problem are we solving? Why does it matter?}

### Evidence
- {Source}: {Finding that supports this problem exists}

## Goals
1. {Goal 1}
2. {Goal 2}

## Success Criteria
- [ ] {Measurable criterion 1}
- [ ] {Measurable criterion 2}

## User Stories

### Story 1: {Title}
**As a** {role}
**I want** {capability}
**So that** {benefit}

**Acceptance criteria:**
- {criterion}

## Use Cases

### UC-1: {Title}
**Actors:** {who}
**Preconditions:** {what must be true}
**Flow:**
1. {step}
2. {step}
**Postconditions:** {what is true after}
**Edge cases:**
- {edge case with handling}

## Edge Cases & Error Handling
| Scenario | Expected Behavior | Rationale |
|----------|-------------------|-----------|
| {case}   | {behavior}        | {why}     |

## Constraints

### Behavioral Constraints (Must NOT do)
- {Behavior to avoid} — Rationale: {why this would be harmful}

### Technical Constraints
- {Technical limitation} — Evidence: {source}

## Requirements

### Functional
- FR-1: {requirement}

### Non-Functional
- NFR-1: {requirement}

## Non-Goals
Strategic decisions about what this feature will NOT aim to achieve.

- {Non-goal} — Rationale: {why we're explicitly not pursuing this}

## Out of Scope (This Release)
Items excluded from current scope but may be considered later.

- {Item} — Future consideration: {when/why it might be added}

## Research Summary

### Internet Research
- {Finding} — Source: {URL/reference}

### Codebase Analysis
- {Pattern/constraint found} — Location: {file:line}

### Existing Capabilities
- {Relevant skill/feature} — How it relates: {explanation}

## Review History
{Added by Stage 5 auto-correct}

## Open Questions
- {Question that needs resolution}

## Next Steps
Ready for /iflow:create-feature to begin implementation.
```

---

## Error Handling

### WebSearch Unavailable
- Skip internet research with warning: "WebSearch unavailable, skipping internet research"
- Proceed with codebase and skills research only

### Agent Unavailable
- Show warning: "{agent} unavailable, proceeding without"
- Continue with available agents

### All Research Fails
- Proceed with user input only
- Mark all claims as: "Assumption: needs verification"

### PRD Reviewer Unavailable
- Show warning: "PRD reviewer unavailable, skipping critical review"
- Proceed directly to Stage 6

---

## Completion

**Both standalone and with-feature modes** use the same 6-stage process.

The only difference is where the file is saved:
- Standalone: `docs/brainstorms/{timestamp}-{slug}.prd.md`
- With feature: `docs/features/{id}-{slug}/brainstorm.prd.md`

---

## PROHIBITED Actions

When executing the brainstorming skill, you MUST NOT:

- Proceed to /iflow:specify, /iflow:design, /iflow:create-plan, or /iflow:implement
- Write any implementation code
- Create feature folders directly (use /iflow:create-feature)
- Continue with any action after user says "Save and Exit"
- Skip the research stage (Stage 2)
- Skip the review stage (Stage 4)
- Skip the AskUserQuestion decision gate (Stage 6)
