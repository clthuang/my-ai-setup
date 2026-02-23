---
name: promptimize
description: Reviews plugin prompts against best practices guidelines and returns scored assessment with improved version. Use when user says 'review this prompt', 'improve this skill', 'optimize this agent', 'promptimize', or 'check prompt quality'.
---

# Promptimize

Review and improve plugin component prompts using structured scoring and best practices.

## YOLO Mode Overrides

If `[YOLO_MODE]` is active in the execution context:

- **Step 8:** Auto-select "Accept all" (skip AskUserQuestion)

## Process

### Step 1: Detect component type

Identify the component type from the input path using **suffix-based matching** (the path CONTAINS the pattern, not an exact glob match -- this handles both absolute dev-workspace paths and cache paths):

| Path suffix pattern | Component type |
|---------------------|----------------|
| `skills/<name>/SKILL.md` | skill |
| `agents/<name>.md` | agent |
| `commands/<name>.md` | command |

Match rules:
1. Check if path contains `skills/` followed by a directory name and `/SKILL.md` --> type = **skill**
2. Check if path contains `agents/` followed by a filename ending in `.md` --> type = **agent**
3. Check if path contains `commands/` followed by a filename ending in `.md` --> type = **command**
4. No match --> display error: "Path must match: skills/*/SKILL.md, agents/*.md, or commands/*.md" --> **STOP**

### Step 2: Load references

Load three files using two-location Glob (try primary cache path first, fall back to dev workspace).

**2a. Scoring rubric**

- Primary: `~/.claude/plugins/cache/*/iflow*/*/skills/promptimize/references/scoring-rubric.md`
- Fallback (dev workspace): `plugins/*/skills/promptimize/references/scoring-rubric.md`

**2b. Prompt guidelines**

- Primary: `~/.claude/plugins/cache/*/iflow*/*/skills/promptimize/references/prompt-guidelines.md`
- Fallback (dev workspace): `plugins/*/skills/promptimize/references/prompt-guidelines.md`

**2c. Target file**

Read the file at the input path directly (absolute path provided by caller).

**Error handling:** If any reference file is not found after both Glob locations --> display error: "Required reference file not found: {filename}. Verify plugin installation." --> **STOP**

### Step 3: Check staleness

1. Parse the `## Last Updated: YYYY-MM-DD` heading from the prompt guidelines file
2. Compare the parsed date against today's date
3. If the date is **more than 30 days old**, set `staleness_warning = true`
4. This flag is used in Step 7 to append a staleness warning to the report

<!-- Steps 4-8 will be added in subsequent tasks -->
