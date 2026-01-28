---
name: using-git-worktrees
description: Creates isolated git worktrees with smart directory selection and safety verification. Use when starting feature work that needs isolation from current workspace.
---

# Using Git Worktrees

Git worktrees create isolated workspaces sharing the same repository.

## Directory Selection Priority

### 1. Check Existing Directories

```bash
ls -d .worktrees 2>/dev/null   # Preferred (hidden)
ls -d worktrees 2>/dev/null    # Alternative
```

If found, use that directory. If both exist, `.worktrees` wins.

### 2. Check CLAUDE.md

```bash
grep -i "worktree.*director" CLAUDE.md 2>/dev/null
```

If preference specified, use it.

### 3. Ask User

```
No worktree directory found. Where should I create worktrees?

1. .worktrees/ (project-local, hidden)
2. ~/worktrees/<project-name>/ (global location)
```

## Safety Verification

For project-local directories, verify ignored before creating:

```bash
git check-ignore -q .worktrees 2>/dev/null
```

**If NOT ignored:**
1. Add to .gitignore
2. Commit the change
3. Proceed with worktree creation

## Creation Steps

### 1. Detect Project Name

```bash
project=$(basename "$(git rev-parse --show-toplevel)")
```

### 2. Create Worktree

```bash
git worktree add "$path" -b "$BRANCH_NAME"
cd "$path"
```

### 3. Run Project Setup

```bash
# Auto-detect
[ -f package.json ] && npm install
[ -f Cargo.toml ] && cargo build
[ -f requirements.txt ] && pip install -r requirements.txt
[ -f go.mod ] && go mod download
```

### 4. Verify Clean Baseline

Run tests to ensure worktree starts clean.

**If tests fail:** Report failures, ask whether to proceed.
**If tests pass:** Report ready.

### 5. Report Location

```
Worktree ready at <full-path>
Tests passing (<N> tests, 0 failures)
Ready to implement <feature-name>
```

## Red Flags - Never

- Create worktree without verifying it's ignored
- Skip baseline test verification
- Proceed with failing tests without asking
- Assume directory location when ambiguous

## Integration

**Pairs with:**
- `finishing-branch` - Cleanup after work complete
