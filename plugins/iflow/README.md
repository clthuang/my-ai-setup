# iflow Plugin

Structured feature development workflow with skills, agents, and commands for methodical development from ideation to implementation.

## Components

| Type | Count |
|------|-------|
| Skills | 19 |
| Agents | 14 |
| Commands | 15 |
| Hooks | 4 |

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
