---
name: secretary-routing-guard
enabled: true
event: prompt
conditions:
  - field: user_prompt
    operator: regex_match
    pattern: /(?:iflow(?:-dev)?:)?secretary\s+(?!help\b|mode\b|orchestrate\b|continue\b)\S
action: warn
---

**Secretary routing constraint.** You MUST dispatch this request to the `iflow-dev:secretary` agent via Task tool. Do NOT explore the codebase, answer the request, or do the work yourself. Read config, call Task, present results.
