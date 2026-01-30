# Brainstorm: Workflow Improvements - Retro & Worktree Switching

**Date:** 2026-01-30
**Topic:** Improve /finish ordering and add worktree switching capabilities

---

## Part 1: Retrospective Before Cleanup

### Problem

Current `/finish` command suggests retrospective AFTER:
- Merging/PR creation
- Worktree cleanup
- Branch deletion

By then, you've lost:
- Easy access to diff against main
- Isolated context for reflection
- Ability to re-examine decisions made during feature

### Solution

Move retrospective to happen BEFORE cleanup, and make it required (not suggested).

### Decisions Made

**1. Required vs Offered?**
- **Decision: Required, automatic**
- User chooses which learnings to keep
- Ensures learning capture happens
- Low friction since user controls output

**2. Before or After Merge Decision?**
- **Decision: After**
- Execute the merge/PR/abandon first
- Then retrospect on what was committed
- Then commit retro artifacts
- Then cleanup

**3. "Keep Branch" Option?**
- **Decision: Keep option, no retro for it**
- "Keep branch" = "not done yet"
- Retro only happens on terminal actions (PR, Merge, Discard)

### Refined /finish Flow

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

---

## Part 2: Worktree Switching

### Problem

Currently, switching worktrees is manual and tedious:
- Exit Claude → cd to worktree → restart Claude
- Or use absolute paths (verbose, git context wrong)
- Hook warns about mismatch but doesn't help fix it

### Solution

Add `/switch-worktree` command and integrate switching into existing workflows.

### Components

**1. New `/switch-worktree` command**
```
/switch-worktree [target]

Targets:
- Feature ID: /switch-worktree 006
- "main": /switch-worktree main
- No arg: list available and prompt
```

Implementation approach:
- Claude Code allows changing cwd via bash `cd`
- Command changes directory and confirms new context
- Re-runs session-start hook logic to show updated context

**2. Update `/create-feature` command**
- After worktree creation, ask: "Switch to worktree now? (y/n)"
- If yes: invoke `/switch-worktree {id}`
- If no: remind user how to switch later

**3. Update session-start hook**
- Current: warns about mismatch, suggests `cd`
- New: offer to switch via prompt
- "You're not in the feature worktree. Switch now? (y/n)"
- If yes: provide command to run or auto-switch

### Decisions

**How should switching work technically?**
- **Decision: Use bash cd** - working directory persists between commands
- Verify with `pwd` after switch
- Re-display context after switch

**Hook: Auto-switch or ask?**
- **Decision: Ask** - don't auto-switch, respect user's current location
- Some users may intentionally be in main repo

---

## Files to Modify

| File | Change |
|------|--------|
| `commands/finish.md` | Reorder: retro before cleanup, make required |
| `commands/switch-worktree.md` | **NEW** - worktree switching command |
| `commands/create-feature.md` | Add switch prompt after worktree creation |
| `hooks/session-start.sh` | Change warning to offer switch |

## Scope

Medium - 1 modified file, 1 new file, 2 updated files
