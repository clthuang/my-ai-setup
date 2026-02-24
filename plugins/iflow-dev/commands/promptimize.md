---
description: Review a plugin prompt against best practices and return an improved version
argument-hint: "[file-path]"
---

# /iflow-dev:promptimize Command

## Input Flow

### Step 1: Check for direct path argument

If `$ARGUMENTS` contains a file path, skip to Step 3 (Delegate to skill).

### Step 2: Interactive component selection

If no arguments provided:

**2a. Select component type:**

```
AskUserQuestion:
  questions: [{
    "question": "What type of component would you like to review?",
    "header": "Component",
    "options": [
      {"label": "Skill", "description": "Review a skill SKILL.md file"},
      {"label": "Agent", "description": "Review an agent .md file"},
      {"label": "Command", "description": "Review a command .md file"}
    ],
    "multiSelect": false
  }]
```

**2b. Discover matching files using two-location Glob:**

Based on the selected component type, search for files:

- **Skill:**
  - Primary: `~/.claude/plugins/cache/*/iflow*/*/skills/*/SKILL.md`
  - Fallback (dev workspace): `plugins/*/skills/*/SKILL.md`

- **Agent:**
  - Primary: `~/.claude/plugins/cache/*/iflow*/*/agents/*.md`
  - Fallback (dev workspace): `plugins/*/agents/*.md`

- **Command:**
  - Primary: `~/.claude/plugins/cache/*/iflow*/*/commands/*.md`
  - Fallback (dev workspace): `plugins/*/commands/*.md`

Use the primary Glob first. If it returns zero results, use the fallback.

**2c. Handle empty results:**

If no files found from either location, display:

```
No {type} files found. Expected location: {glob pattern}. Verify plugin installation or check working directory.
```

Then STOP.

**2d. Present file selection:**

If `[YOLO_MODE]` is active, auto-select the first match (skip AskUserQuestion for file selection).

Otherwise, present matching files for user selection:

```
AskUserQuestion:
  questions: [{
    "question": "Which {type} would you like to review?",
    "header": "Select File",
    "options": [
      {"label": "{filename-1}", "description": "{full-path-1}"},
      {"label": "{filename-2}", "description": "{full-path-2}"}
    ],
    "multiSelect": false
  }]
```

List each discovered file as an option, using the filename as the label and the full path as the description.

### Step 3: Delegate to skill

The skill performs full path validation in its Step 1.

```
Skill(skill: "iflow-dev:promptimize", args: "<selected-path>")
```

Where `<selected-path>` is the file path from Step 2d (interactive) or `$ARGUMENTS` (direct).
