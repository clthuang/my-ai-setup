---
description: Wrap up implementation - review, retro, merge or PR
argument-hint: ""
---

# /iflow:wrap-up Command

Wrap up the current implementation with code review, retrospective, and merge/PR. This command is for work done outside the iflow feature workflow (e.g., after plan mode).

## Config Variables
Use these values from session context (injected at session start):
- `{iflow_base_branch}` — base branch for merges (default: `main`)
- `{iflow_release_script}` — path to release script (empty if not configured)

## YOLO Mode Overrides

If `[YOLO_MODE]` is active:
- Step 2a (tasks incomplete) → auto "Continue anyway"
- Step 2b (docs no update needed) → auto "Skip"
- Step 2b (docs updates found) → proceed with documentation-writer (no prompt needed)
- Phase 4 (completion decision) → auto "Merge & Release (Recommended)" (or "Merge (Recommended)" if `{iflow_release_script}` is not configured)
- **Git merge failure:** STOP and report. Do NOT attempt to resolve merge conflicts
  autonomously. Output: "YOLO MODE STOPPED: Merge conflict on {iflow_base_branch}. Resolve manually."

---

## Phase 1: Auto-Commit and Push

### Step 1a: Commit and Push

1. Check for uncommitted changes via `git status --short`
2. If uncommitted changes found:
   - `git add -A && git commit -m "wip: uncommitted changes before wrap-up"`
   - `git push`
   - On push failure: Show error and STOP - user must resolve manually
3. If no uncommitted changes: Continue

---

## Phase 2: Pre-Completion Reviews

### Step 2a: Check Task Completion

1. Call `TaskList` to get all tasks
2. Count pending/in_progress tasks
3. If no tasks exist: Continue (skip this step)

If incomplete tasks found:

```
AskUserQuestion:
  questions: [{
    "question": "{n} tasks still incomplete. How to proceed?",
    "header": "Tasks",
    "options": [
      {"label": "Continue anyway", "description": "Proceed despite incomplete tasks"},
      {"label": "Review and complete tasks first", "description": "Go back and finish remaining tasks"}
    ],
    "multiSelect": false
  }]
```

If "Review and complete tasks first": Show "Complete remaining tasks, then run /iflow:wrap-up again." → STOP

### Step 2b: Documentation Update (Automatic)

Run documentation update automatically using agents:

1. **Gather context from git:**
   - Run `git log --oneline -20` for recent commit messages
   - Run `git diff --stat HEAD~20` (or since branch divergence) for files changed

2. **Dispatch documentation-researcher agent:**

```
Task tool call:
  description: "Research documentation context"
  subagent_type: iflow:documentation-researcher
  model: sonnet
  prompt: |
    Research current documentation state for recent implementation work.

    Context:
    - Recent commits: {git log output}
    - Files changed: {git diff stat output}

    Find:
    - Existing docs that may need updates
    - What user-visible changes were made
    - What documentation patterns exist in project

    Return findings as structured JSON.
```

3. **Evaluate researcher findings:**

If `no_updates_needed: true`:

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

If "Skip": Continue to Phase 3.

4. **Dispatch documentation-writer agent:**

```
Task tool call:
  description: "Update documentation"
  subagent_type: iflow:documentation-writer
  model: sonnet
  prompt: |
    Update documentation based on research findings.

    Research findings: {JSON from researcher agent}

    Pay special attention to any `drift_detected` entries — these represent
    components that exist on the filesystem but are missing from README.md
    (or vice versa). Update README.md (root). If `plugins/iflow/README.md` exists (dev workspace), update it too.
    Add missing entries to the appropriate tables, remove stale entries,
    and correct component count headers.

    Also update CHANGELOG.md:
    - Add entries under the `## [Unreleased]` section
    - Use Keep a Changelog categories: Added, Changed, Fixed, Removed
    - Only include user-visible changes (new commands, skills, config options, behavior changes)
    - Skip internal refactoring, test additions, and code quality changes

    Write necessary documentation updates.
    Return summary of changes made.
```

5. **Commit documentation changes:**
```bash
git add -A
git commit -m "docs: update documentation"
git push
```

---

## Phase 3: Retrospective (Automatic)

### Step 3a: Run Retrospective

Dispatch retro-facilitator agent with lightweight context:

```
Task tool call:
  description: "Run retrospective"
  subagent_type: iflow:retro-facilitator
  model: opus
  prompt: |
    Run an AORTA retrospective on the recent implementation work.

    Context:
    - Recent commits: {git log --oneline -20}
    - Files changed: {git diff --stat summary}

    Analyze what went well, obstacles encountered, and learnings.
    Return structured findings.
