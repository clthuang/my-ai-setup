---
name: warn-docs-sync
enabled: true
event: file
tool_matcher: Edit|Write|MultiEdit
conditions:
  - field: file_path
    operator: regex_match
    pattern: plugins/iflow-dev/(commands|skills|agents)/
action: warn
---

**Plugin component modified.** If you added, removed, or renamed a skill, command, or agent, update:
- `README.md` — user-facing tables
- `README_FOR_DEV.md` — developer lists and counts
- `plugins/iflow-dev/skills/workflow-state/SKILL.md` — Workflow Map (if phase sequence changed)
