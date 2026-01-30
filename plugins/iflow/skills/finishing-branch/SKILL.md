---
name: finishing-branch
description: Guides branch completion with structured options for merge, PR, keep, or discard. Use when implementation is complete and ready to integrate.
---

# Finishing a Development Branch

Guide completion of development work with clear options.

## Core Principle

Verify tests → Present options → Execute choice → Clean up branch.

## The Process

### Step 1: Verify Tests

```bash
# Run project's test suite
npm test / cargo test / pytest / go test ./...
```

**If tests fail:** Stop. Cannot proceed until tests pass.

**If tests pass:** Continue to Step 2.

### Step 2: Present Options

Present exactly these 4 options:

```
Implementation complete. What would you like to do?

1. Merge back to <base-branch> locally
2. Push and create a Pull Request
3. Keep the branch as-is (I'll handle it later)
4. Discard this work

Which option?
```

### Step 3: Execute Choice

**Option 1: Merge Locally**
```bash
git checkout <base-branch>
git pull
git merge <feature-branch>
# Verify tests on merged result
git branch -d <feature-branch>
```

**Option 2: Push and Create PR**
```bash
git push -u origin <feature-branch>
gh pr create --title "<title>" --body "..."
```
Note: Branch will be deleted when PR is merged via GitHub.

**Option 3: Keep As-Is**
Report: "Keeping branch for later."
Don't delete branch.

**Option 4: Discard**
Confirm first:
```
This will permanently delete branch and all commits.
Type 'discard' to confirm.
```
If confirmed:
```bash
git checkout <base-branch>
git branch -D <feature-branch>
```

## Quick Reference

| Option | Merge | Push | Delete Branch |
|--------|-------|------|---------------|
| 1. Merge locally | ✓ | - | ✓ (after merge) |
| 2. Create PR | - | ✓ | - (GitHub deletes) |
| 3. Keep as-is | - | - | - |
| 4. Discard | - | - | ✓ (force) |

## Red Flags - Never

- Proceed with failing tests
- Merge without verifying tests on result
- Delete work without confirmation
- Force-push without explicit request
