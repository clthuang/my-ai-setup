---
name: updating-docs
description: Automatically updates documentation using agents. Use when the user says 'update docs', 'sync documentation', or when completing a feature.
---

# Updating Documentation

Automatic documentation updates using documentation-researcher and documentation-writer agents.

## Config Variables
Use these values from session context (injected at session start):
- `{iflow_artifacts_root}` — root directory for feature artifacts (default: `docs`)

## Prerequisites

- Feature folder in `{iflow_artifacts_root}/features/` with spec.md for context
- This skill is invoked automatically from `/iflow:finish-feature`

## Process

### Step 1: Dispatch Documentation Researcher

```
Task tool call:
  description: "Research documentation context"
  subagent_type: iflow:documentation-researcher
  model: sonnet
  prompt: |
    Research current documentation state for feature {id}-{slug}.

    Feature context:
    - spec.md: {content summary}
    - Files changed: {list from git diff}

    Find:
    - Existing docs that may need updates
    - What user-visible changes were made
    - What documentation patterns exist in project
    - Ground truth drift: detect project type and run the appropriate drift detection strategy

    Return findings as structured JSON.
```

### Step 2: Evaluate Findings

Check researcher output:

**If `no_updates_needed: true`:**

```
AskUserQuestion:
  questions: [{
    "question": "No user-visible changes detected. Skip documentation?",
    "header": "Docs",
    "options": [
      {"label": "Skip", "description": "No documentation updates needed"},
      {"label": "Write anyway", "description": "Force documentation update"}
    ],
    "multiSelect": false
  }]
```

If "Skip": Exit skill - no documentation updates.

### Step 3: Dispatch Documentation Writer

If updates needed:

```
Task tool call:
  description: "Update documentation"
  subagent_type: iflow:documentation-writer
  model: sonnet
  prompt: |
    Update documentation based on research findings.

    Feature: {id}-{slug}
    Research findings: {JSON from researcher agent}

    Pay special attention to any `drift_detected` entries — these represent
    documented items that don't match the filesystem (or vice versa).
    Update the affected documentation files. Add missing entries,
    remove stale entries, and correct any count headers.

    Also update CHANGELOG.md:
    - Add entries under the `## [Unreleased]` section
    - Use Keep a Changelog categories: Added, Changed, Fixed, Removed
    - Only include user-visible changes (new commands, skills, config options, behavior changes)
    - Skip internal refactoring, test additions, and code quality changes

    Write necessary documentation updates.
    Return summary of changes made.
```

### Step 4: Report Results

Show summary from documentation-writer:

```
Documentation updated:
- README.md: Added /finish command to commands table
- {Other updates...}
```

## What Gets Documented

| Change Type | Documentation Impact |
|-------------|---------------------|
| New command/skill | README commands table, CHANGELOG |
| Changed behavior | README (if documented), CHANGELOG |
| New config option | README, CHANGELOG |
| User-facing output change | CHANGELOG |
| Deprecated/removed feature | README, CHANGELOG (breaking) |

## What Does NOT Get Documented

- Internal refactoring
- Performance improvements (unless >2x)
- Code quality improvements
- Test additions

## Advisory, Not Blocking

This skill suggests but does not require updates:
- User can skip if no user-visible changes
- Agents determine what needs updating
- No enforcement or blocking behavior
