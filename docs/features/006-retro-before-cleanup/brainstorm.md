# Brainstorm: Retrospective Before Cleanup

**Date:** 2026-01-30
**Topic:** Change /finish ordering so retrospective happens before worktree cleanup

## Problem

Current `/finish` command suggests retrospective AFTER:
- Merging/PR creation
- Worktree cleanup
- Branch deletion

By then, you've lost:
- Easy access to diff against main
- Isolated context for reflection
- Ability to re-examine decisions made during feature

## Solution

Move retrospective to happen BEFORE cleanup, and make it required (not suggested).

## Decisions Made

### 1. Required vs Offered?
**Decision: Required, automatic**
- User chooses which learnings to keep
- Ensures learning capture happens
- Low friction since user controls output

### 2. Before or After Merge Decision?
**Decision: After**
- Execute the merge/PR/abandon first
- Then retrospect on what was committed
- Then commit retro artifacts
- Then cleanup

### 3. "Keep Branch" Option?
**Decision: Keep option, no retro for it**
- "Keep branch" = "not done yet"
- Retro only happens on terminal actions (PR, Merge, Discard)
- When user runs `/finish` again and completes, retro happens then

## Refined Flow

```
/finish
├── Pre-completion checks
├── Completion choice: PR / Merge / Keep / Discard
│
├── If "Keep": exit early (no retro, no cleanup)
│
├── Execute choice (merge/PR/abandon)
├── RETROSPECTIVE (required, automatic)
│   └── User selects which learnings to keep
├── Commit retro artifacts
├── Update .meta.json
└── Worktree cleanup
```

## Files to Modify

- `commands/finish.md` - Reorder sections, make retro required

## Scope

Small, focused change. ~10 lines in one file.
