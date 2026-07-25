---
description: End the session — commit WIP, report engine state and open items
---

# /pd:wrap-up

Session bookend, not a phase. Leaves the feature branch committed and the open work visible. Merging, releasing, and phase exit belong to `/pd:finish-feature` and the phase commands.

**Steps:**
1. `git branch --show-current`. On `{pd_base_branch}` → say so and stop; wrap-up never commits to the base branch.
2. Uncommitted changes → `git add -A && git commit -m "wip: {one-line summary of the diff}"`. A push failure is reported, not retried or worked around.
3. Engine status line for the active feature via `get_phase`, fields verbatim; none active → say so.
4. Open items, one line each: uncommitted paths, verification commands last seen failing, unresolved reviewer blockers.

**Constraints:** no state writes — no `transition_phase`, no `complete_phase`, no `.meta.json`. Nothing is carried into the next session but the commit and this report.
