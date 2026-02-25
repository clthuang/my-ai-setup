---
description: List all active features and their branches
---

# /iflow-dev:list-features Command

## Config Variables
Use these values from session context (injected at session start):
- `{iflow_artifacts_root}` — root directory for feature artifacts (default: `docs`)

List all active features.

## Gather Features

1. **Scan {iflow_artifacts_root}/features/** for feature folders
2. **Read .meta.json** from each to get branch info
3. **Determine status** from artifacts and metadata. Include features with `status: "planned"` in addition to active features.

## For Each Feature

Determine:
- ID and name
- Current phase (from artifacts, or `planned` if status is planned)
- Branch name (from .meta.json, or `—` if null)
- Project (from .meta.json `project_id`, or `—` if absent/null)
- Last activity (file modification time)

## Display

```
Active Features:

ID   Name              Phase        Branch                          Project    Last Activity
───  ────              ─────        ──────                          ───────    ─────────────
42   user-auth         design       feature/42-user-auth            P001       2 hours ago
43   data-models       planned      —                               P001       1 day ago
41   search-feature    implement    feature/41-search-feature       —          30 min ago
40   fix-login         complete     feature/40-fix-login            —          1 day ago

Commands:
  /iflow-dev:show-status {id}  View feature details
  /iflow-dev:create-feature    Start new feature
  git checkout {branch}    Switch to feature
```

## If No Features

```
No active features.

Run /iflow-dev:create-feature "description" to start a new feature.
```
