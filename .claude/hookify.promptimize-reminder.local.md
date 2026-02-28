---
name: promptimize-reminder
enabled: true
event: file
tool_matcher: Write|Edit
conditions:
  - field: file_path
    operator: regex_match
    pattern: plugins/iflow/(agents|skills|commands)/.*\.md$
action: warn
---

**Component file modified.** Consider running /iflow:promptimize to verify prompt quality.
