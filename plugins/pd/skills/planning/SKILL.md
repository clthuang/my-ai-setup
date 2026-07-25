---
name: planning
description: Shape of a feature's Plan section — ordered tasks, files touched, per-task verification. Use when writing or reviewing `## Plan` in plan.md.
---

# Planning

`plan.md` carries one `## Plan` section: tasks derived from `## Design` at the moment they are dispatched, regenerated whenever the design moves. It is not a fourth artifact kept in sync by hand.

Each task states:

- **Deliverable** — the concrete output. Never a line count, never a time estimate.
- **Files** — the paths it creates or modifies.
- **Verification** — the exact command that proves it done, with the expected result. A task no command can prove is under-specified: split it or sharpen it.
- **Source** — the design decision or requirement it implements.
- **`[parallel-safe]`** — set only when the task's file set is disjoint from every other marked task. Unmarked tasks run in plan order.

Order by dependency: a task appears after every task producing an input it reads.
