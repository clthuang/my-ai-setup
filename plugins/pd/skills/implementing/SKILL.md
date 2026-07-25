---
name: implementing
description: Execution mechanics for the implement phase — inline versus worktree-isolated task dispatch, and merge-back. Use when executing a feature's plan tasks.
---

# Implementing

## Choosing a mode
Tasks the plan marks `[parallel-safe]` dispatch to `pd:implementer` agents under worktree isolation. Everything else — including any single-task feature — the orchestrator implements inline on the feature branch, with no worktree.

## Worktree dispatch
Batch size is `max_concurrent_agents` from session context (default 5). Per batch:

**1. Create one worktree per task.**
```bash
git worktree add ".pd-worktrees/task-{N}" -b "worktree-{feature_id}-task-{N}"
```
Git creates the branch before it validates the path, so a failed add leaks a branch. On non-zero exit, run `git branch -D "worktree-{feature_id}-task-{N}" 2>/dev/null || true` and drop that one task to inline execution — the rest of the batch continues.

**2. Seed gitignored inputs.** If the project root holds a `.worktreeinclude` file, copy every path it lists into each new worktree; without them the agent cannot run the project's tests or build. No such file means nothing to copy.

**3. Dispatch the batch in ONE message**, one Task call per task, so they run concurrently. Each prompt carries: the absolute worktree path, the task contract with its verification command, and pointers to the `shape.md` and `plan.md` sections it implements. Each prompt also states the isolation rules — every Bash call begins with `cd {abs_worktree_path}`, every file tool uses absolute paths, and nothing outside the worktree is written.

**4. Merge back onto the feature branch in plan order.**
```bash
git merge --no-ff "worktree-{feature_id}-task-{N}" -m "task {N}: {title}"
```
A conflict is a hard stop: halt the remaining merges, leave the worktree on disk, and return the conflicted paths and unmerged branch name to the user. Remove a worktree only after its own merge succeeds:
```bash
git worktree remove ".pd-worktrees/task-{N}" 2>/dev/null
```
(`--quiet` is unsupported on git 2.50+.) Confirm `.pd-worktrees/` is gitignored before the first dispatch.

## Every task, both modes
Run the task's verification command and show its output. A task whose command fails is not done: fix it, or stop and say so. Never mark a task complete on a red or unrun check.
