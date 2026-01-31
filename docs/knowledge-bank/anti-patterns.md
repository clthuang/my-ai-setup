# Anti-Patterns

Things to avoid. Updated through retrospectives.

---

## Known Anti-Patterns

### Anti-Pattern: Working in Wrong Worktree
Making changes in main worktree when a feature worktree exists.
- Observed in: Feature #002
- Cost: Had to stash, move changes, re-apply in correct worktree
- Instead: Check `git worktree list` at session start; work in feature worktree if one exists

### Anti-Pattern: Over-Granular Tasks
Breaking a single file modification into many small separate tasks.
- Observed in: Feature #003
- Cost: Initial 31 tasks had to be consolidated to 18 during verification
- Example: 4 tasks for one skill file (create structure, add sequence, add validation, add patterns)
- Instead: One task per logical unit of work (one file = one task, or one component = one task)

### Anti-Pattern: Relative Paths in Hooks
Using `find .` or relative paths in hooks for project file discovery.
- Observed in: Plugin cache staleness bug
- Cost: Missed test files when Claude ran from subdirectories; stale feature metadata
- Root cause: `find .` searches from PWD; `PLUGIN_ROOT` points to cached copy
- Instead: Use `detect_project_root()` from shared library, search from `PROJECT_ROOT`

### Anti-Pattern: Skipping Workflow for "Simple" Tasks
Rationalizing that a task is "just mechanical" to justify skipping workflow phases.
- Observed in: Feature #008
- Cost: Had to retroactively create feature; missed the brainstorm → feature promotion checkpoint
- Root cause: Task felt simple (search-and-replace), so jumped from option selection to implementation
- Instead: Brainstorm phase ends with "Turn this into a feature?" - always ask, let user decide to skip

<!-- Example format:
### Anti-Pattern: Premature Optimization
Optimizing before measuring actual performance.
- Observed in: Feature #35
- Cost: 2 days wasted on unnecessary caching
- Instead: Measure first, optimize bottlenecks only
-->
