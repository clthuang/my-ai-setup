---
description: Complete a feature - merge, cleanup worktree, suggest retro
argument-hint: [feature-id]
---

# /finish Command

Complete a feature and clean up.

## Determine Feature

Same logic as /status command.

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

How would you like to merge?
1. Create PR (recommended for team projects)
2. Merge to main locally
3. Keep branch (don't merge yet)
```

### Option 1: Create PR

```bash
git push -u origin feature/{id}-{slug}
gh pr create --title "Feature: {slug}" --body "..."
```

Inform: "PR created: {url}"

### Option 2: Merge Locally

```bash
git checkout main
git merge feature/{id}-{slug}
git push
```

### Option 3: Keep Branch

Inform: "Branch kept. Run /finish again when ready to merge."
Skip cleanup.

## Cleanup (for options 1 & 2)

If worktree exists:
```bash
cd {original-repo}
git worktree remove ../{project}-{id}-{slug}
git branch -d feature/{id}-{slug}  # after merge
```

## Update State

If Vibe-Kanban:
- Move card to "Done"

## Suggest Retrospective

```
✓ Feature {id}-{slug} completed

Capture learnings? This helps improve future work.
Run /retro to reflect on this feature.
```
