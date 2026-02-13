# Anti-Patterns

Things to avoid. Updated through retrospectives.

---

## Known Anti-Patterns

### Anti-Pattern: Working in Wrong Worktree
Making changes in main worktree when a feature worktree exists.
- Observed in: Feature #002
- Cost: Had to stash, move changes, re-apply in correct worktree
- Instead: Check `git worktree list` at session start; work in feature worktree if one exists
- Last observed: Feature #002
- Observation count: 1

### Anti-Pattern: Over-Granular Tasks
Breaking a single file modification into many small separate tasks.
- Observed in: Feature #003
- Cost: Initial 31 tasks had to be consolidated to 18 during verification
- Example: 4 tasks for one skill file (create structure, add sequence, add validation, add patterns)
- Instead: One task per logical unit of work (one file = one task, or one component = one task)
- Last observed: Feature #003
- Observation count: 1

### Anti-Pattern: Relative Paths in Hooks
Using `find .` or relative paths in hooks for project file discovery.
- Observed in: Plugin cache staleness bug
- Cost: Missed test files when Claude ran from subdirectories; stale feature metadata
- Root cause: `find .` searches from PWD; `PLUGIN_ROOT` points to cached copy
- Instead: Use `detect_project_root()` from shared library, search from `PROJECT_ROOT`
- Last observed: Feature #008 (approximate -- original provenance was non-numeric)
- Observation count: 1

### Anti-Pattern: Skipping Workflow for "Simple" Tasks
Rationalizing that a task is "just mechanical" to justify skipping workflow phases.
- Observed in: Feature #008
- Cost: Had to retroactively create feature; missed the brainstorm → feature promotion checkpoint
- Root cause: Task felt simple (search-and-replace), so jumped from option selection to implementation
- Instead: Brainstorm phase ends with "Turn this into a feature?" - always ask, let user decide to skip
- Last observed: Feature #008
- Observation count: 1

### Anti-Pattern: Line Number References in Sequential Tasks
Referencing specific line numbers in tasks that will shift after earlier task insertions.
- Observed in: Feature #018
- Cost: Tasks 4.2-4.4 line numbers shifted ~60 lines after Task 4.1 insertion, causing confusion
- Root cause: Line numbers are brittle anchors when tasks modify the same file sequentially
- Instead: Use semantic anchors (exact text search targets) that survive insertions
- Last observed: Feature #018
- Observation count: 1

### Anti-Pattern: Frozen Artifact Contradictions
Leaving PRD claims that contradict later spec/design resolutions without noting the divergence.
- Observed in: Feature #018
- Cost: Implementation reviewer flagged PRD FR-9 (MCP tool) vs actual implementation (inline Mermaid) as a "blocker"
- Root cause: PRD is frozen brainstorm artifact but readers don't know which claims were superseded
- Instead: Add Design Divergences table in plan.md documenting PRD/spec/design deviations with rationale
- Last observed: Feature #018
- Observation count: 1

### Anti-Pattern: Dual-Representation Dependency Graphs
Maintaining dependency information in both ASCII art and textual description invites contradictions.
- Observed in: Feature #021
- Cost: Plan dependency graph redrawn 3+ times across 6 iterations to fix graph-vs-text mismatches
- Root cause: Two representations of the same data with no single source of truth
- Instead: Use mermaid for dependency graphs (serves both visual and textual roles) or maintain only one representation
- Last observed: Feature #021
- Observation count: 1

### Anti-Pattern: Bash Variable Interpolation in Inline Python
Using `${VARIABLE}` inside Python strings embedded in bash scripts enables injection.
- Observed in: Feature #021
- Cost: Security reviewer flagged session-start.sh line 169 using `${PROJECT_ROOT}` in Python glob
- Root cause: Bash expands variables before Python sees the string; special characters in paths could break or inject
- Instead: Pass external values via `sys.argv` or environment variables; never string interpolation
- Last observed: Feature #021
- Observation count: 1

<!-- Example format:
### Anti-Pattern: Premature Optimization
Optimizing before measuring actual performance.
- Observed in: Feature #35
- Cost: 2 days wasted on unnecessary caching
- Instead: Measure first, optimize bottlenecks only
-->