```

If retro-facilitator fails, fall back to:
```
Task tool call:
  description: "Gather retrospective context"
  subagent_type: iflow:investigation-agent
  model: sonnet
  prompt: |
    Analyze the recent implementation work for learnings.
    - Recent commits: {git log}
    - Files changed: {list}
    Return key observations and learnings.
```

Store learnings directly via `store_memory` MCP tool (no retro.md file).

Commit if any changes were made.

### Step 3b: CLAUDE.md Update

Capture session learnings into project CLAUDE.md.

**Dependency:** Requires `claude-md-management` plugin (from claude-plugins-official marketplace).

1. **Invoke skill:**
   Invoke the `claude-md-management:revise-claude-md` skill via the Skill tool.

2. **If skill unavailable** (plugin not installed):
   Log "claude-md-management plugin not installed, skipping CLAUDE.md update." and continue to Phase 4.

3. **If changes made:**
   ```bash
   git add CLAUDE.md .claude.local.md 2>/dev/null
   git commit -m "chore: update CLAUDE.md with session learnings" --allow-empty
   git push
   ```

---

## Phase 4: Completion Decision

The option labels depend on whether `{iflow_release_script}` is configured:

```
AskUserQuestion:
  questions: [{
    "question": "Work complete. How would you like to finish?",
    "header": "Finish",
    "options": [
      {"label": "Merge & Release (Recommended)", "description": "Merge to {iflow_base_branch} and run release script"},
      // ↑ Use "Merge (Recommended)" and description "Merge to {iflow_base_branch}"
      //   if {iflow_release_script} is not configured
      {"label": "Create PR", "description": "Open pull request for team review"}
    ],
    "multiSelect": false
  }]
```

---

## Phase 5: Execute Selected Option

### Step 5a: Pre-Merge Validation

Before executing the selected option, discover and run project checks.

**Discovery** — scan in this order, collecting checks from all matching categories:

1. **CI/CD config**: Glob for `.github/workflows/*.yml`. For each file, grep for `run:` lines that reference local scripts or common commands (e.g. `./validate.sh`, `npm test`, `npm run lint`). Deduplicate against checks already collected.
2. **Validation script**: Check if `validate.sh` exists at the project root. If found, add `./validate.sh`.
3. **Package.json scripts**: If `package.json` exists, read it and look for scripts named `test`, `lint`, `check`, or `validate`. For each found, add `npm run {name}`.
4. **Makefile**: If `Makefile` exists, grep for targets named `check`, `test`, `lint`, or `validate`. For each found, add `make {target}`.

Deduplicate: if the same underlying command appears via multiple discovery paths, run it only once.

If **no checks discovered**: Log "No project checks found — skipping pre-merge validation." and proceed.

**Execution loop** (max 3 attempts):

1. Run all discovered checks sequentially.
2. If all pass → proceed to the selected option below.
3. If any check fails:
   - Analyze the failure output and attempt to fix the issues automatically.
   - Commit fixes: `git add -A && git commit -m "fix: address pre-merge validation failures"`.
   - Re-run all checks (counts as next attempt).
4. If checks still fail after 3 attempts, STOP and inform the user:

```
Pre-merge validation failed after 3 attempts.

Still failing:
- {check command}: {brief error summary}

Fix these issues manually, then run /iflow:wrap-up again.
```

Do NOT proceed to Create PR or Merge & Release if validation is failing.

### If "Create PR":

```bash
git push -u origin HEAD
gh pr create --title "{Brief summary from commits}" --body "## Summary
{Brief description from recent changes}

## Changes
{List of key changes}

## Testing
{Test instructions}"
```

Output: "PR created: {url}"
→ Continue to Phase 6

### If "Merge & Release" (or "Merge"):

```bash
# Merge to base branch
git checkout {iflow_base_branch}
git pull origin {iflow_base_branch}
git merge {current-branch}
git push
```

If `{iflow_release_script}` is set and the file exists at that path, run it:
```bash
{iflow_release_script}
```
Otherwise, skip the release step and output "No release script configured."

Output: "Merged to {iflow_base_branch}." followed by "Release: v{version}" if release script ran, or "No release script configured." if not.
→ Continue to Phase 6

---

## Phase 6: Cleanup

### Step 6a: Branch Cleanup

Determine current branch:
- If on `{iflow_base_branch}` or `main`: No branch cleanup needed
- If on a feature/topic branch:
  - After PR: Branch will be deleted when PR merged via GitHub
  - After Merge & Release: `git branch -d {branch-name}`

### Step 6b: Final Output

```
Work wrapped up successfully.
{PR created: {url} | Released v{version}}

Learnings captured via memory tools.
```
