# Review System and Evidence-Grounded Workflow (v2.3.0)

This guide documents the review system redesign (v2.2.0) and evidence-grounded phase improvements (v2.3.0).

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
| `spec-reviewer` | Agent | Reviews spec.md during specify phase for testability, assumptions, scope |
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
| Specify | `spec-reviewer` | Testability, assumptions, scope |
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

## Evidence-Grounded Workflow Improvements (v2.3.0)

### Spec Phase Enhancements

Spec.md now includes a **Feasibility Assessment** section with:
- **5-level confidence scale:** None → Possible → Plausible → Probable → Proven
- **Evidence requirements:** Citations to research, prototypes, prior art, or proofs
- Replaces unsupported assumptions with evidence-based validation

### Design Phase Enhancements

Design workflow expanded to 5 stages with evidence grounding:

**Stage 0: Prior Art Research**
- Gather existing solutions, patterns, standards
- Document what's already been tried
- Identify evidence sources for decisions

**Stage 1-2: Architecture & Interface Design**
- Technical decisions now require documented alternatives and trade-offs
- Evidence-grounded reasoning: why this choice over alternatives
- Principles documented to guide implementation

**Stage 3: Design Review with Independent Verification**
- design-reviewer uses Context7 (documentation) and WebSearch (standards/best practices)
- Independent verification replaces assumption-based review
- 1-3 iteration review loop for robustness

### Plan Phase Enhancements

Plan.md items now include reasoning fields:
- **Why this item:** Links to spec requirements and design decisions
- **Why this order:** Dependency reasoning, TDD sequence
- **Removed:** Line-of-code estimates (replaced by reasoning)
- **Added:** Traceability to design and spec artifacts

### Tasks Phase Enhancements

Tasks.md now includes:
- **Why field:** Links each task back to plan items
- **Traceability chain:** Tasks → Plan → Design → Spec → PRD
- Enables requirements verification at implementation

### Workflow Automation (v2.3.0)

Phase approvals now trigger automatic actions:
- **Auto-commit:** After spec, design, plan, tasks approval
- **Auto-push:** After phase completion for workflow continuity
- Commit messages include phase name and changes summary

## Workflow Changes

### Old Flow (v2.1 and earlier)
```
brainstorm → specify → design → create-plan → create-tasks → implement → verify → finish
```

### Current Flow (v2.2+)
```
brainstorm → specify → design → create-plan → create-tasks → implement → finish
```

### Evidence-Grounded Flow (v2.3+)
```
brainstorm
  ↓ (PRD with research evidence)
specify (with Feasibility Assessment + evidence)
  ↓ (spec-skeptic validates assumptions)
design (5-stage: Prior Art → Architecture → Interface → Review → Handoff)
  ↓ (design-reviewer uses independent verification)
create-plan (items with reasoning fields)
  ↓ (plan-reviewer validates failure modes)
create-tasks (with Why field traceability)
  ↓ (task-reviewer validates executability)
implement (4-level requirements verification)
  ↓
finish (merge, retro, cleanup)
```

Key improvements:
- Each phase now has its own skeptic reviewer
- Phase transitions validated by `phase-reviewer`
- Evidence-grounded decisions throughout
- Auto-commit/auto-push maintain VCS continuity
- Complete traceability from tasks back to PRD
