# Specification: Workflow Improvements - Retro & Worktree Switching

## Problem Statement

Two related workflow issues:

1. **Retrospective timing**: The `/finish` command suggests running retrospective AFTER worktree cleanup, when context is lost. By then, you can't easily diff against main or examine decisions made during the feature.

2. **Worktree switching friction**: When working with git worktrees, switching between them requires exiting Claude, changing directory, and restarting. The session-start hook warns about being in the wrong worktree but doesn't help fix it.

## Goals

1. Move retrospective to happen before worktree cleanup (while context exists)
2. Make retrospective required for completed features (user controls what to keep)
3. Add `/switch-worktree` command for easy worktree navigation
4. Integrate worktree switching prompts into existing workflows

## Non-Goals

- Auto-switching worktrees without user consent
- Managing worktrees for other projects
- Bare repository workflow migration

## Requirements

### R1: Retrospective Before Cleanup

The `/finish` command MUST run retrospective before worktree cleanup:

```
/finish
├── Pre-completion checks
├── Completion choice: PR / Merge / Keep / Discard
│
├── If "Keep": exit early (no changes)
│
├── Execute choice (merge/PR/abandon)
├── RETROSPECTIVE (required)
│   └── Invoke retrospecting skill
│   └── User selects which learnings to keep
├── Commit retro artifacts to feature branch
├── Update .meta.json status
└── Worktree cleanup (remove worktree, delete branch)
```

### R2: Retrospective is Required

- Retrospective MUST run automatically for terminal actions (PR, Merge, Discard)
- User MUST NOT be asked "want to run retro?" - it just happens
- User controls which learnings to keep (interactive selection)
- Retro artifacts saved to `docs/features/{id}-{slug}/retro.md`

### R3: Keep Branch Skips Retro

- "Keep branch" option exits early
- No retrospective (feature not complete)
- No status update
- No cleanup
- User runs `/finish` again when ready

### R4: Switch Worktree Command

New command `/switch-worktree`:

```
/switch-worktree [target]
```

**Targets:**
- Feature ID: `/switch-worktree 006` → switches to feature 006's worktree
- Feature slug: `/switch-worktree retro-before-cleanup` → same
- `main`: `/switch-worktree main` → switches to main repository
- No argument: list available worktrees and prompt for selection

**Behavior:**
1. Resolve target to directory path
2. Execute `cd {path}` via bash
3. Verify with `pwd`
4. Display updated context (feature, phase, next command)

**Error handling:**
- Target not found: "No worktree found for '{target}'. Available: ..."
- Directory doesn't exist: "Worktree directory missing. Run `git worktree list` to diagnose."

### R5: Create Feature Offers Switch

After `/create-feature` creates a worktree:

```
✓ Feature {id}-{slug} created
  Worktree: ../{project}-{id}-{slug}

Switch to worktree now?
1. Yes (recommended)
2. No, stay here
```

- If yes: invoke `/switch-worktree {id}`
- If no: continue in current directory

### R6: Session Start Hook Offers Switch

When session-start hook detects worktree mismatch:

**Current behavior:**
```
⚠️  WARNING: You are not in the feature worktree.
   Current directory: /path/to/main
   Feature worktree: ../my-ai-setup-006-retro
   Consider: cd ../my-ai-setup-006-retro
```

**New behavior:**
```
⚠️  You're not in the feature worktree.
   Current: /path/to/main
   Feature: ../my-ai-setup-006-retro

   Run /switch-worktree 006 to switch, or continue here.
```

- Hook does NOT auto-switch
- Hook suggests the command to run
- User decides whether to switch

### R7: List Worktrees

`/switch-worktree` with no argument lists available targets:

```
Available worktrees:

  main     /Users/terry/projects/my-ai-setup (current)
  001      ../my-ai-setup-001-kanban-task-visualisation
  006      ../my-ai-setup-006-retro-before-cleanup

Switch to: [id/main]
```

## Acceptance Criteria

- [ ] `/finish` runs retrospective before cleanup for PR/Merge/Discard
- [ ] Retrospective runs automatically (no "want to run?" prompt)
- [ ] "Keep branch" exits without retro or cleanup
- [ ] Retro artifacts committed before worktree removal
- [ ] `/switch-worktree 006` changes cwd to feature 006 worktree
- [ ] `/switch-worktree main` changes cwd to main repo
- [ ] `/switch-worktree` (no arg) lists worktrees and prompts
- [ ] Context displayed after switch (feature, phase, next command)
- [ ] `/create-feature` asks to switch after worktree creation
- [ ] Session-start hook suggests `/switch-worktree` instead of `cd`

## Files to Modify

| Action | File | Description |
|--------|------|-------------|
| Modify | `commands/finish.md` | Reorder: retro before cleanup, make required |
| Create | `commands/switch-worktree.md` | New worktree switching command |
| Modify | `commands/create-feature.md` | Add switch prompt after creation |
| Modify | `hooks/session-start.sh` | Suggest switch command instead of cd |

## Open Questions

None - all decisions made during brainstorming.
