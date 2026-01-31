---
description: Sync plugin source files to cache. Use when you've made changes to plugin files and want to apply them immediately.
---

# /iflow:sync-cache Command

Sync the iflow plugin source files to the Claude Code cache directory.

## Instructions

1. Run the sync script from the project source:
   ```bash
   ./plugins/iflow/hooks/sync-cache.sh
   ```

2. Report the result:
   - If successful: "Plugin cache synced successfully."
   - If failed: Report the error message.
