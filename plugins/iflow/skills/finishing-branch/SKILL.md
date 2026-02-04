---
name: finishing-branch
description: This skill should be used when the user says 'finish the branch', 'merge to main', 'create PR', or 'complete the feature'. Guides branch completion with PR or merge options.
---

# Finishing a Development Branch

Guide completion of development work with streamlined options.

## Base Branch

The default base branch is `develop`. Feature branches merge to `develop`, not `main`.

Releases from `develop` to `main` are handled by `scripts/release.sh`.

## Core Principle

Commit changes → Present options → Execute choice → Clean up branch.

## The Process

### Step 1: Verify Clean State

Ensure all changes are committed:
```bash
git status --short
```

If uncommitted changes exist, commit them first:
```bash
git add -A && git commit -m "wip: uncommitted changes before finish"
git push
```

### Step 2: Present Options

Present exactly 2 options via AskUserQuestion:

```
AskUserQuestion:
  questions: [{
    "question": "Implementation complete. How would you like to proceed?",
    "header": "Finish",
    "options": [
      {"label": "Create PR", "description": "Open pull request for team review"},
      {"label": "Merge & Release", "description": "Merge to develop and run release script"}
    ],
    "multiSelect": false
  }]
```

### Step 3: Execute Choice

**Option 1: Create PR**
```bash
git push -u origin {feature-branch}
gh pr create --title "{title}" --body "..."
```
Output: "PR created: {url}"
Note: Branch will be deleted when PR is merged via GitHub.

**Option 2: Merge & Release**
```bash
# Merge to develop
git checkout develop
git pull origin develop
git merge {feature-branch}
git push

# Run release script
./scripts/release.sh

# Delete feature branch
git branch -d {feature-branch}
```
Output: "Merged to develop. Released v{version}"

## Quick Reference

| Option | Merge | Push | Release | Delete Branch |
|--------|-------|------|---------|---------------|
| Create PR | - | Yes | - | GitHub deletes on merge |
| Merge & Release | Yes | Yes | Yes | Yes (local) |

## Red Flags - Never

- Force-push without explicit request
- Delete work without confirmation
- Skip the release script on Merge & Release option
