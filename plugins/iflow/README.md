# iflow Plugin

Structured feature development workflow with skills, agents, and commands for methodical development from ideation to implementation.

## Components

| Type | Count |
|------|-------|
| Skills | 19 |
| Agents | 21 |
| Commands | 16 |
| Hooks | 5 |

## Commands

**Start:**
| Command | Description |
|---------|-------------|
| `/iflow:brainstorm [topic]` | 7-stage PRD creation with research subagents |
| `/iflow:create-feature <desc>` | Start building (creates folder + branch) |

**Build phases** (run in order):
| Command | Output |
|---------|--------|
| `/iflow:specify [--feature=ID]` | spec.md |
| `/iflow:design` | design.md (4-stage workflow) |
| `/iflow:create-plan` | plan.md |
| `/iflow:create-tasks` | tasks.md |
| `/iflow:implement` | Code changes |
| `/iflow:finish` | Merge, retro, cleanup |

**Anytime:**
| Command | Purpose |
|---------|---------|
| `/iflow:verify` | Quality check current phase |
| `/iflow:show-status` | See current feature state |
| `/iflow:list-features` | See all active features |
| `/iflow:retrospect` | Capture learnings |
| `/iflow:add-to-backlog <idea>` | Capture ideas for later |
| `/iflow:cleanup-brainstorms` | Delete old scratch files |
| `/iflow:sync-cache` | Reload plugin after changes |
| `/iflow:secretary` | Intelligent task routing to commands/agents |

## Design Phase Workflow

The `/iflow:design` command uses a 4-stage workflow for robust design artifacts:

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

The `/iflow:create-plan` command uses a 2-stage review workflow:

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
| brainstorm-reviewer | Reviews brainstorm artifacts for completeness before promotion |
| chain-reviewer | Validates artifacts have what next phase needs (gatekeeper) |
| code-quality-reviewer | Reviews implementation quality by severity |
| code-simplifier | Identifies unnecessary complexity and suggests simplifications |
| codebase-explorer | Analyzes codebase for patterns and constraints |
| design-reviewer | Challenges design assumptions and finds gaps (skeptic) |
| documentation-researcher | Researches documentation state and identifies update needs |
| documentation-writer | Writes and updates documentation |
| final-reviewer | Validates implementation delivers PRD outcomes |
| generic-worker | General-purpose implementation agent |
| implementation-behavior-reviewer | Validates behavior against requirements chain |
| implementer | Task implementation with TDD and self-review |
| internet-researcher | Searches web for best practices and standards |
| investigation-agent | Read-only research before implementation |
| plan-reviewer | Skeptical plan reviewer for failure modes and TDD compliance |
| prd-reviewer | Critical review of PRD drafts |
| security-reviewer | Reviews implementation for security vulnerabilities |
| skill-searcher | Finds relevant existing skills |
| spec-reviewer | Verifies implementation matches spec |
| task-breakdown-reviewer | Validates task breakdown quality |
| secretary | Intelligent task routing with discovery, interpretation, and delegation |

## Installation

```bash
/plugin marketplace add .
/plugin install iflow@my-local-plugins
```
