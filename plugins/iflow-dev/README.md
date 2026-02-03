# iflow Plugin

Structured feature development workflow with skills, agents, and commands for methodical development from ideation to implementation.

## Components

| Type | Count |
|------|-------|
| Skills | 19 |
| Agents | 15 |
| Commands | 15 |
| Hooks | 4 |

## Commands

**Start:**
| Command | Description |
|---------|-------------|
| `/iflow-dev:brainstorm [topic]` | 7-stage PRD creation with research subagents |
| `/iflow-dev:create-feature <desc>` | Start building (creates folder + branch) |

**Build phases** (run in order):
| Command | Output |
|---------|--------|
| `/iflow-dev:specify [--feature=ID]` | spec.md |
| `/iflow-dev:design` | design.md (4-stage workflow) |
| `/iflow-dev:create-plan` | plan.md |
| `/iflow-dev:create-tasks` | tasks.md |
| `/iflow-dev:implement` | Code changes |
| `/iflow-dev:finish` | Merge, retro, cleanup |

**Anytime:**
| Command | Purpose |
|---------|---------|
| `/iflow-dev:verify` | Quality check current phase |
| `/iflow-dev:show-status` | See current feature state |
| `/iflow-dev:list-features` | See all active features |
| `/iflow-dev:retrospect` | Capture learnings |
| `/iflow-dev:add-to-backlog <idea>` | Capture ideas for later |
| `/iflow-dev:cleanup-brainstorms` | Delete old scratch files |
| `/iflow-dev:sync-cache` | Reload plugin after changes |

## Design Phase Workflow

The `/iflow-dev:design` command uses a 4-stage workflow for robust design artifacts:

```
Stage 1: ARCHITECTURE DESIGN → High-level structure, components, decisions, risks
    ↓
Stage 2: INTERFACE DESIGN → Precise contracts between components
    ↓
Stage 3: DESIGN REVIEW LOOP → design-reviewer challenges assumptions (1-3 iterations)
    ↓
Stage 4: HANDOFF REVIEW → chain-reviewer ensures plan phase readiness
```

### Reviewer Roles

| Reviewer | Role | Question |
|----------|------|----------|
| design-reviewer | Skeptic | "Is this design robust, complete, and will it actually work?" |
| chain-reviewer | Gatekeeper | "Can the next phase complete its work using ONLY this artifact?" |

The design-reviewer challenges the design quality. The chain-reviewer ensures the artifact is sufficient for the next phase.

## Create Plan Phase Workflow

The `/iflow-dev:create-plan` command uses a 2-stage review workflow:

```
Stage 1: PLAN-REVIEWER (Skeptical Review)
    │   • Failure modes - What could go wrong?
    │   • Untested assumptions - What's assumed but not validated?
    │   • Dependency accuracy - Are dependencies correct and complete?
    │   • TDD order - Interface → Tests → Implementation sequence?
    ↓
Stage 2: CHAIN-REVIEWER (Execution Readiness)
    │   • Can an engineer break this into tasks?
    │   • Are all design items covered?
    ↓
[User Prompt: Run /create-tasks?]
```

### Reviewer Roles

| Reviewer | Role | Question |
|----------|------|----------|
| plan-reviewer | Skeptic | "Will this plan actually work when implemented?" |
| chain-reviewer | Gatekeeper | "Can the next phase complete its work using ONLY this artifact?" |

## Agents

| Agent | Purpose |
|-------|---------|
| brainstorm-reviewer | Reviews PRD drafts for completeness before promotion |
| chain-reviewer | Validates artifacts have what next phase needs (gatekeeper) |
| codebase-explorer | Analyzes codebase for patterns and constraints |
| code-quality-reviewer | Reviews implementation quality by severity |
| design-reviewer | Challenges design assumptions and finds gaps (skeptic) |
| final-reviewer | Validates implementation matches spec |
| generic-worker | General-purpose implementation agent |
| implementer | Task implementation with self-review |
| internet-researcher | Searches web for best practices and standards |
| plan-reviewer | Skeptical plan reviewer for failure modes and TDD compliance |
| investigation-agent | Read-only research before implementation |
| prd-reviewer | Critical review of PRD drafts |
| quality-reviewer | Verifies code quality and finds dead code |
| skill-searcher | Finds relevant existing skills |
| spec-reviewer | Verifies implementation matches spec |

## Installation

```bash
/plugin marketplace add .
/plugin install iflow@my-local-plugins
```
