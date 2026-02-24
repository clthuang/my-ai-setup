# Anti-Patterns

Things to avoid. Updated through retrospectives.

---

## Known Anti-Patterns

### Anti-Pattern: Working in Wrong Worktree
Making changes in main worktree when a feature worktree exists.
- Observed in: Feature #002
- Cost: Had to stash, move changes, re-apply in correct worktree
- Instead: Check `git worktree list` at session start; work in feature worktree if one exists
- Last observed: Feature #022
- Observation count: 1

### Anti-Pattern: Over-Granular Tasks
Breaking a single file modification into many small separate tasks.
- Observed in: Feature #003
- Cost: Initial 31 tasks had to be consolidated to 18 during verification
- Example: 4 tasks for one skill file (create structure, add sequence, add validation, add patterns)
- Instead: One task per logical unit of work (one file = one task, or one component = one task)
- Last observed: Feature #022
- Observation count: 1

### Anti-Pattern: Relative Paths in Hooks
Using `find .` or relative paths in hooks for project file discovery.
- Observed in: Plugin cache staleness bug
- Cost: Missed test files when Claude ran from subdirectories; stale feature metadata
- Root cause: `find .` searches from PWD; `PLUGIN_ROOT` points to cached copy
- Instead: Use `detect_project_root()` from shared library, search from `PROJECT_ROOT`
- Last observed: Feature #022
- Observation count: 1

### Anti-Pattern: Skipping Workflow for "Simple" Tasks
Rationalizing that a task is "just mechanical" to justify skipping workflow phases.
- Observed in: Feature #008
- Cost: Had to retroactively create feature; missed the brainstorm → feature promotion checkpoint
- Root cause: Task felt simple (search-and-replace), so jumped from option selection to implementation
- Instead: Brainstorm phase ends with "Turn this into a feature?" - always ask, let user decide to skip
- Last observed: Feature #022
- Observation count: 1

### Anti-Pattern: Line Number References in Sequential Tasks
Referencing specific line numbers in tasks that will shift after earlier task insertions.
- Observed in: Feature #018
- Cost: Tasks 4.2-4.4 line numbers shifted ~60 lines after Task 4.1 insertion, causing confusion
- Root cause: Line numbers are brittle anchors when tasks modify the same file sequentially
- Instead: Use semantic anchors (exact text search targets) that survive insertions
- Last observed: Feature #025
- Observation count: 3

### Anti-Pattern: Frozen Artifact Contradictions
Leaving PRD claims that contradict later spec/design resolutions without noting the divergence.
- Observed in: Feature #018
- Cost: Implementation reviewer flagged PRD FR-9 (MCP tool) vs actual implementation (inline Mermaid) as a "blocker"
- Root cause: PRD is frozen brainstorm artifact but readers don't know which claims were superseded
- Instead: Add Design Divergences table in plan.md documenting PRD/spec/design deviations with rationale
- Last observed: Feature #022
- Observation count: 2

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
- Last observed: Feature #023
- Observation count: 2

### Anti-Pattern: Parser Against Assumed Format
Designing parsers against assumed format without verifying against actual files. Writing regex patterns or format specifications based on what the format "should be" rather than reading actual files to confirm.
- Observed in: Feature #022, design phase iteration 3
- Cost: Design circuit breaker hit (5 iterations); task parser regex was checkbox-based but actual tasks.md uses heading-based format
- Instead: Read actual target files before writing parsers; add "verified against: <file path>" annotation to design documents
- Last observed: Feature #023
- Observation count: 2

### Anti-Pattern: Post-Approval Informational Iterations
Continuing review iterations after approval when all remaining issues are informational ("no change needed"). Adds wall-clock time without producing artifact changes.
- Observed in: Feature #022, create-plan phase
- Cost: Plan review iterations 4-5 after iter 3 approval produced zero changes, adding ~30 min
- Instead: Implement early-exit when reviewer approves with zero actionable issues
- Last observed: Feature #022
- Observation count: 1

<!-- Example format:
### Anti-Pattern: Premature Optimization
Optimizing before measuring actual performance.
- Observed in: Feature #35
- Cost: 2 days wasted on unnecessary caching
- Instead: Measure first, optimize bottlenecks only
-->

### Anti-Pattern: Specifying a Parser Without a Complete Round-Trip Example
When design describes a parser (fields extracted, splitting logic, metadata structure) but does not include a fully worked example showing input text and resulting data structure with ALL fields populated, downstream phases repeatedly discover missing fields or format gaps, causing cascading review iterations.
- Observed in: Feature #023, design through create-tasks phases
- Cost: 3+ extra review iterations across 3 phases as format was refined piecemeal
- Instead: Include at least one complete input→output example with all parser fields in the design
- Confidence: high
- Last observed: Feature #023
- Observation count: 1

