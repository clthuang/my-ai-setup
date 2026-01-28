---
description: Start a new feature with folder structure and optional worktree
argument-hint: <feature-description>
---

# /feature Command

Start a new feature development workflow.

## Gather Information

1. **Get feature description** from argument or ask user
2. **Determine feature ID**: Find highest number in `docs/features/` and add 1
3. **Create slug** from description (lowercase, hyphens, max 30 chars)

## Suggest Workflow Mode

Based on described scope, suggest a mode:

| Scope | Suggested Mode |
|-------|----------------|
| "fix typo", "quick fix", single file | Hotfix |
| "add button", "small feature", clear scope | Quick |
| Most features | Standard |
| "rewrite", "refactor system", "breaking change" | Full |

Present to user:
```
Feature: {id}-{slug}
Suggested mode: {mode}

Modes:
1. Hotfix — implement only, no worktree
2. Quick — spec → tasks → implement, optional worktree
3. Standard — all phases, recommended worktree
4. Full — all phases, required worktree, required verification

Choose mode [1-4] or press Enter for {suggested}:
```

## Create Feature

### For Hotfix Mode
- Create folder: `docs/features/{id}-{slug}/`
- No worktree
- Inform: "Hotfix mode. Run /implement when ready."

### For Quick Mode
- Create folder: `docs/features/{id}-{slug}/`
- Ask: "Create worktree? (y/n)"
- If yes: `git worktree add ../{project}-{id}-{slug} -b feature/{id}-{slug}`
- Inform: "Quick mode. Run /spec to start."

### For Standard/Full Mode
- Create folder: `docs/features/{id}-{slug}/`
- Create worktree: `git worktree add ../{project}-{id}-{slug} -b feature/{id}-{slug}`
- Inform: "Created worktree at ../{project}-{id}-{slug}"
- Inform: "Standard mode. Run /brainstorm to start."

## State Tracking

If Vibe-Kanban available:
- Create card with feature name
- Set status to "New"

Otherwise:
- Use TodoWrite to track feature

## Output

```
✓ Feature {id}-{slug} created
  Mode: {mode}
  Folder: docs/features/{id}-{slug}/
  Worktree: ../{project}-{id}-{slug} (if created)

  Next: Run /{next-phase} to begin
```
