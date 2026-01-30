---
description: Start brainstorming - works with or without active feature
argument-hint: [topic or idea to explore]
---

Invoke the brainstorming skill.

Check docs/features/ for active feature:
- If found: Ask whether to add to existing feature or start new brainstorm
- If not found: Start standalone brainstorm (creates scratch file in docs/brainstorms/)

Follow brainstorming skill instructions for exploration and optional promotion to feature.

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
