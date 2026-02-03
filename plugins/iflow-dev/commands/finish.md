---
description: Complete a feature - merge, run retro, cleanup branch
argument-hint: [feature-id]
---

# /iflow-dev:finish Command

Complete a feature and clean up.

## Determine Feature

Same logic as /iflow-dev:show-status command.

---

## Phase 1: Auto-Commit Uncommitted Work

1. **Check for uncommitted changes** via `git status --short`
2. **If uncommitted changes found:**
   - Auto-commit: `git add -A && git commit -m "wip: uncommitted changes before finish"`
   - Push to feature branch: `git push`
   - On push failure: Show error and STOP - user must resolve manually
3. **If no uncommitted changes:** Continue to Phase 2

---

## Phase 2: Pre-Completion Reviews

1. **Check tasks completion** (if tasks.md exists)
   - If incomplete tasks found, use AskUserQuestion:
     ```
     AskUserQuestion:
       questions: [{
         "question": "{n} tasks still incomplete. Continue anyway?",
         "header": "Tasks",
         "options": [
           {"label": "Continue", "description": "Proceed despite incomplete tasks"},
           {"label": "Stop", "description": "Return to complete tasks first"}
         ],
         "multiSelect": false
       }]
     ```

2. **Offer quality review** (for Standard/Full modes)
   - Use AskUserQuestion:
     ```
     AskUserQuestion:
       questions: [{
         "question": "Run quality review before completing?",
         "header": "Quality",
         "options": [
           {"label": "Yes", "description": "Spawn quality-reviewer agent"},
           {"label": "Skip", "description": "Continue without review"}
         ],
         "multiSelect": false
       }]
     ```
   - If yes: Spawn quality-reviewer agent

3. **Offer documentation review** (if docs detected)
   - Detect: README.md, CHANGELOG.md, HISTORY.md, API.md, docs/*.md
   - If any docs exist, use AskUserQuestion:
     ```
     AskUserQuestion:
       questions: [{
         "question": "Review documentation before completing?",
         "header": "Docs",
         "options": [
           {"label": "Yes", "description": "Invoke /iflow-dev:update-docs skill"},
           {"label": "Skip", "description": "Continue without doc review"}
         ],
         "multiSelect": false
       }]
     ```
   - If yes: Invoke `/iflow-dev:update-docs` skill
   - If no docs detected: Skip silently

---

## Phase 3: Retrospective (Required)

Run retrospective BEFORE the merge decision:

1. **Invoke retrospecting skill:**
   - Gather data from feature folder
   - Ask user about learnings via AskUserQuestion
   - User selects which learnings to keep
   - Save to `docs/features/{id}-{slug}/retro.md`

2. **Commit retrospective artifacts:**
   ```bash
   git add docs/features/{id}-{slug}/retro.md docs/features/{id}-{slug}/.meta.json
   git commit -m "docs: add retrospective for feature {id}-{slug}"
   git push
   ```

This is **required**, not optional. The user controls what learnings to capture,
but the retrospective step always runs before the merge decision.

---

## Phase 4: Completion Decision

After all artifacts are committed, present completion options via AskUserQuestion:

```
AskUserQuestion:
  questions: [{
    "question": "Feature {id}-{slug} ready. How would you like to complete?",
    "header": "Finish",
    "options": [
      {"label": "Create PR", "description": "Open pull request (recommended for teams)"},
      {"label": "Merge Locally", "description": "Merge to main and push directly"},
      {"label": "Keep Branch", "description": "Exit without merging (finish later)"},
      {"label": "Discard", "description": "Mark as abandoned and delete branch"}
    ],
    "multiSelect": false
  }]
```

---

## Phase 5: Execute Selected Option

### If "Create PR":
```bash
git push -u origin feature/{id}-{slug}
gh pr create --title "Feature: {slug}" --body "..."
```
Inform: "PR created: {url}"
→ Continue to Cleanup

### If "Merge Locally":
```bash
git checkout main
git merge feature/{id}-{slug}
git push
```
→ Continue to Cleanup

### If "Keep Branch":
Inform: "Branch kept. Run /iflow-dev:finish again when ready to merge."
**Exit early** - no cleanup.

### If "Discard":
Confirm via AskUserQuestion:
```
AskUserQuestion:
  questions: [{
    "question": "This will mark the feature as abandoned. Are you sure?",
    "header": "Confirm",
    "options": [
      {"label": "Yes, Discard", "description": "Mark abandoned and delete branch"},
      {"label": "Cancel", "description": "Return to options"}
    ],
    "multiSelect": false
  }]
```
→ If confirmed, continue to Cleanup with abandoned status

---

## Phase 6: Cleanup (for terminal options only)

For "Create PR", "Merge Locally", or "Discard":

1. **Update .meta.json:**

   **For completed (Create PR, Merge Locally):**
   ```json
   {
     "status": "completed",
     "completed": "{ISO timestamp}"
   }
   ```

   **For abandoned (Discard):**
   ```json
   {
     "status": "abandoned",
     "completed": "{ISO timestamp}"
   }
   ```

2. **Delete .review-history.md:**
   ```bash
   rm docs/features/{id}-{slug}/.review-history.md
   ```

3. **Delete branch:**
   - After merge: `git branch -d feature/{id}-{slug}`
   - After PR: Branch deleted when PR merged via GitHub
   - After discard: `git branch -D feature/{id}-{slug}`

---

## Update State

If Vibe-Kanban:
- Move card to "Done" (completed) or "Archived" (abandoned)

---

## Final Output

```
✓ Feature {id}-{slug} {completed|abandoned}
✓ Retrospective saved to retro.md
✓ Branch cleaned up

Learnings captured in knowledge bank.
```
