---
description: Alternative entry point - skip brainstorming and create feature directly
argument-hint: <feature-description>
---

# /create-feature Command

**Alternative entry point** for feature development. Use when you want to skip brainstorming.

Recommended flow: `/brainstorm` → (promotion) → `/specify` → ...
This command: `/create-feature` → `/specify` → ... (skips exploration)

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
- Skip worktree creation entirely
- Set `.meta.json`: `"worktree": null`
- Inform: "Hotfix mode. Skipped brainstorming. Run /implement when ready."

### For Quick Mode
- Create folder: `docs/features/{id}-{slug}/`
- Ask user: "Create isolated worktree for this feature? (y/n)"
- If user declines: Set `.meta.json`: `"worktree": null`
- If user confirms: Execute worktree creation steps below
- Inform: "Quick mode. Skipped brainstorming. Continuing to /specify..."
- Auto-invoke `/specify`

### For Standard/Full Mode
- Create folder: `docs/features/{id}-{slug}/`
- Automatically create worktree (no user prompt)
- Execute worktree creation steps below
- Inform: "Created worktree at ../{project}-{id}-{slug}"
- Inform: "Skipped brainstorming. Continuing to /specify..."
- Auto-invoke `/specify`

### Worktree Creation Steps

Execute these commands when creating a worktree:

```bash
# 1. Verify we're in a git repository
git rev-parse --git-dir

# 2. Get project name from current directory
project_name=$(basename $(pwd))

# 3. Create worktree with new branch
git worktree add "../${project_name}-${feature_id}-${slug}" -b "feature/${feature_id}-${slug}"

# 4. Verify creation succeeded
ls -la "../${project_name}-${feature_id}-${slug}"
```

**After successful creation:**
- Store path in `.meta.json`: `"worktree": "../{project}-{id}-{slug}"`
- Inform user: "Worktree created at ../{path}. Consider: cd ../{path}"

**If creation fails:**
- Set `.meta.json`: `"worktree": null`
- Warn user: "Failed to create worktree: {error}. Continuing without isolation."

## Create Metadata File

Write to `docs/features/{id}-{slug}/.meta.json`:

```json
{
  "id": "{id}",
  "name": "{slug}",
  "mode": "{selected-mode}",
  "created": "{ISO timestamp}",
  "worktree": "{path or null}"
}
```

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

  Note: Skipped brainstorming. Proceeding to /specify.
```

## Auto-Continue

After creation (except Hotfix), automatically invoke `/specify` skill.
