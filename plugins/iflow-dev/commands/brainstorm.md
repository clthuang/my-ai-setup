---
description: Start brainstorming - produces evidence-backed PRD through 6-stage process
argument-hint: [topic or idea to explore]
---

Invoke the brainstorming skill.

Check docs/features/ for active feature:
- If found: Ask whether to add to existing feature or start new brainstorm
- If not found: Start standalone brainstorm (creates scratch file in docs/brainstorms/)

Follow brainstorming skill instructions for the 6-stage process:
1. CLARIFY - Resolve ambiguities through Q&A
2. RESEARCH - Parallel subagent research (internet, codebase, skills)
3. DRAFT PRD - Generate PRD with evidence citations
4. CRITICAL REVIEW - Challenge assumptions and gaps
5. AUTO-CORRECT - Apply actionable improvements
6. USER DECISION - Promote to feature, refine, or save

Output: `{timestamp}-{slug}.prd.md` in docs/brainstorms/ (standalone) or feature folder.

## State Management

When brainstorming within an active feature:

**On start:** Update `.meta.json` to mark phase started:
```json
{
  "phases": {
    "brainstorm": {
      "started": "{ISO timestamp}"
    }
  }
}
```

**On completion:** Update `.meta.json` to mark phase completed:
```json
{
  "phases": {
    "brainstorm": {
      "completed": "{ISO timestamp}",
      "iterations": 1
    }
  },
  "currentPhase": "brainstorm"
}
```

Note: Brainstorm is the entry point - no validation or reviewer loop required. User explores freely.
