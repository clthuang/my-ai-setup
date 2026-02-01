---
description: List and delete old brainstorm scratch files
---

# /iflow:cleanup-brainstorms Command

Manage brainstorm scratch files in `docs/brainstorms/`.

## Process

### 1. List Files

List all files in `docs/brainstorms/` (exclude `.gitkeep`):

```
Brainstorm scratch files:

1. 20260129-143052-api-caching.md (today)
2. 20260128-091530-auth-rework.md (yesterday)
3. 20260115-220000-old-idea.md (14 days ago)

Total: 3 files
```

Calculate relative dates:
- Same day: "today"
- Yesterday: "yesterday"
- Within 7 days: "N days ago"
- Older: "N weeks ago" or date

### 2. Select Files to Delete

Ask user:
```
Enter numbers to delete (comma-separated), 'all' to delete all, or 'q' to quit:
```

### 3. Confirm Deletion

Show selected files and confirm via AskUserQuestion:
```
AskUserQuestion:
  questions: [{
    "question": "Will delete: {list of selected files}. Confirm?",
    "header": "Delete",
    "options": [
      {"label": "Yes, Delete", "description": "Remove selected files permanently"},
      {"label": "Cancel", "description": "Keep all files"}
    ],
    "multiSelect": false
  }]
```

### 4. Delete Files

If confirmed:
- Delete selected files
- Report: "Deleted 1 file."

If cancelled:
- Report: "Cancelled. No files deleted."

## Edge Cases

- No files found: "No brainstorm scratch files found."
- Invalid selection: "Invalid selection. Please enter valid numbers."
- File already deleted: Skip gracefully
