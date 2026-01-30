---
description: List all active features and their branches
---

# /list-features Command

List all active features.

## Gather Features

1. **Scan docs/features/** for feature folders
2. **Read .meta.json** from each to get branch info
3. **Determine status** from artifacts and metadata

## For Each Feature

Determine:
- ID and name
- Current phase (from artifacts)
- Branch name (from .meta.json)
- Last activity (file modification time)

## Display

```
Active Features:

ID   Name              Phase        Branch                          Last Activity
───  ────              ─────        ──────                          ─────────────
42   user-auth         design       feature/42-user-auth            2 hours ago
41   search-feature    implement    feature/41-search-feature       30 min ago
40   hotfix-login      complete     feature/40-hotfix-login         1 day ago

Commands:
  /show-status {id}        View feature details
  /create-feature          Start new feature
  git checkout {branch}    Switch to feature
```

## If No Features

```
No active features.

Run /create-feature "description" to start a new feature.
```
