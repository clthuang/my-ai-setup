---
description: Show an entity's ancestry chain or descendant tree
argument-hint: "[--feature=<id> | --project=<id> | --backlog=<id> | --brainstorm=<stem>] [--descendants]"
---

# /pd:show-lineage

Read-only lineage query. `get_lineage` returns a pre-formatted tree — print it, do not re-render or re-walk it.

**Steps:**
1. Resolve the entity ref from the flag: `--feature=` → `feature:{id}-{slug}`, `--project=` → `project:{id}`, `--backlog=` → `backlog:{id}`, `--brainstorm=` → `brainstorm:{stem}`. No flag → the `feature/(.+)` suffix of `git branch --show-current`.
2. A bare feature id without slug: `get_entity(ref="feature:{id}")` to resolve the full ref. Not found → glob `{pd_artifacts_root}/features/{id}-*` for the slug.
3. `get_lineage(type_id="{ref}", direction=..., max_depth=10)` — `direction="down"` with `--descendants`, else `"up"`.
4. Print the returned tree. Traversal truncated at the depth limit → append one line saying so.

**Constraints:** no flag and no feature branch → print the usage line and stop. Error envelope surfaced verbatim, with `/pd:doctor` as the hint.
