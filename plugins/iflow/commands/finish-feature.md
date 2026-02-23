---
description: Complete a feature - merge, run retro, cleanup branch
argument-hint: [feature-id]
---

# /iflow:finish-feature Command

Complete a feature and clean up.

## YOLO Mode Overrides

If `[YOLO_MODE]` is active:
- Step 2a (tasks incomplete) → auto "Continue anyway"
- Step 2b (docs no update needed AND `changelog_state.needs_entry` is false) → auto "Skip"
- Step 2b (docs no update needed BUT `changelog_state.needs_entry` is true) → proceed with documentation-writer for CHANGELOG only
- Step 2b (docs updates found) → proceed with documentation-writer (no prompt needed)
- Phase 4 (completion decision) → auto "Merge & Release (Recommended)"
- **Git merge failure:** STOP and report. Do NOT attempt to resolve merge conflicts
  autonomously. Output: "YOLO MODE STOPPED: Merge conflict on develop. Resolve manually,
  then run /secretary continue"

## Determine Feature

Same logic as /iflow:show-status command.

---

## Phase 1: Auto-Commit (with Branch/Phase Checks)

### Steps 1a-1c: Branch Check, Partial Recovery, Mark Started

Follow `validateAndSetup("finish")` from the **workflow-transitions** skill (skip transition validation since finish has no hard prerequisites).

### Step 1d: Commit and Push

1. Check for uncommitted changes via `git status --short`
2. If uncommitted changes found:
   - `git add -A && git commit -m "wip: uncommitted changes before finish"`
   - `git push`
   - On push failure: Show error and STOP - user must resolve manually
3. If no uncommitted changes: Continue

---

## Phase 2: Pre-Completion Reviews

### Step 2a: Check Tasks Completion

If `tasks.md` exists, check for incomplete tasks (unchecked `- [ ]` items).

If incomplete tasks found:

```
AskUserQuestion:
  questions: [{
    "question": "{n} tasks still incomplete. How to proceed?",
    "header": "Tasks",
    "options": [
      {"label": "Continue anyway", "description": "Proceed despite incomplete tasks"},
      {"label": "Run /iflow:implement", "description": "Execute implementation once more"},
      {"label": "Run /iflow:implement until done", "description": "Loop until all tasks complete"}
    ],
    "multiSelect": false
  }]
```

If "Run /iflow:implement": Execute `/iflow:implement`, then return to Phase 2.
If "Run /iflow:implement until done": Loop `/iflow:implement` until no incomplete tasks, then continue.

### Step 2b: Documentation Update (Automatic)

Run documentation update automatically using agents:

1. **Dispatch documentation-researcher agent:**

```
Task tool call:
  description: "Research documentation context"
  subagent_type: iflow:documentation-researcher
  prompt: |
    Research current documentation state for feature {id}-{slug}.

    Feature context:
    - spec.md: {content summary}
    - Files changed: {list from git diff}

    Find:
    - Existing docs that may need updates
    - What user-visible changes were made
    - What documentation patterns exist in project

    Return findings as structured JSON.
```

2. **Evaluate researcher findings:**

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

3. **Dispatch documentation-writer agent:**

```
Task tool call:
  description: "Update documentation"
  subagent_type: iflow:documentation-writer
  prompt: |
    Update documentation based on research findings.

    Feature: {id}-{slug}
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

4. **Commit documentation changes:**
```bash
git add -A
git commit -m "docs: update documentation for feature {id}-{slug}"
git push
```

---

## Phase 3: Retrospective (Automatic)

Run retrospective automatically without asking permission.

### Step 3a: Run Retrospective

Follow the `retrospecting` skill, which handles:
1. Context bundle assembly (.meta.json, .review-history.md, git summary, artifact stats)
2. retro-facilitator agent dispatch (AORTA framework analysis)
3. retro.md generation
4. Knowledge bank updates
5. Commit

The skill includes graceful degradation — if retro-facilitator fails, it falls back to investigation-agent.

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
   git commit -m "chore: update CLAUDE.md with feature {id}-{slug} learnings" --allow-empty
   git push
   ```

---

## Phase 4: Completion Decision

Present only two options:

```
AskUserQuestion:
  questions: [{
    "question": "Feature {id}-{slug} complete. How would you like to finish?",
    "header": "Finish",
    "options": [
      {"label": "Merge & Release (Recommended)", "description": "Merge to develop and run release script"},
      {"label": "Create PR", "description": "Open pull request for team review"}
    ],
    "multiSelect": false
  }]
```

---

## Phase 5: Execute Selected Option

### Step 5a: Pre-Merge Validation

Before executing the selected option, discover and run project checks to catch issues while still on the feature branch.

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

Fix these issues manually, then run /finish-feature again.
```

Do NOT proceed to Create PR or Merge & Release if validation is failing.

### If "Create PR":

```bash
git push -u origin feature/{id}-{slug}
gh pr create --title "Feature: {slug}" --body "## Summary
{Brief description from spec.md}

## Changes
{List of key changes}

## Testing
{Test instructions or 'See tasks.md'}"
```

Output: "PR created: {url}"
→ Continue to Phase 6

### If "Merge & Release":

```bash
# Merge to develop
git checkout develop
git pull origin develop
git merge feature/{id}-{slug}
git push

# Run release script
./scripts/release.sh --ci
```

Output: "Merged to develop. Release: v{version}"
→ Continue to Phase 6

---

## Phase 6: Cleanup (Automatic)

Run automatically after Phase 5 completes.

### Step 6a: Update .meta.json

```json
{
  "status": "completed",
  "completed": "{ISO timestamp}",
  "phases": {
    "finish": {
      "completed": "{ISO timestamp}"
    }
  }
}
```

### Step 6b: Delete temporary files

```bash
rm docs/features/{id}-{slug}/.review-history.md 2>/dev/null || true
rm docs/features/{id}-{slug}/implementation-log.md 2>/dev/null || true
```

### Step 6c: Delete Feature Branch

- After PR: Branch will be deleted when PR merged via GitHub
- After Merge & Release: `git branch -d feature/{id}-{slug}`

### Step 6d: Final Output

```
Feature {id}-{slug} completed
Retrospective saved to retro.md
Branch cleaned up
{PR created: {url} | Released v{version}}

Learnings captured in knowledge bank.
```
