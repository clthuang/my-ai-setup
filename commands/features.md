---
description: List all active features across worktrees
---

# /features Command

List all active features.

## Gather Features

1. **Scan docs/features/** for feature folders
2. **Scan git worktrees** for feature branches
3. **Cross-reference** to determine status

## For Each Feature

Determine:
- ID and name
- Current phase (from artifacts)
- Worktree path (if exists)
- Last activity (file modification time)

## Display

```
Active Features:

ID   Name              Phase        Worktree                    Last Activity
───  ────              ─────        ────────                    ─────────────
42   user-auth         design       ../project-42-user-auth     2 hours ago
41   search-feature    implement    ../project-41-search        30 min ago
40   hotfix-login      complete     (none)                      1 day ago

Commands:
  /status {id}     View feature details
  /feature         Start new feature
  cd {worktree}    Switch to feature
```

## If No Features

```
No active features.

Run /feature "description" to start a new feature.
```
