---
description: Execute the plan with execution-grounded QA and one adversarial review
argument-hint: "[--feature=<id-slug>]"
---

# /pd:implement

Contract command. Shared mechanics: workflow-transitions skill. Execution mechanics (worktree parallel dispatch): implementing skill.

**Purpose:** turn `plan.md` into working, verified code on the feature branch.

**Inputs:** `plan.md` tasks; `shape.md` contracts; engine phase state.

**Steps:**
1. Engine entry `target_phase="implement"`; gate `bash scripts/phase-gate.sh implement {feature-dir}`.
2. Execute tasks in plan order. Parallel-safe tasks dispatch to implementer agents in `.pd-worktrees/` isolation (implementing skill); single-thread work stays inline. Every task ends with its verification command run green and a commit.
3. **QA moment (execution-grounded, FR-5):** dispatch `pd:qa-executor` — it RUNS the suites and drives the affected flows end-to-end, returning commands + output as evidence. Express mode: this pass is the combined QA+review and step 4 is skipped.
4. **Review moment (2 of 2):** dispatch `pd:code-quality-reviewer` on the full branch diff (fresh context; findings cite file:line; return schema in the agent file). One pass → at most one fix round → remaining blockers escalate to the user.
5. Circuit breaker: one bounded breaker for the whole phase — 3 fix cycles total; the final validation run does not count toward it. Tripping stops execution with a summary.
6. Engine exit. Code and tests are the artifact; there is no implementation log.

**Constraints:** implementer prompts carry task-scoped contracts and pointers, never state dumps; non-trivial logic lands with a test asserting a fact true only on the new path; a clean QA + review pass ends the phase — no second full-review round exists.