### Anti-Pattern: Implementation Reviewer Flagging Pre-Existing Code as Blockers
When the quality reviewer flags code quality issues on lines not introduced by the current feature (e.g., a bare except clause in a function written months ago), it wastes review iterations on rebuttals and creates noise that obscures genuine issues in the new code.
- Observed in: Feature #023, implement phase
- Cost: 2 wasted review iterations (iterations 3-4 produced zero code changes)
- Instead: Reviewer should check git diff to verify flagged code is from the current feature before classifying as blocker
- Confidence: high
- Last observed: Feature #023
- Observation count: 1

### Anti-Pattern: Over-Documentation Before System Maturity
Adding behavioral guidance for features/behaviors not yet consistently observed in practice. Documentation should trail patterns by at least one reinforcement cycle (observed in 2+ features).
- Observed in: CLAUDE.md template analysis — most template items were aspirational rather than proven
- Cost: False authority and wasted reader attention on unproven patterns
- Instead: Wait for observational evidence from 1+ cycles before documenting as standard guidance
- Confidence: medium
- Last observed: 2026-02-22
- Observation count: 1

### Anti-Pattern: Classifying Absent Content Without Full-Artifact Verification
Asserting that a required element is missing without verifying its absence in the full artifact. Summarized reviewer inputs mask content that exists in the full document, producing false-positive blockers that waste a full review iteration.
- Observed in: Feature #026 — design iter 1 (3 false-positive blockers), task review iter 1 (2), chain review iter 3 (1)
- Cost: 6 wasted blocker rebuttals across 3 phases
- Instead: Before classifying an element as absent, verify it is genuinely not present in the full artifact
- Confidence: high
- Last observed: 2026-02-22
- Observation count: 1

### Anti-Pattern: Flagging Annotated Spec Deviations as Implementation Failures
When a spec-design deviation is annotated in the design document (TD-* entry) and acknowledged in the spec, treating it as a spec failure during implementation review wastes a circuit-breaker slot on a non-fixable issue.
- Observed in: Feature #026, implement iter 5 — AC-5 vs TD-5 flagged as spec failure despite annotation in design.md
- Cost: Consumed final circuit-breaker iteration on a non-resolvable issue
- Instead: Check for deviation annotations before flagging spec mismatches as blockers
- Confidence: high
- Last observed: 2026-02-22
- Observation count: 1

### Anti-Pattern: Open-Ended Security Review Without a Threat Model
Conducting security review on a path extraction subsystem without first defining a threat model. Each fix closes one attack path and reveals the next, producing escalating iterations rather than convergence.
- Observed in: Feature #026, implement iters 3-5 — path validation hardened 3 times without converging
- Cost: 3 iterations of security review; circuit breaker reached without resolution
- Instead: Require a Security Threat Model subsection in design defining allowed path forms, rejected patterns, and acceptable residual risks
- Confidence: medium
- Last observed: 2026-02-22
- Observation count: 1

### Anti-Pattern: Describing Algorithms Without Specifying Concrete I/O and Edge Cases
Mentioning an algorithm by name (e.g., "Accept-some merge") without documenting step-by-step inputs, outputs, and edge cases causes blockers in downstream phases as each consumer interprets the gap differently.
- Observed in: Feature #027, design iter 1 blocker ("Accept-some partial merge algorithm unspecified") + tasks iter 2 (4 blockers: content unspecified, CHANGE scope unclear, merge algorithm undocumented, extraction target unspecified)
- Cost: Same underspecification caused blockers in two separate phases
- Instead: For every algorithm described, document: all inputs, all outputs, error/edge cases, write targets
- Confidence: high
- Last observed: Feature #027
- Observation count: 1

### Anti-Pattern: Hardcoding Year Values in Search Queries
Embedding literal year values (e.g., "2026") in search queries or date-sensitive prompts causes silent degradation as time passes — no error signal, just less relevant results.
- Observed in: Feature #027, implementation iter 2 — quality reviewer flagged hardcoded year in refresh-prompt-guidelines.md search queries
- Cost: Silently stale results with no visible error
- Instead: Use dynamic placeholders like {current year} with instructions to resolve at runtime
- Confidence: high
- Last observed: Feature #027
- Observation count: 1
