---
description: Create a project and invoke decomposition
argument-hint: --prd=<path>
---

# /iflow:create-project Command

Create a project from a PRD and invoke AI-driven decomposition into features.

## Step 1: Accept PRD

Receive `--prd={path}` argument (from brainstorm Stage 7 or standalone invocation).

If no `--prd` argument: ask user for PRD path via AskUserQuestion.

## Step 2: Validate PRD

1. Check PRD file exists at path
2. Check file is non-empty (> 100 bytes)
3. If validation fails: show error, stop

## Step 3: Derive Project ID

1. Scan `docs/projects/` for existing `P{NNN}-*` directories
2. Extract highest NNN, increment by 1
3. If no projects exist, start at P001
4. Zero-pad to 3 digits

## Step 4: Derive Slug

1. Extract title from PRD first heading (e.g., `# PRD: Feature Name` → `feature-name`)
2. Lowercase, replace spaces/special chars with hyphens, max 30 chars, trim trailing hyphens

## Step 5: Prompt Expected Lifetime

```
AskUserQuestion:
  questions: [{
    "question": "What is the expected project lifetime?",
    "header": "Lifetime",
    "options": [
      {"label": "3-months", "description": "Short-lived project"},
      {"label": "6-months", "description": "Medium-term project"},
      {"label": "1-year (Recommended)", "description": "Standard project lifetime"},
      {"label": "2-years", "description": "Long-lived project"}
    ],
    "multiSelect": false
  }]
```

## Step 6: Create Project Directory

1. Create `docs/projects/` if it doesn't exist
2. Create `docs/projects/P{NNN}-{slug}/`

## Step 7: Write Project .meta.json

```json
{
  "id": "P{NNN}",
  "slug": "{slug}",
  "status": "active",
  "expected_lifetime": "{selected lifetime}",
  "created": "{ISO timestamp}",
  "completed": null,
  "brainstorm_source": "{prd-path}",
  "milestones": [],
  "features": [],
  "lastCompletedMilestone": null
}
```

## Step 8: Copy PRD

1. Copy PRD content to `docs/projects/P{NNN}-{slug}/prd.md`
2. Verify copy: confirm destination file exists and is non-empty
3. If verification fails: show error, stop

## Step 9: Output

```
Project P{NNN}-{slug} created
  Lifetime: {expected_lifetime}
  Directory: docs/projects/P{NNN}-{slug}/
  PRD: Copied

Invoking decomposition...
```

## Step 10: Invoke Decomposition

Invoke the decomposing skill as inline continuation (not subprocess). Pass context:
- `project_dir`: `docs/projects/P{NNN}-{slug}/`
- `prd_content`: full PRD markdown text
- `expected_lifetime`: selected lifetime value

Follow the decomposing skill steps from this point forward.

## Error Handling

| Error | Action |
|-------|--------|
| PRD file not found | Show error with path, stop |
| PRD file empty | Show error, stop |
| PRD copy verification fails | Show error, stop |
| `docs/projects/` doesn't exist | Create it (Step 6) |
