# Review System Migration (v2.2.0)

This guide documents breaking changes from the review system redesign.

## Breaking Changes

### Removed Components

| Component | Type | Replacement |
|-----------|------|-------------|
| `/verify` command | Command | Use phase reviewers instead |
| `verifying` skill | Skill | Absorbed into skeptic agents |
| `verifying-before-completion` skill | Skill | Discipline absorbed into agents |
| `spec-reviewer` agent | Agent | Merged into `implementation-reviewer` |
| `implementation-behavior-reviewer` agent | Agent | Merged into `implementation-reviewer` |
| `final-reviewer` agent | Agent | Merged into `implementation-reviewer` |

### Renamed Components

| Old Name | New Name |
|----------|----------|
| `chain-reviewer` | `phase-reviewer` |
| `task-breakdown-reviewer` | `task-reviewer` |

### New Components

| Component | Type | Purpose |
|-----------|------|---------|
| `spec-skeptic` | Agent | Reviews spec.md during specify phase for testability, assumptions, scope |
| `implementation-reviewer` | Agent | 4-level validation (Tasks → Spec → Design → PRD) |

## Migration for Custom Workflows

If you have custom workflows referencing removed components:

| Old Reference | New Reference |
|---------------|---------------|
| `chain-reviewer` | `phase-reviewer` |
| `spec-reviewer` | `implementation-reviewer` (Level 2: Spec) |
| `implementation-behavior-reviewer` | `implementation-reviewer` (all levels) |
| `final-reviewer` | `implementation-reviewer` (Level 4: PRD) |
| `/verify` | Remove - phase reviewers handle validation |
| `verifying` skill | Use phase-specific skeptic agent |
| `verifying-before-completion` | Built into all reviewer agents |

## Review System Overview

### Two-Tier Review Pattern

The new system uses a consistent two-tier pattern for each phase:

1. **Skeptic** (during phase): Challenges artifact quality
   - Question: "Is this artifact robust?"
   - Provides critical + constructive feedback
   - Uses severity: `blocker | warning | suggestion`

2. **Phase-Reviewer** (at transition): Validates handoff completeness
   - Question: "Does artifact have what next phase needs?"
   - Validates sufficiency, not quality

### Phase-Specific Skeptics

| Phase | Skeptic Agent | Focus |
|-------|---------------|-------|
| Specify | `spec-skeptic` | Testability, assumptions, scope |
| Design | `design-reviewer` | Robustness, completeness |
| Plan | `plan-reviewer` | Failure modes, TDD order |
| Tasks | `task-reviewer` | Executability, size |
| Implement | `implementation-reviewer` | Requirements compliance |

### Context Chain

All reviewers receive full previous artifact history for complete context:

| Phase | Skeptic Receives | Phase-Reviewer Receives |
|-------|------------------|-------------------------|
| Specify | prd.md, spec.md | prd.md, spec.md |
| Design | prd.md, spec.md, design.md | prd.md, spec.md, design.md |
| Plan | prd.md, spec.md, design.md, plan.md | prd.md, spec.md, design.md, plan.md |
| Tasks | spec.md, design.md, plan.md, tasks.md | spec.md, design.md, plan.md, tasks.md |
| Implement | ALL + code | ALL + code |

### Severity Model

All skeptics use standardized severity:

| Level | Meaning | Action |
|-------|---------|--------|
| `blocker` | Cannot proceed | Must fix before continuing |
| `warning` | Should address | Fix recommended but can proceed |
| `suggestion` | Improvement | Constructive feedback with HOW to improve |

**Key change:** `suggestion` replaces `note` and MUST include constructive guidance.

## Implementation Reviewer Details

The consolidated `implementation-reviewer` validates at 4 levels:

| Level | Validates Against | Checks |
|-------|-------------------|--------|
| Level 1: Tasks | tasks.md | Each task marked done, acceptance criteria met |
| Level 2: Spec | spec.md | All requirements addressed, acceptance criteria met |
| Level 3: Design | design.md | Architecture followed, interfaces match |
| Level 4: PRD | prd.md | Original outcomes achieved, no scope creep |

Critical rule: **Verify independently** - never trust claims, always read code.

## Workflow Changes

### Old Flow
```
brainstorm → specify → design → create-plan → create-tasks → implement → verify → finish
```

### New Flow
```
brainstorm → specify → design → create-plan → create-tasks → implement → finish
```

The `verify` phase is removed because:
- Each phase now has its own skeptic reviewer
- Phase transitions validated by `phase-reviewer`
- No separate verification step needed
