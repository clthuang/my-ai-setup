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
| Most features, clear scope | Standard |
| "rewrite", "refactor system", "breaking change" | Full |

Present to user:
```
Feature: {id}-{slug}
Suggested mode: {mode}

Modes:
1. Standard — all phases (default)
2. Full — all phases, required verification

Choose mode [1-2] or press Enter for {suggested}:
```

## Create Feature

### For All Modes

1. Create folder: `docs/features/{id}-{slug}/`
2. Create feature branch:
   ```bash
   git checkout -b feature/{id}-{slug}
   ```
3. Create `.meta.json` (see below)

### Mode-Specific Behavior

**Standard/Full:**
- Inform: "Created branch feature/{id}-{slug}."
- Inform: "Continuing to /specify..."
- Auto-invoke `/specify`

## Create Metadata File

Write to `docs/features/{id}-{slug}/.meta.json`:

```json
{
  "id": "{id}",
  "slug": "{slug}",
  "mode": "{selected-mode}",
  "status": "active",
  "created": "{ISO timestamp}",
  "branch": "feature/{id}-{slug}"
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
  Branch: feature/{id}-{slug}

  Note: Skipped brainstorming. Proceeding to /specify.
```

## Auto-Continue

After creation, automatically invoke `/specify` skill.
