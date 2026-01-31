---
description: Alternative entry point - skip brainstorming and create feature directly
argument-hint: <feature-description>
---

# /iflow:create-feature Command

**Alternative entry point** for feature development. Use when you want to skip brainstorming.

Recommended flow: `/iflow:brainstorm` → (promotion) → `/iflow:specify` → ...
This command: `/iflow:create-feature` → `/iflow:specify` → ... (skips exploration)

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
- Inform: "Continuing to /iflow:specify..."
- Auto-invoke `/iflow:specify`

## Create Metadata File

Write to `docs/features/{id}-{slug}/.meta.json`:

```json
{
  "id": "{id}",
  "slug": "{slug}",
  "mode": "{selected-mode}",
  "status": "active",
  "created": "{ISO timestamp}",
  "branch": "feature/{id}-{slug}",
  "brainstorm_source": "{path-to-brainstorm-if-promoted}"
}
```

Note: `brainstorm_source` is only included when feature is promoted from a brainstorm.

## Handle Backlog Source

If feature was promoted from a brainstorm that originated from a backlog item:

1. **Read brainstorm content** from `brainstorm_source` path in context
2. **Parse for backlog source** using pattern `\*Source: Backlog #(\d{5})\*`
3. **If found:**
   - Add `"backlog_source": "{id}"` to `.meta.json`
   - Read `docs/backlog.md`
   - Find row matching `| {id} |`
   - Remove that row
   - Write updated backlog
   - Display: `Linked from backlog item #{id} (removed from backlog)`
4. **If pattern not found:** No action, continue normally
5. **If ID found but row missing:** Display warning `⚠️ Backlog item #{id} not found in docs/backlog.md`, continue with feature creation

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
  Linked from: Backlog #{backlog_id} (removed)  ← only if backlog source found

  Note: Skipped brainstorming. Proceeding to /iflow:specify.
```

## Auto-Continue

After creation, automatically invoke `/iflow:specify` skill.
