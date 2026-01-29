---
description: Complete a feature - merge, cleanup worktree, suggest retro
argument-hint: [feature-id]
---

# /finish Command

Complete a feature and clean up.

## Determine Feature

Same logic as /show-status command.

## Pre-Completion Checks

1. **Check for uncommitted changes**
   - If found: "Uncommitted changes detected. Commit or stash first."

2. **Check tasks completion** (if tasks.md exists)
   - If incomplete tasks: "Warning: {n} tasks still incomplete. Continue? (y/n)"

3. **Suggest quality review** (for Standard/Full modes)
   - "Run quality review before completing? (y/n)"
   - If yes: Spawn quality-reviewer agent

## Completion Options

```
Feature {id}-{slug} ready to complete.

How would you like to finish?
1. Create PR (recommended for team projects)
2. Merge to main locally
3. Keep branch (don't merge yet)
4. Discard/abandon feature
```

### Option 1: Create PR

```bash
git push -u origin feature/{id}-{slug}
gh pr create --title "Feature: {slug}" --body "..."
```

Inform: "PR created: {url}"
→ Update status to "completed"

### Option 2: Merge Locally

```bash
git checkout main
git merge feature/{id}-{slug}
git push
```

→ Update status to "completed"

### Option 3: Keep Branch

Inform: "Branch kept. Run /finish again when ready to merge."
Skip cleanup and status update.

### Option 4: Discard/Abandon

Confirm: "This will mark the feature as abandoned. Are you sure? (y/n)"
→ Update status to "abandoned"

## Update Feature Status

For options 1, 2, or 4, update `.meta.json`:

**For completed (options 1, 2):**
```json
{
  "status": "completed",
  "completed": "{ISO timestamp}"
}
```

**For abandoned (option 4):**
```json
{
  "status": "abandoned",
  "completed": "{ISO timestamp}"
}
```

Note: `completed` and `abandoned` are terminal statuses. They cannot be changed. New work requires a new feature.

## Review History Cleanup

Delete `.review-history.md` from the feature folder:
- History served its purpose during development
- Git has the permanent record
- Avoids clutter in completed features

```bash
rm docs/features/{id}-{slug}/.review-history.md
```

## Worktree Cleanup (for options 1, 2, 4)

If worktree exists and status is terminal:
```bash
cd {original-repo}
git worktree remove ../{project}-{id}-{slug}
git branch -d feature/{id}-{slug}  # after merge, or -D for abandon
```

## Update State

If Vibe-Kanban:
- Move card to "Done" (completed) or "Archived" (abandoned)

## Suggest Retrospective

```
✓ Feature {id}-{slug} {completed|abandoned}

Capture learnings? This helps improve future work.
Run /retrospect to reflect on this feature.
```
