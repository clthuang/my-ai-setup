# Anti-Patterns

Things to avoid. Updated through retrospectives.

---

## Known Anti-Patterns

### Anti-Pattern: Working in Wrong Worktree
Making changes in main worktree when a feature worktree exists.
- Observed in: Feature #002
- Cost: Had to stash, move changes, re-apply in correct worktree
- Instead: Check `git worktree list` at session start; work in feature worktree if one exists

<!-- Example format:
### Anti-Pattern: Premature Optimization
Optimizing before measuring actual performance.
- Observed in: Feature #35
- Cost: 2 days wasted on unnecessary caching
- Instead: Measure first, optimize bottlenecks only
-->
