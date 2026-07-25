---
name: finishing-branch
description: Merge-to-base-branch mechanics and post-retro branch cleanup. Use when completing a feature branch.
---

# Finishing a Branch

Order matters: the retrospective runs first. Branch and worktree cleanup destroy the evidence it reads.

1. **Clean tree.** Commit anything outstanding — a dirty tree stops the merge.

2. **Merge** into `{pd_base_branch}` (from session context):
   ```bash
   git checkout {pd_base_branch} && git pull && git merge {feature-branch} && git push
   ```
   A conflict is a hard stop: report the conflicted paths, leave both branches intact, return to the user. Never force-push; never resolve a conflict by discarding one side.

3. **Release.** Run `{pd_release_script}` if that session value is set and the file exists; otherwise say none is configured.

4. **Clean up, only after `retro.md` is committed:** `git branch -d {feature-branch}` — never `-D`, since the safe delete refusing on unmerged work is the guard — then remove any `.pd-worktrees/` directories left from this feature.

**PR path:** push the branch and open the PR in place of steps 2–4; the remote deletes the branch when the PR merges.
