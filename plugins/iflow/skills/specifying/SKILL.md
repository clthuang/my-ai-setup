---
name: specifying
description: Creates precise specifications. Use when the user says 'write the spec', 'document requirements', 'define acceptance criteria', or 'create spec.md'.
---

# Specification Phase

Create precise, testable requirements.

## Prerequisites

Check for feature context:
- Look for feature folder in `docs/features/`
- If not found:
  - "No active feature. Would you like to /iflow:brainstorm first to explore ideas?"
  - Do NOT proceed without user confirmation
- If found:
  - Check for `docs/features/{id}-{slug}/prd.md`
  - If `prd.md` exists: Read for context, use as input for spec
  - If `prd.md` not found:
    ```
    AskUserQuestion:
      questions: [{
        "question": "No PRD found. How to proceed?",
        "header": "PRD Missing",
        "options": [
          {"label": "Run /brainstorm", "description": "Create PRD through brainstorming first"},
          {"label": "Describe feature now", "description": "Provide requirements directly"}
        ],
        "multiSelect": false
      }]
    ```
    - If "Run /brainstorm": Invoke `/iflow:brainstorm` → STOP
    - If "Describe feature now": Proceed to gather requirements directly

## Read Feature Context

1. Find active feature folder in `docs/features/`
2. Read `.meta.json` for mode and context
3. Adjust behavior based on mode:
   - Standard: Full process with optional verification
   - Full: Full process with required verification

## Process

### If PRD exists:

1. **Draft spec.md from PRD content:**
   - Problem Statement: from PRD "Problem Statement" section
   - Success Criteria: from PRD "Goals" or "Success Metrics"
   - Scope: from PRD "Scope" section (In Scope / Out of Scope)
   - Acceptance Criteria: derive from PRD requirements

2. **Present draft to user:**
   ```
   AskUserQuestion:
     questions: [{
       "question": "Review this spec. What needs to change?",
       "header": "Review",
       "options": [
         {"label": "Looks good", "description": "Save and complete"},
         {"label": "Edit problem", "description": "Revise problem statement"},
         {"label": "Edit criteria", "description": "Revise success/acceptance criteria"},
         {"label": "Edit scope", "description": "Revise scope boundaries"}
       ],
       "multiSelect": false
     }]
   ```

3. Repeat until user selects "Looks good"

### If no PRD (user chose "Describe feature"):

1. **Define the Problem**
   From user input, distill:
   - One-sentence problem statement
   - Who it affects
   - Why it matters

2. **Define Success Criteria**
   Ask: "How will we know this is done?"
   Each criterion must be:
   - Specific (not vague)
   - Measurable (can verify)
   - Testable (can write test for)

3. **Define Scope**
   **In scope:** What we WILL build
   **Out of scope:** What we WON'T build (explicit)
   Apply YAGNI: Remove anything not essential.

4. **Define Acceptance Criteria**
   For each feature aspect:
   - Given [context]
   - When [action]
   - Then [result]

5. **Draft spec, present for review** (same AskUserQuestion as above)

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
"Run /iflow:verify to check, or /iflow:design to continue."
