---
description: Complete a feature - merge, run retro, cleanup branch
argument-hint: [feature-id]
---

# /iflow:finish Command

Complete a feature and clean up.

## Determine Feature

Same logic as /iflow:show-status command.

## Pre-Completion Checks

1. **Check for uncommitted changes**
   - If found: "Uncommitted changes detected. Commit or stash first."

2. **Check tasks completion** (if tasks.md exists)
   - If incomplete tasks: "Warning: {n} tasks still incomplete. Continue? (y/n)"

3. **Suggest quality review** (for Standard/Full modes)
   - "Run quality review before completing? (y/n)"
   - If yes: Spawn quality-reviewer agent

4. **Offer documentation review**
   - Detect doc files (README.md, CHANGELOG.md, HISTORY.md, API.md, docs/*.md)
   - If any docs exist: "Documentation review? (y/n)"
   - If yes: Invoke `/iflow:update-docs` skill
   - If no: Continue to completion options
   - If no docs detected: Skip silently

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
→ Continue to Retrospective

### Option 2: Merge Locally

```bash
git checkout main
git merge feature/{id}-{slug}
git push
```

→ Continue to Retrospective

### Option 3: Keep Branch

Inform: "Branch kept. Run /iflow:finish again when ready to merge."
**Exit early** - no retrospective, no status update, no cleanup.

### Option 4: Discard/Abandon

Confirm: "This will mark the feature as abandoned. Are you sure? (y/n)"
→ Continue to Retrospective

## Run Retrospective (Required)

**For options 1, 2, and 4 only** (not option 3):

Automatically invoke the retrospecting skill:
- Gather data from feature folder
- Ask user about learnings
- User selects which learnings to keep
- Save to `docs/features/{id}-{slug}/retro.md`

This is **required**, not optional. The user controls what learnings to capture,
but the retrospective step always runs for terminal actions.

## Commit Retro Artifacts

If still on feature branch (options 1, 4):
```bash
git add docs/features/{id}-{slug}/retro.md
git commit -m "docs: add retrospective for feature {id}-{slug}"
```

For option 2 (already merged), retro.md goes directly to main.

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

## Branch Cleanup (for options 1, 2, 4)

For terminal statuses, delete the feature branch:

```bash
# After merge (option 2)
git branch -d feature/{id}-{slug}

# After PR creation (option 1) - keep branch until PR merged
# Branch will be deleted when PR is merged via GitHub

# After abandon (option 4)
git branch -D feature/{id}-{slug}
```

## Update State

If Vibe-Kanban:
- Move card to "Done" (completed) or "Archived" (abandoned)

## Final Output

```
✓ Feature {id}-{slug} {completed|abandoned}
✓ Retrospective saved to retro.md
✓ Branch cleaned up

Learnings captured in knowledge bank.
```
