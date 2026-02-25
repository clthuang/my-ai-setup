---
description: Show workspace dashboard with features, branches, and brainstorms
---

# /iflow-dev:show-status Command

## Config Variables
Use these values from session context (injected at session start):
- `{iflow_artifacts_root}` — root directory for feature artifacts (default: `docs`)
- `{iflow_base_branch}` — base branch for the project (default: `main`)

Display a workspace dashboard with current context, open features, and brainstorms.

## Section 1: Current Context

Gather via git and file inspection:

1. **Current branch**: Run `git rev-parse --abbrev-ref HEAD`
2. **Current feature**: If branch matches `feature/{id}-{slug}`, read `{iflow_artifacts_root}/features/{id}-{slug}/.meta.json` to get feature name and determine current phase (first missing artifact from: spec.md, design.md, plan.md, tasks.md — or "implement" if all exist). Show "None" if not on a feature branch.
3. **Other branches**: Run `git branch` and list all local branches except the current one. Show "None" if only one branch exists.

## Section 1.5: Project Features

Scan `{iflow_artifacts_root}/features/` for folders containing `.meta.json` where `project_id` is present and non-null.

If any project-linked features found:
1. Group features by `project_id`
2. For each project_id:
   a. Resolve project directory via glob `{iflow_artifacts_root}/projects/{project_id}-*/`
   b. Read project `.meta.json` to get slug
   c. Display heading: `## Project: {project_id}-{slug}`
   d. List all features for that project as bullets: `- {id}-{slug} ({status}[, phase: {phase}])` — include ALL statuses (planned, active, completed, abandoned)

If no project-linked features, omit this section entirely.

## Section 2: Open Features

Scan `{iflow_artifacts_root}/features/` for folders containing `.meta.json` where status is NOT `"completed"` AND `project_id` is either absent or null. This excludes project-linked features (shown in Section 1.5) and completed standalone features.

For each open feature, show:
- **ID**: from `.meta.json`
- **Name**: the slug from `.meta.json`
- **Phase**: determined from first missing artifact (spec.md, design.md, plan.md, tasks.md) or "implement" if all exist
- **Branch**: from `.meta.json`

If no open features exist, show "None".

## Section 3: Open Brainstorms

List files in `{iflow_artifacts_root}/brainstorms/` excluding `.gitkeep`. For each file, show:
- Filename
- Age (e.g., "1 day ago", "3 days ago") based on file modification time

If no brainstorm files exist, show "None".

## Display Format

When on a feature branch:

```
## Current Context
Branch: feature/018-show-status-upgrade
Feature: 018-show-status-upgrade (phase: design)
Other branches: main, {iflow_base_branch}

## Project: P001-crypto-tracker
- 021-auth (active, phase: design)
- 022-data-models (planned)
- 023-dashboard (planned)

## Open Features
ID   Name                    Phase        Branch
018  show-status-upgrade     design       feature/018-show-status-upgrade
016  api-refactor            implement    feature/016-api-refactor

## Open Brainstorms
20260205-002937-rca-agent.prd.md (1 day ago)
20260204-secretary-agent.prd.md (2 days ago)

Next: Run /iflow-dev:design to continue
```

When not on a feature branch:

```
## Current Context
Branch: {iflow_base_branch}
Feature: None
Other branches: main

## Open Features
None

## Open Brainstorms
20260205-002937-rca-agent.prd.md (1 day ago)

Tip: Run /iflow-dev:create-feature or /iflow-dev:brainstorm to start
```

## Footer Logic

- If on a feature branch with a detected phase, show: `Next: Run /iflow-dev:{next-command} to continue` where `{next-command}` is the command for the current phase (e.g., design, create-plan, create-tasks, implement).
- If not on a feature branch, show: `Tip: Run /iflow-dev:create-feature or /iflow-dev:brainstorm to start`
