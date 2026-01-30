---
name: updating-docs
description: Guide user through documentation updates based on feature context. Use when completing a feature or when documentation might need updating.
---

# Updating Documentation

Guide documentation updates based on feature changes.

## Prerequisites

Check for context:
- Feature folder in `docs/features/` → Read spec.md for context
- No feature folder → Still useful, just detect docs without change analysis

This skill can be invoked:
- Directly via `/update-docs`
- From `/finish` when offered

## Process

### Step 1: Detect Documentation Files

Use detection spec from `references/detect-docs.md`:

```
Check for:
- README.md (project root)
- CHANGELOG.md (project root)
- HISTORY.md (project root)
- API.md (project root)
- docs/*.md (top-level only, no subdirectories)
```

Present findings:

```
Detected documentation files:
- README.md ✓
- CHANGELOG.md ✗
- docs/guide.md ✓
- docs/setup.md ✓
```

**If no docs found:** Report "No documentation files detected." and exit.

### Step 2: Analyze Feature Changes (if context available)

If spec.md exists, read the **In Scope** section and check for user-visible changes:

| Indicator | Example | Doc Impact |
|-----------|---------|------------|
| Adds new command/skill | "Create `/update-docs` skill" | README, CHANGELOG |
| Changes existing behavior | "Modify `/finish` to offer..." | README (if documented), CHANGELOG |
| Adds configuration option | "Add `--no-review` flag" | README, CHANGELOG |
| Changes user-facing output | "Show documentation suggestions" | CHANGELOG |
| Deprecates/removes feature | "Remove legacy mode" | README, CHANGELOG (breaking) |

**NOT user-visible** (no doc update suggested):
- Internal refactoring
- Performance improvements (unless >2x)
- Code quality improvements
- Test additions

### Step 3: Present Suggestions

Based on detected docs and change analysis:

```
Based on feature spec, these docs might need updates:

README.md
  → New skill added (/update-docs) - usage section may need update

CHANGELOG.md
  → Not present. Consider creating one for this new feature.

docs/guide.md
  → No user-visible changes affect this doc

Would you like to update any of these? (select)
```

If no user-visible changes detected:
```
No user-visible changes detected in spec.
Documentation updates are optional for this feature.

Still want to review documentation? (y/n)
```

### Step 4: Assist with Updates

For each doc the user selects:

1. **Read current content**
2. **Provide context** from the feature:
   - What changed (from spec.md In Scope)
   - Success criteria that might need documenting
   - Any new commands/options/behaviors

3. **Let user edit** - Do NOT auto-generate content
   - User controls tone, detail level, audience
   - Offer to help if asked, but don't write unprompted

4. **Confirm save** before moving to next doc

## Output

After all selected docs reviewed:

```
Documentation review complete.
- README.md: Updated
- CHANGELOG.md: Skipped

Continue with /finish? (y/n)
```

## Advisory, Not Blocking

This skill suggests but does not require updates:
- User can skip any or all suggestions
- User can update docs not suggested
- No enforcement or blocking behavior
